"""JSON file persistence for cron jobs.

This module handles loading and saving cron jobs to a JSON file,
with file locking for concurrent access safety.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import BaseModel, Field

from macbot.cron.types import CronJob

logger = logging.getLogger(__name__)

# Storage format version for future migrations
STORAGE_VERSION = 1


class CronStorageData(BaseModel):
    """Root structure of the cron storage file.

    Attributes:
        version: Storage format version.
        jobs: List of stored cron jobs.
    """

    version: int = Field(default=STORAGE_VERSION, description="Storage format version")
    jobs: list[CronJob] = Field(default_factory=list, description="Stored jobs")


class CronStorage:
    """JSON file-based storage for cron jobs.

    Provides thread-safe read/write access to cron job data
    stored in a JSON file. Uses file locking to prevent
    concurrent modification issues.

    Example:
        storage = CronStorage("/path/to/cron.json")
        jobs = storage.load()
        storage.save(jobs)
    """

    def __init__(
        self,
        path: str | Path,
        create_if_missing: bool = True,
    ) -> None:
        """Initialize the cron storage.

        Args:
            path: Path to the JSON storage file.
            create_if_missing: Create file if it doesn't exist.
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(".lock")
        self._lock = FileLock(str(self._lock_path))
        self._create_if_missing = create_if_missing

    @property
    def path(self) -> Path:
        """Get the storage file path."""
        return self._path

    def _ensure_file_exists(self) -> None:
        """Ensure the storage file and parent directory exist."""
        if not self._path.exists():
            if self._create_if_missing:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._write_data(CronStorageData())
                logger.info(f"Created cron storage file: {self._path}")
            else:
                raise FileNotFoundError(f"Cron storage file not found: {self._path}")

    def _read_data(self) -> CronStorageData:
        """Read and parse the storage file.

        Returns:
            Parsed storage data.

        Raises:
            FileNotFoundError: If file doesn't exist and create_if_missing is False.
            json.JSONDecodeError: If file contains invalid JSON.
        """
        self._ensure_file_exists()

        content = self._path.read_text(encoding="utf-8")
        if not content.strip():
            return CronStorageData()

        data = json.loads(content)

        # Handle version migrations if needed
        version = data.get("version", 1)
        if version != STORAGE_VERSION:
            data = self._migrate_data(data, version)

        return CronStorageData.model_validate(data)

    def _write_data(self, data: CronStorageData) -> None:
        """Write storage data to file.

        Args:
            data: Data to write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict with datetime serialization
        json_data = data.model_dump(mode="json")

        content = json.dumps(json_data, indent=2, default=self._json_serializer)
        self._path.write_text(content, encoding="utf-8")

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime objects.

        Args:
            obj: Object to serialize.

        Returns:
            JSON-serializable representation.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _migrate_data(self, data: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Migrate data from an older version.

        Args:
            data: Raw data from file.
            from_version: Version of the stored data.

        Returns:
            Migrated data at current version.
        """
        # Currently no migrations needed
        logger.info(f"Migrating cron storage from version {from_version} to {STORAGE_VERSION}")
        data["version"] = STORAGE_VERSION
        return data

    def load(self) -> list[CronJob]:
        """Load all cron jobs from storage.

        Returns:
            List of cron jobs.
        """
        with self._lock:
            data = self._read_data()
            logger.debug(f"Loaded {len(data.jobs)} cron jobs from {self._path}")
            return data.jobs

    def save(self, jobs: list[CronJob]) -> None:
        """Save cron jobs to storage.

        Args:
            jobs: List of jobs to save.
        """
        with self._lock:
            data = CronStorageData(jobs=jobs)
            self._write_data(data)
            logger.debug(f"Saved {len(jobs)} cron jobs to {self._path}")

    def get(self, job_id: str) -> CronJob | None:
        """Get a specific job by ID.

        Args:
            job_id: The job ID to look up.

        Returns:
            The job if found, None otherwise.
        """
        jobs = self.load()
        for job in jobs:
            if job.id == job_id:
                return job
        return None

    def add(self, job: CronJob) -> None:
        """Add a new job to storage.

        Args:
            job: The job to add.

        Raises:
            ValueError: If a job with the same ID already exists.
        """
        with self._lock:
            data = self._read_data()

            # Check for duplicate ID
            for existing in data.jobs:
                if existing.id == job.id:
                    raise ValueError(f"Job with ID '{job.id}' already exists")

            data.jobs.append(job)
            self._write_data(data)
            logger.info(f"Added cron job: {job.name} ({job.id})")

    def update(self, job: CronJob) -> bool:
        """Update an existing job.

        Args:
            job: The job with updated data.

        Returns:
            True if the job was found and updated.
        """
        with self._lock:
            data = self._read_data()

            for i, existing in enumerate(data.jobs):
                if existing.id == job.id:
                    job.updated_at = datetime.now(timezone.utc)
                    data.jobs[i] = job
                    self._write_data(data)
                    logger.info(f"Updated cron job: {job.name} ({job.id})")
                    return True

            return False

    def remove(self, job_id: str) -> bool:
        """Remove a job from storage.

        Args:
            job_id: ID of the job to remove.

        Returns:
            True if the job was found and removed.
        """
        with self._lock:
            data = self._read_data()
            original_count = len(data.jobs)

            data.jobs = [j for j in data.jobs if j.id != job_id]

            if len(data.jobs) < original_count:
                self._write_data(data)
                logger.info(f"Removed cron job: {job_id}")
                return True

            return False

    def clear(self) -> int:
        """Remove all jobs from storage.

        Returns:
            Number of jobs removed.
        """
        with self._lock:
            data = self._read_data()
            count = len(data.jobs)
            data.jobs = []
            self._write_data(data)
            logger.info(f"Cleared {count} cron jobs")
            return count

    def count(self) -> int:
        """Get the number of stored jobs.

        Returns:
            Number of jobs.
        """
        return len(self.load())

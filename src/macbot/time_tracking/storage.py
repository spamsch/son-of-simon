"""SQLite storage for time tracking.

Tracks time entries and active timers.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Module-level singleton
_storage: "TimeTrackingStorage | None" = None


def get_storage() -> "TimeTrackingStorage":
    """Get the singleton TimeTrackingStorage instance.

    Returns:
        TimeTrackingStorage instance
    """
    global _storage
    if _storage is None:
        _storage = TimeTrackingStorage()
    return _storage


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 23m" or "45m 12s"
    """
    if seconds < 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 and hours == 0:  # Only show seconds if under an hour
        parts.append(f"{secs}s")

    return " ".join(parts) if parts else "0s"


class TimeTrackingStorage:
    """SQLite storage for time tracking data."""

    def __init__(self, db_path: Path | str | None = None):
        """Initialize the time tracking database.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.macbot/time_tracking.db
        """
        if db_path is None:
            db_path = Path.home() / ".macbot" / "time_tracking.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Completed time entries
                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_task_name ON time_entries(task_name);
                CREATE INDEX IF NOT EXISTS idx_start_time ON time_entries(start_time);

                -- Currently running timer (max 1 row)
                CREATE TABLE IF NOT EXISTS active_timer (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    task_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def start_timer(self, task_name: str) -> dict[str, Any]:
        """Start a new timer, stopping any existing one first.

        Args:
            task_name: Name of the task to track

        Returns:
            Dictionary with start info and optional stopped timer info
        """
        result: dict[str, Any] = {"success": True, "task_name": task_name}

        # Check for and stop any existing timer
        stopped = self.stop_timer(auto_stop=True)
        if stopped.get("success") and stopped.get("was_active"):
            result["previous_timer"] = {
                "task_name": stopped["task_name"],
                "duration": stopped["duration"],
                "duration_seconds": stopped["duration_seconds"],
            }

        # Start new timer
        start_time = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO active_timer (id, task_name, start_time) VALUES (1, ?, ?)",
                (task_name, start_time),
            )

        result["started_at"] = start_time
        return result

    def stop_timer(self, notes: str | None = None, auto_stop: bool = False) -> dict[str, Any]:
        """Stop the current timer and record the time entry.

        Args:
            notes: Optional notes to add to the time entry
            auto_stop: If True, this is an automatic stop (for auto-switch)

        Returns:
            Dictionary with stop info
        """
        active = self.get_active()
        if not active:
            return {
                "success": False if not auto_stop else True,
                "was_active": False,
                "error": "No timer running" if not auto_stop else None,
            }

        end_time = datetime.now()
        start_time = datetime.fromisoformat(active["start_time"])
        duration_seconds = int((end_time - start_time).total_seconds())

        # Record the time entry
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO time_entries (task_name, start_time, end_time, duration_seconds, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (active["task_name"], active["start_time"], end_time.isoformat(), duration_seconds, notes),
            )
            # Remove active timer
            conn.execute("DELETE FROM active_timer WHERE id = 1")

        return {
            "success": True,
            "was_active": True,
            "task_name": active["task_name"],
            "started_at": active["start_time"],
            "ended_at": end_time.isoformat(),
            "duration": format_duration(duration_seconds),
            "duration_seconds": duration_seconds,
        }

    def get_active(self) -> dict[str, Any] | None:
        """Get the currently active timer if any.

        Returns:
            Dictionary with active timer info, or None if no timer running
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM active_timer WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_status(self) -> dict[str, Any]:
        """Get the current timer status.

        Returns:
            Dictionary with timer status info
        """
        active = self.get_active()
        if not active:
            return {"active": False, "message": "No timer running"}

        start_time = datetime.fromisoformat(active["start_time"])
        elapsed_seconds = int((datetime.now() - start_time).total_seconds())

        return {
            "active": True,
            "task_name": active["task_name"],
            "started_at": active["start_time"],
            "elapsed": format_duration(elapsed_seconds),
            "elapsed_seconds": elapsed_seconds,
        }

    def get_entries(
        self,
        days: int = 7,
        task_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get time entries for a period.

        Args:
            days: Number of days to look back
            task_name: Filter by task name (optional)
            limit: Maximum number of entries to return

        Returns:
            List of time entry dictionaries
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        query = "SELECT * FROM time_entries WHERE start_time >= ?"
        params: list[Any] = [cutoff]

        if task_name:
            query += " AND task_name = ?"
            params.append(task_name)

        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_summary(self, days: int = 7, task_name: str | None = None) -> dict[str, Any]:
        """Get a summary of time entries grouped by task.

        Args:
            days: Number of days to look back
            task_name: Filter by specific task name (optional)

        Returns:
            Dictionary with summary information
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Build query
        base_where = "WHERE start_time >= ?"
        params: list[Any] = [cutoff]

        if task_name:
            base_where += " AND task_name = ?"
            params.append(task_name)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get totals by task
            query = f"""
                SELECT task_name, SUM(duration_seconds) as total_seconds, COUNT(*) as entry_count
                FROM time_entries
                {base_where}
                GROUP BY task_name
                ORDER BY total_seconds DESC
            """
            cursor = conn.execute(query, params)
            by_task = [
                {
                    "task": row["task_name"],
                    "total": format_duration(row["total_seconds"]),
                    "total_seconds": row["total_seconds"],
                    "entries": row["entry_count"],
                }
                for row in cursor.fetchall()
            ]

            # Calculate grand total
            total_seconds = sum(t["total_seconds"] for t in by_task)

        # Build period description
        if days == 1:
            period = "Today"
        elif days == 7:
            period = "Last 7 days"
        else:
            period = f"Last {days} days"

        result: dict[str, Any] = {
            "success": True,
            "period": period,
            "total": format_duration(total_seconds),
            "total_seconds": total_seconds,
            "by_task": by_task,
        }

        # Include individual entries if filtering by task
        if task_name:
            result["entries"] = self.get_entries(days=days, task_name=task_name)

        return result

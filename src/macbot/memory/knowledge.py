"""Knowledge memory module for persistent agent learning.

Stores lessons learned, user preferences, and user facts in a human-readable
YAML file that persists across agent runs and is loaded into the system prompt.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class KnowledgeMemory:
    """Persistent agent knowledge memory stored in YAML format."""

    def __init__(self, path: str = "~/.macbot/memory.yaml"):
        """Initialize knowledge memory.

        Args:
            path: Path to the memory YAML file (supports ~ expansion)
        """
        self.path = Path(os.path.expanduser(path))
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load memory from file.

        Returns:
            Dictionary with lessons_learned, user_preferences, user_facts lists
        """
        if self._data is not None:
            return self._data

        if self.path.exists():
            with open(self.path) as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

        # Ensure all required keys exist
        if "lessons_learned" not in self._data:
            self._data["lessons_learned"] = []
        if "user_preferences" not in self._data:
            self._data["user_preferences"] = []
        if "user_facts" not in self._data:
            self._data["user_facts"] = []

        return self._data

    def save(self) -> None:
        """Save memory to file with timestamp header."""
        if self._data is None:
            return

        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Build YAML content with header comment
        header = f"# Agent Memory - Auto-updated by macbot\n# Last updated: {datetime.now().isoformat()}\n\n"

        with open(self.path, "w") as f:
            f.write(header)
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def add_lesson(self, topic: str, lesson: str) -> None:
        """Add a lesson learned.

        If a lesson with the same topic exists, it will be updated.

        Args:
            topic: Short topic identifier (e.g., "Booking.com automation")
            lesson: The lesson content
        """
        data = self.load()

        # Check if topic already exists
        for item in data["lessons_learned"]:
            if item.get("topic") == topic:
                item["lesson"] = lesson
                item["updated"] = datetime.now().strftime("%Y-%m-%d")
                self.save()
                return

        # Add new lesson
        data["lessons_learned"].append({
            "topic": topic,
            "lesson": lesson,
            "added": datetime.now().strftime("%Y-%m-%d"),
        })
        self.save()

    def set_preference(self, category: str, preference: str) -> None:
        """Set or update a user preference.

        Replaces any existing preference in the same category.

        Args:
            category: Category of preference (e.g., "output", "hotels")
            preference: The preference value
        """
        data = self.load()

        # Check if category already exists
        for item in data["user_preferences"]:
            if item.get("category") == category:
                item["preference"] = preference
                self.save()
                return

        # Add new preference
        data["user_preferences"].append({
            "category": category,
            "preference": preference,
        })
        self.save()

    def add_fact(self, fact: str) -> None:
        """Add a fact about the user.

        Skips if the exact fact already exists.

        Args:
            fact: The fact to add
        """
        data = self.load()

        # Check for duplicates
        for item in data["user_facts"]:
            if item.get("fact") == fact:
                return

        data["user_facts"].append({"fact": fact})
        self.save()

    def remove_lesson(self, topic: str) -> bool:
        """Remove a lesson by topic.

        Args:
            topic: The topic to remove

        Returns:
            True if removed, False if not found
        """
        data = self.load()

        for i, item in enumerate(data["lessons_learned"]):
            if item.get("topic") == topic:
                del data["lessons_learned"][i]
                self.save()
                return True

        return False

    def remove_preference(self, category: str) -> bool:
        """Remove a preference by category.

        Args:
            category: The category to remove

        Returns:
            True if removed, False if not found
        """
        data = self.load()

        for i, item in enumerate(data["user_preferences"]):
            if item.get("category") == category:
                del data["user_preferences"][i]
                self.save()
                return True

        return False

    def remove_fact(self, fact: str) -> bool:
        """Remove a user fact.

        Args:
            fact: The fact to remove

        Returns:
            True if removed, False if not found
        """
        data = self.load()

        for i, item in enumerate(data["user_facts"]):
            if item.get("fact") == fact:
                del data["user_facts"][i]
                self.save()
                return True

        return False

    def get_all(self) -> dict[str, Any]:
        """Get all memory contents.

        Returns:
            Dictionary with all memory data
        """
        return self.load()

    def format_for_prompt(self, max_items: int | None = None) -> str:
        """Format memory as markdown text for system prompt injection.

        Args:
            max_items: If set, limit each section to the most recent N items.

        Returns:
            Markdown-formatted string, or empty string if no memory
        """
        data = self.load()

        sections = []

        # Lessons learned
        lessons = data["lessons_learned"]
        if max_items is not None:
            lessons = lessons[-max_items:]
        if lessons:
            lines = ["### Lessons Learned"]
            for item in lessons:
                lines.append(f"- **{item['topic']}**: {item['lesson']}")
            sections.append("\n".join(lines))

        # User preferences
        preferences = data["user_preferences"]
        if max_items is not None:
            preferences = preferences[-max_items:]
        if preferences:
            lines = ["### User Preferences"]
            for item in preferences:
                lines.append(f"- **{item['category']}**: {item['preference']}")
            sections.append("\n".join(lines))

        # User facts
        facts = data["user_facts"]
        if max_items is not None:
            facts = facts[-max_items:]
        if facts:
            lines = ["### User Facts"]
            for item in facts:
                lines.append(f"- {item['fact']}")
            sections.append("\n".join(lines))

        if not sections:
            return ""

        return "## Agent Memory\n\n" + "\n\n".join(sections)

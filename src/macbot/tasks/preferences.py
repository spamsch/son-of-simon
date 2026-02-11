"""Tasks: Core Preferences

Read-only task that exposes the agent's core preferences (well-known
directories, etc.) at runtime.
"""

from typing import Any

from macbot.core.preferences import CorePreferences
from macbot.tasks.base import Task

_preferences: CorePreferences | None = None


def get_preferences() -> CorePreferences:
    """Get the shared CorePreferences instance."""
    global _preferences
    if _preferences is None:
        _preferences = CorePreferences()
    return _preferences


class GetPreferencesTask(Task):
    """Return all core preferences including resolved directory paths."""

    @property
    def name(self) -> str:
        return "get_preferences"

    @property
    def description(self) -> str:
        return (
            "Get core preferences including well-known directories. "
            "Returns resolved absolute paths for temp, documents, apps, "
            "and any user-defined directories."
        )

    async def execute(self) -> dict[str, Any]:
        """Return preferences with expanded paths.

        Returns:
            Dictionary with all preferences and resolved directories.
        """
        prefs = get_preferences()
        data = prefs.load()
        return {
            "success": True,
            "directories": prefs.get_directories(),
            "raw": data,
        }


def register_preferences_tasks(registry: Any) -> None:
    """Register preferences tasks with a registry.

    Args:
        registry: TaskRegistry to register tasks with.
    """
    registry.register(GetPreferencesTask())

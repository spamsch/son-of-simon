"""Core preferences for the agent.

Provides well-known directories and other structural config loaded from
``~/.macbot/preferences.yaml``.  The file is bootstrapped with sensible
defaults on first run and never overwritten afterwards.
"""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PREFERENCES: dict[str, Any] = {
    "directories": {
        "temp": "/tmp",
        "documents": "~/Documents/SonOfSimon",
        "apps": "~/Documents/Apps",
    },
}

# Human-readable descriptions for the default directory keys.
_DIRECTORY_DESCRIPTIONS: dict[str, str] = {
    "temp": "temporary downloads and scratch files",
    "documents": "markdown documents, plans, and reusable scripts",
    "apps": "generated apps (HTML visualizations, web tools, etc.)",
}

_YAML_HEADER = """\
# Son of Simon - Core Preferences
# Edit this file to customize agent behavior.

"""


class CorePreferences:
    """Loads and exposes user preferences from ``~/.macbot/preferences.yaml``."""

    def __init__(self, path: str = "~/.macbot/preferences.yaml") -> None:
        self.path = Path(os.path.expanduser(path))
        self._data: dict[str, Any] | None = None

    # -- loading --------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """Load preferences, merging defaults for any missing keys."""
        if self._data is not None:
            return self._data

        if self.path.exists():
            with open(self.path) as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

        # Merge defaults for missing top-level sections
        for key, default_value in DEFAULT_PREFERENCES.items():
            if key not in self._data:
                self._data[key] = default_value
            elif isinstance(default_value, dict) and isinstance(self._data[key], dict):
                # Merge missing sub-keys
                for sub_key, sub_value in default_value.items():
                    if sub_key not in self._data[key]:
                        self._data[key][sub_key] = sub_value

        return self._data

    # -- directory helpers ----------------------------------------------

    def get_directories(self) -> dict[str, str]:
        """Return directories with ``~`` expanded to absolute paths."""
        data = self.load()
        return {
            name: os.path.expanduser(path)
            for name, path in data.get("directories", {}).items()
        }

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        for path in self.get_directories().values():
            Path(path).mkdir(parents=True, exist_ok=True)

    # -- bootstrap ------------------------------------------------------

    def save_defaults(self) -> None:
        """Write the default preferences file if it doesn't exist yet."""
        if self.path.exists():
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            f.write(_YAML_HEADER)
            yaml.dump(
                DEFAULT_PREFERENCES,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    # -- prompt formatting ----------------------------------------------

    def format_for_prompt(self) -> str:
        """Render preferences as markdown for system-prompt injection."""
        dirs = self.get_directories()
        if not dirs:
            return ""

        lines = [
            "## Core Preferences",
            "",
            "### Well-Known Directories",
            "Use these directories for file operations:",
        ]
        for name, resolved in dirs.items():
            lines.append(f"- **{name}**: `{resolved}`")

        lines.append("")
        lines.append("**Rules:**")
        for name in dirs:
            desc = _DIRECTORY_DESCRIPTIONS.get(name)
            if desc:
                lines.append(f"- Use `{name}` for {desc}")
        lines.append("- Always use these paths instead of inventing new locations")

        return "\n".join(lines)

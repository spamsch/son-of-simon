"""Tests for core preferences."""

import pytest
import yaml

from macbot.core.preferences import CorePreferences, DEFAULT_PREFERENCES


class TestCorePreferences:
    """Tests for the CorePreferences class."""

    def test_defaults_when_no_file(self, tmp_path):
        """Defaults are returned when no file exists."""
        prefs = CorePreferences(path=str(tmp_path / "missing.yaml"))
        data = prefs.load()

        assert data["directories"]["temp"] == "/tmp"
        assert data["directories"]["documents"] == "~/Documents/SonOfSimon"
        assert data["directories"]["apps"] == "~/Documents/Apps"

    def test_load_from_custom_yaml(self, tmp_path):
        """Values are loaded from a user-provided YAML file."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "temp": "/var/tmp",
                "documents": "~/MyDocs",
                "apps": "~/MyApps",
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        data = prefs.load()

        assert data["directories"]["temp"] == "/var/tmp"
        assert data["directories"]["documents"] == "~/MyDocs"
        assert data["directories"]["apps"] == "~/MyApps"

    def test_default_merging_for_missing_keys(self, tmp_path):
        """Missing directory keys are filled in from defaults."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "temp": "/var/tmp",
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        data = prefs.load()

        # User-provided key preserved
        assert data["directories"]["temp"] == "/var/tmp"
        # Missing keys filled from defaults
        assert data["directories"]["documents"] == "~/Documents/SonOfSimon"
        assert data["directories"]["apps"] == "~/Documents/Apps"

    def test_custom_directory_preserved(self, tmp_path):
        """User-added directory keys are preserved and not removed."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "temp": "/tmp",
                "screenshots": "~/Desktop/Screenshots",
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        data = prefs.load()

        assert data["directories"]["screenshots"] == "~/Desktop/Screenshots"
        # Defaults still merged
        assert "documents" in data["directories"]

    def test_tilde_expansion_in_get_directories(self, tmp_path):
        """get_directories() expands ~ to the home directory."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "docs": "~/Documents/Test",
                "abs": "/tmp/absolute",
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        dirs = prefs.get_directories()

        assert "~" not in dirs["docs"]
        assert dirs["docs"].endswith("/Documents/Test")
        assert dirs["abs"] == "/tmp/absolute"

    def test_ensure_directories_creates_dirs(self, tmp_path):
        """ensure_directories() creates all configured directories."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "a": str(tmp_path / "dir_a"),
                "b": str(tmp_path / "dir_b" / "nested"),
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        prefs.ensure_directories()

        assert (tmp_path / "dir_a").is_dir()
        assert (tmp_path / "dir_b" / "nested").is_dir()

    def test_format_for_prompt_output(self, tmp_path):
        """format_for_prompt() produces expected markdown."""
        prefs = CorePreferences(path=str(tmp_path / "missing.yaml"))
        text = prefs.format_for_prompt()

        assert "## Core Preferences" in text
        assert "### Well-Known Directories" in text
        assert "**temp**" in text
        assert "**documents**" in text
        assert "**apps**" in text
        assert "`/tmp`" in text
        assert "Always use these paths instead of inventing new locations" in text

    def test_format_for_prompt_includes_custom_dirs(self, tmp_path):
        """Custom directories appear in the prompt output."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {
                "screenshots": "~/Desktop/Screenshots",
            }
        }))

        prefs = CorePreferences(path=str(yaml_file))
        text = prefs.format_for_prompt()

        assert "**screenshots**" in text

    def test_save_defaults_creates_file(self, tmp_path):
        """save_defaults() creates the YAML file when missing."""
        yaml_file = tmp_path / "subdir" / "preferences.yaml"
        prefs = CorePreferences(path=str(yaml_file))
        prefs.save_defaults()

        assert yaml_file.exists()
        content = yaml.safe_load(yaml_file.read_text())
        assert content == DEFAULT_PREFERENCES

    def test_save_defaults_does_not_overwrite(self, tmp_path):
        """save_defaults() never overwrites an existing file."""
        yaml_file = tmp_path / "preferences.yaml"
        yaml_file.write_text("directories:\n  temp: /custom\n")

        prefs = CorePreferences(path=str(yaml_file))
        prefs.save_defaults()

        content = yaml.safe_load(yaml_file.read_text())
        assert content["directories"]["temp"] == "/custom"

    def test_lazy_loading(self, tmp_path):
        """load() caches data and does not re-read the file."""
        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({"directories": {"temp": "/a"}}))

        prefs = CorePreferences(path=str(yaml_file))
        data1 = prefs.load()

        # Overwrite the file — cached data should be unchanged
        yaml_file.write_text(yaml.dump({"directories": {"temp": "/b"}}))
        data2 = prefs.load()

        assert data1 is data2
        assert data2["directories"]["temp"] == "/a"


class TestGetPreferencesTask:
    """Tests for the get_preferences task."""

    @pytest.mark.asyncio
    async def test_task_returns_resolved_paths(self, tmp_path):
        """The task returns expanded directory paths."""
        from macbot.tasks.preferences import GetPreferencesTask, _preferences
        import macbot.tasks.preferences as mod

        yaml_file = tmp_path / "prefs.yaml"
        yaml_file.write_text(yaml.dump({
            "directories": {"temp": "/tmp", "docs": "~/Documents"},
        }))

        # Inject test preferences
        old = mod._preferences
        mod._preferences = CorePreferences(path=str(yaml_file))
        try:
            task = GetPreferencesTask()
            result = await task.execute()

            assert result["success"] is True
            assert "~" not in result["directories"]["docs"]
            assert result["directories"]["temp"] == "/tmp"
            assert "directories" in result["raw"]
        finally:
            mod._preferences = old

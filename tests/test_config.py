"""Tests for prosaic.config module."""

import json
from pathlib import Path

import pytest

from prosaic import config


class TestGetConfigDir:
    """Tests for get_config_dir()."""

    def test_default_path(self, monkeypatch):
        """Default path is ~/.config/prosaic without env vars."""
        monkeypatch.delenv("PROSAIC_CONFIG_DIR", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = config.get_config_dir()
        assert result == Path.home() / ".config" / "prosaic"

    def test_env_override(self, monkeypatch, tmp_path):
        """PROSAIC_CONFIG_DIR takes priority."""
        custom_dir = tmp_path / "custom"
        monkeypatch.setenv("PROSAIC_CONFIG_DIR", str(custom_dir))
        result = config.get_config_dir()
        assert result == custom_dir.resolve()

    def test_xdg_fallback(self, monkeypatch, tmp_path):
        """XDG_CONFIG_HOME is used as fallback."""
        monkeypatch.delenv("PROSAIC_CONFIG_DIR", raising=False)
        xdg_dir = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        result = config.get_config_dir()
        assert result == xdg_dir / "prosaic"


class TestLoadConfig:
    """Tests for load_config()."""

    def test_missing_file(self, tmp_config_dir):
        """Returns empty dict when settings.json doesn't exist."""
        result = config.load_config()
        assert result == {}

    def test_existing_file(self, write_config):
        """Loads JSON correctly from existing file."""
        data = {"foo": "bar", "num": 42}
        write_config(data)
        result = config.load_config()
        assert result == data

    def test_auto_migrates_legacy(self, write_config, legacy_config):
        """Automatically migrates legacy config to v2."""
        write_config(legacy_config)
        result = config.load_config()
        assert "app_version" in result
        assert "profiles" in result
        assert "default" in result["profiles"]
        assert result["profiles"]["default"]["archive_dir"] == "/home/user/Writing"


class TestSaveConfig:
    """Tests for save_config()."""

    def test_creates_dir(self, tmp_config_dir):
        """Creates parent directory if needed."""
        # Remove the config dir to test creation
        import shutil
        shutil.rmtree(tmp_config_dir)

        data = {"test": True}
        config.save_config(data)

        config_path = config.get_config_path()
        assert config_path.exists()
        assert json.loads(config_path.read_text()) == data


class TestMigrateConfig:
    """Tests for migrate_config()."""

    def test_legacy_migration(self, legacy_config):
        """Wraps legacy fields into profiles.default, adds app_version."""
        result = config.migrate_config(legacy_config)
        assert "app_version" in result
        assert result["active_profile"] == "default"
        assert "profiles" in result
        assert result["profiles"]["default"]["archive_dir"] == "/home/user/Writing"
        assert result["profiles"]["default"]["init_git"] is True

    def test_already_v2(self, v2_config):
        """Returns unchanged if already v2."""
        result = config.migrate_config(v2_config)
        assert result == v2_config

    def test_empty_config(self):
        """Returns empty dict unchanged."""
        result = config.migrate_config({})
        assert result == {}

    def test_incomplete_config(self):
        """Does not migrate if setup_complete is missing."""
        incomplete = {"archive_dir": "/some/path"}
        result = config.migrate_config(incomplete)
        assert result == incomplete


class TestBackupConfig:
    """Tests for backup_config()."""

    def test_creates_backup_for_legacy(self, write_config, legacy_config):
        """Creates backup when migrating legacy config."""
        write_config(legacy_config)
        backup_path = config.backup_config()
        assert backup_path is not None
        assert backup_path.exists()
        assert json.loads(backup_path.read_text()) == legacy_config

    def test_skips_if_already_v2(self, write_config, v2_config):
        """Does not create backup for v2 config."""
        write_config(v2_config)
        backup_path = config.backup_config()
        assert backup_path is None

    def test_skips_if_backup_exists(self, write_config, legacy_config, tmp_config_dir):
        """Does not overwrite existing backup."""
        write_config(legacy_config)
        # Create existing backup
        existing_backup = tmp_config_dir / "settings.backup.json"
        existing_backup.write_text('{"old": "backup"}')

        backup_path = config.backup_config()
        assert backup_path is None
        # Existing backup should be unchanged
        assert json.loads(existing_backup.read_text()) == {"old": "backup"}


class TestProfileState:
    """Tests for active profile state management."""

    def test_default_profile(self):
        """Default active profile is 'default'."""
        config._active_profile = "default"  # Reset
        assert config.get_active_profile() == "default"

    def test_set_active_profile(self):
        """set_active_profile updates the state."""
        config.set_active_profile("work")
        assert config.get_active_profile() == "work"
        config.set_active_profile("default")  # Reset


class TestWasJustMigrated:
    """Tests for was_just_migrated()."""

    def test_returns_true_after_migration(self, write_config, legacy_config):
        """Returns True immediately after migrating legacy config."""
        config._just_migrated = False  # Reset
        write_config(legacy_config)
        config.load_config()  # This triggers migration
        assert config.was_just_migrated() is True

    def test_returns_false_after_check(self, write_config, legacy_config):
        """Returns False on second check (resets after reading)."""
        config._just_migrated = False  # Reset
        write_config(legacy_config)
        config.load_config()
        config.was_just_migrated()  # First check
        assert config.was_just_migrated() is False  # Second check

    def test_returns_false_for_v2_config(self, write_config, v2_config):
        """Returns False when loading already-migrated config."""
        config._just_migrated = False  # Reset
        write_config(v2_config)
        config.load_config()
        assert config.was_just_migrated() is False


class TestGetProfileConfig:
    """Tests for get_profile_config()."""

    def test_default_profile(self, write_config, v2_config):
        """Reads active profile by default."""
        write_config(v2_config)
        config.set_active_profile("default")
        result = config.get_profile_config()
        assert result["archive_dir"] == "/home/user/Writing"

    def test_named_profile(self, write_config):
        """Reads specific named profile."""
        multi_profile = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/home/default"},
                "work": {"archive_dir": "/home/work"},
            },
        }
        write_config(multi_profile)
        result = config.get_profile_config("work")
        assert result["archive_dir"] == "/home/work"

    def test_missing_profile(self, write_config, v2_config):
        """Returns empty dict for missing profile."""
        write_config(v2_config)
        result = config.get_profile_config("nonexistent")
        assert result == {}


class TestSaveProfileConfig:
    """Tests for save_profile_config()."""

    def test_saves_to_profile(self, write_config, v2_config):
        """Writes to correct profile key."""
        write_config(v2_config)
        config.set_active_profile("default")

        new_data = {"archive_dir": "/new/path", "init_git": False}
        config.save_profile_config(new_data)

        loaded = config.load_config()
        assert loaded["profiles"]["default"]["archive_dir"] == "/new/path"

    def test_creates_new_profile(self, write_config, v2_config):
        """Creates new profile if it doesn't exist."""
        write_config(v2_config)

        new_data = {"archive_dir": "/work/path"}
        config.save_profile_config(new_data, "work")

        loaded = config.load_config()
        assert "work" in loaded["profiles"]
        assert loaded["profiles"]["work"]["archive_dir"] == "/work/path"


class TestGetWorkspaceDir:
    """Tests for get_workspace_dir()."""

    def test_from_profile(self, write_config, tmp_workspace):
        """Reads archive_dir from active profile."""
        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": str(tmp_workspace)},
            },
        }
        write_config(v2)
        config.set_active_profile("default")
        result = config.get_workspace_dir()
        assert result == tmp_workspace

    def test_fallback(self, tmp_config_dir):
        """Defaults to ~/Prosaic when no config."""
        config.set_active_profile("default")
        result = config.get_workspace_dir()
        assert result == Path.home() / "Prosaic"


class TestLastFile:
    """Tests for get_last_file() and set_last_file()."""

    def test_get_last_file(self, write_config, tmp_workspace):
        """Reads last_file from profile."""
        last_file = tmp_workspace / "test.md"
        last_file.write_text("# Test")

        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {
                    "archive_dir": str(tmp_workspace),
                    "last_file": str(last_file),
                }
            },
        }
        write_config(v2)
        config.set_active_profile("default")

        result = config.get_last_file()
        assert result == last_file

    def test_set_last_file(self, write_config, tmp_workspace):
        """Writes last_file to profile."""
        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": str(tmp_workspace)},
            },
        }
        write_config(v2)
        config.set_active_profile("default")

        test_file = tmp_workspace / "new.md"
        test_file.write_text("# New")
        config.set_last_file(test_file)

        loaded = config.load_config()
        assert loaded["profiles"]["default"]["last_file"] == str(test_file)


class TestGetNotesPath:
    """Tests for get_notes_path()."""

    def test_returns_workspace_notes(self, write_config, tmp_workspace):
        """Returns workspace/notes.md."""
        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": str(tmp_workspace)},
            },
        }
        write_config(v2)
        config.set_active_profile("default")
        result = config.get_notes_path()
        assert result == tmp_workspace / "notes.md"


class TestEnsureWorkspace:
    """Tests for ensure_workspace()."""

    def test_creates_dirs(self, write_config, tmp_workspace):
        """Creates pieces/, books/, notes.md."""
        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": str(tmp_workspace), "init_git": False},
            },
        }
        write_config(v2)
        config.set_active_profile("default")

        config.ensure_workspace()

        assert (tmp_workspace / "pieces").is_dir()
        assert (tmp_workspace / "books").is_dir()
        assert (tmp_workspace / "notes.md").is_file()

    def test_preserves_existing_notes(self, write_config, tmp_workspace):
        """Does not overwrite existing notes.md."""
        existing_content = "# My Existing Notes\n\nImportant stuff"
        (tmp_workspace / "notes.md").write_text(existing_content)

        v2 = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": str(tmp_workspace), "init_git": False},
            },
        }
        write_config(v2)
        config.set_active_profile("default")

        config.ensure_workspace()

        assert (tmp_workspace / "notes.md").read_text() == existing_content


class TestListProfiles:
    """Tests for list_profiles()."""

    def test_single_profile(self, write_config, v2_config):
        """Returns list with single profile."""
        write_config(v2_config)
        assert config.list_profiles() == ["default"]

    def test_multiple_profiles(self, write_config):
        """Returns all profile names."""
        multi = {
            "app_version": "1.2.0",
            "profiles": {
                "default": {"archive_dir": "/a"},
                "work": {"archive_dir": "/b"},
                "personal": {"archive_dir": "/c"},
            },
        }
        write_config(multi)
        profiles = config.list_profiles()
        assert set(profiles) == {"default", "work", "personal"}

    def test_empty_config(self, write_config):
        """Returns empty list for empty config."""
        write_config({})
        assert config.list_profiles() == []


class TestDeleteProfile:
    """Tests for delete_profile()."""

    def test_deletes_profile(self, write_config):
        """Successfully deletes a profile."""
        multi = {
            "app_version": "1.2.0",
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/a"},
                "work": {"archive_dir": "/b"},
            },
        }
        write_config(multi)
        result = config.delete_profile("work")
        assert result is True
        assert "work" not in config.list_profiles()

    def test_cannot_delete_only_profile(self, write_config, v2_config):
        """Cannot delete the last remaining profile."""
        write_config(v2_config)
        result = config.delete_profile("default")
        assert result is False
        assert "default" in config.list_profiles()

    def test_cannot_delete_nonexistent(self, write_config, v2_config):
        """Cannot delete a profile that doesn't exist."""
        write_config(v2_config)
        result = config.delete_profile("nonexistent")
        assert result is False

    def test_switches_active_if_deleted(self, write_config):
        """Switches active profile if deleted profile was active."""
        multi = {
            "app_version": "1.2.0",
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/a"},
                "work": {"archive_dir": "/b"},
            },
        }
        write_config(multi)
        config.set_active_profile("default")
        config.delete_profile("default")
        assert config.get_active_profile() == "work"


class TestRenameProfile:
    """Tests for rename_profile()."""

    def test_renames_profile(self, write_config, v2_config):
        """Successfully renames a profile."""
        write_config(v2_config)
        result = config.rename_profile("default", "personal")
        assert result is True
        assert "personal" in config.list_profiles()
        assert "default" not in config.list_profiles()

    def test_cannot_rename_nonexistent(self, write_config, v2_config):
        """Cannot rename a profile that doesn't exist."""
        write_config(v2_config)
        result = config.rename_profile("nonexistent", "newname")
        assert result is False

    def test_cannot_rename_to_existing(self, write_config):
        """Cannot rename to an existing profile name."""
        multi = {
            "app_version": "1.2.0",
            "profiles": {
                "default": {"archive_dir": "/a"},
                "work": {"archive_dir": "/b"},
            },
        }
        write_config(multi)
        result = config.rename_profile("default", "work")
        assert result is False

    def test_updates_active_on_rename(self, write_config, v2_config):
        """Updates active_profile when renamed."""
        write_config(v2_config)
        config.set_active_profile("default")
        config.rename_profile("default", "personal")
        assert config.get_active_profile() == "personal"


class TestUpdateProfileWorkspace:
    """Tests for update_profile_workspace()."""

    def test_updates_workspace(self, write_config, v2_config):
        """Successfully updates workspace path."""
        write_config(v2_config)
        result = config.update_profile_workspace("default", "/new/path")
        assert result is True
        profile = config.get_profile_config("default")
        assert profile["archive_dir"] == "/new/path"

    def test_cannot_update_nonexistent(self, write_config, v2_config):
        """Cannot update a profile that doesn't exist."""
        write_config(v2_config)
        result = config.update_profile_workspace("nonexistent", "/path")
        assert result is False


class TestValidLanguageCodes:
    """Tests for VALID_LANGUAGE_CODES constant."""

    def test_contains_english(self):
        assert "en_US" in config.VALID_LANGUAGE_CODES

    def test_contains_hungarian(self):
        assert "hu_HU" in config.VALID_LANGUAGE_CODES

    def test_all_codes_are_strings(self):
        for code in config.VALID_LANGUAGE_CODES:
            assert isinstance(code, str)

    def test_is_non_empty(self):
        assert len(config.VALID_LANGUAGE_CODES) > 50


class TestNeedsLanguageSetup:
    """Tests for needs_language_setup()."""

    def test_returns_true_when_missing(self, write_config, v2_config):
        """Returns True when spell_language is absent from profile."""
        write_config(v2_config)
        assert config.needs_language_setup("default") is True

    def test_returns_false_when_present(self, write_config, v2_config):
        """Returns False when spell_language is set."""
        v2_config["profiles"]["default"]["spell_language"] = "en"
        write_config(v2_config)
        assert config.needs_language_setup("default") is False

    def test_uses_active_profile_when_none(self, write_config, v2_config):
        """Uses active profile when profile_name is None."""
        write_config(v2_config)
        config.set_active_profile("default")
        assert config.needs_language_setup(None) is True


class TestProfilesNeedingLanguageSetup:
    """Tests for profiles_needing_language_setup()."""

    def test_returns_all_when_none_configured(self, write_config):
        """Returns all profiles when none have spell_language."""
        cfg = {
            "app_version": "1.0.0",
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/a"},
                "work": {"archive_dir": "/b"},
            },
        }
        write_config(cfg)
        result = config.profiles_needing_language_setup()
        assert set(result) == {"default", "work"}

    def test_excludes_configured_profiles(self, write_config):
        """Excludes profiles that already have spell_language."""
        cfg = {
            "app_version": "1.0.0",
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/a", "spell_language": "en"},
                "work": {"archive_dir": "/b"},
            },
        }
        write_config(cfg)
        result = config.profiles_needing_language_setup()
        assert result == ["work"]

    def test_returns_empty_when_all_configured(self, write_config):
        """Returns empty list when all profiles have spell_language."""
        cfg = {
            "app_version": "1.0.0",
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/a", "spell_language": "en"},
                "work": {"archive_dir": "/b", "spell_language": "hu"},
            },
        }
        write_config(cfg)
        result = config.profiles_needing_language_setup()
        assert result == []

"""Tests for prosaic.wizard module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from prosaic import wizard


class TestNeedsSetup:
    """Tests for needs_setup()."""

    def test_no_config(self, tmp_config_dir):
        """Returns True when no settings.json exists."""
        assert wizard.needs_setup() is True

    def test_legacy_complete(self, write_config, legacy_config):
        """Returns False for complete legacy config."""
        write_config(legacy_config)
        assert wizard.needs_setup() is False

    def test_profile_exists(self, write_config, v2_config):
        """Returns False for configured profile."""
        write_config(v2_config)
        assert wizard.needs_setup("default") is False

    def test_profile_missing(self, write_config, v2_config):
        """Returns True for unconfigured profile name."""
        write_config(v2_config)
        assert wizard.needs_setup("work") is True

    def test_empty_profile(self, write_config):
        """Returns True for registered but empty profile."""
        config = {
            "app_version": "1.2.0",
            "setup_complete": True,
            "active_profile": "default",
            "profiles": {
                "default": {"archive_dir": "/some/path"},
                "work": {},  # Registered but not configured
            },
        }
        write_config(config)
        assert wizard.needs_setup("default") is False
        assert wizard.needs_setup("work") is True


class TestParseProfileNames:
    """Tests for _parse_profile_names()."""

    def test_comma_separated(self):
        """Parses comma-separated names."""
        result = wizard._parse_profile_names("work, fiction, journal")
        assert result == ["work", "fiction", "journal"]

    def test_space_separated(self):
        """Parses space-separated names."""
        result = wizard._parse_profile_names("work fiction journal")
        assert result == ["work", "fiction", "journal"]

    def test_mixed_separators(self):
        """Parses mixed comma and space separators."""
        result = wizard._parse_profile_names("work, fiction journal")
        assert result == ["work", "fiction", "journal"]

    def test_normalizes_case(self):
        """Converts to lowercase."""
        result = wizard._parse_profile_names("Work, FICTION")
        assert result == ["work", "fiction"]

    def test_filters_empty(self):
        """Filters empty strings."""
        result = wizard._parse_profile_names("work,, fiction, ")
        assert result == ["work", "fiction"]


class TestSetupWorkspace:
    """Tests for setup_workspace()."""

    def test_creates_structure(self, tmp_workspace):
        """Creates dirs + notes.md + metrics.json."""
        config = {"archive_dir": str(tmp_workspace), "init_git": False}
        wizard.setup_workspace(config)

        assert (tmp_workspace / "pieces").is_dir()
        assert (tmp_workspace / "books").is_dir()
        assert (tmp_workspace / "notes.md").is_file()
        assert (tmp_workspace / "metrics.json").is_file()

    def test_preserves_existing_notes(self, tmp_workspace):
        """Does not overwrite existing notes.md."""
        existing = "# My notes\n\nDon't delete me"
        (tmp_workspace / "notes.md").write_text(existing)

        config = {"archive_dir": str(tmp_workspace), "init_git": False}
        wizard.setup_workspace(config)

        assert (tmp_workspace / "notes.md").read_text() == existing


class TestRunSetupSingleProfile:
    """Tests for run_setup() in single profile mode."""

    def test_single_profile_mode(self, tmp_workspace):
        """Returns correct structure in single profile mode."""
        with patch("click.prompt", side_effect=[str(tmp_workspace), "en_US"]):
            with patch("click.confirm", side_effect=[False, False, True]):
                # 1. init git? no  2. light theme? no  3. enable spell check? yes
                result = wizard.run_setup(
                    profile_name="work",
                    single_profile_mode=True,
                )

        assert "profiles" in result
        assert "work" in result["profiles"]
        assert result["active_profile"] == "work"
        assert result["profiles"]["work"]["archive_dir"] == str(tmp_workspace)
        assert result["profiles"]["work"]["spell_language"] == "en_US"


class TestRunSetupFresh:
    """Tests for run_setup() fresh install mode."""

    def test_fresh_single_profile(self, tmp_workspace):
        """Fresh install with single profile (no multi-profile)."""
        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [str(tmp_workspace), "en_US"]
            with patch("click.confirm") as mock_confirm:
                # 1. rename default? no
                # 2. enable multiple profiles? no
                # 3. init git? no
                # 4. use light theme? yes
                # 5. enable spell check? yes
                mock_confirm.side_effect = [False, False, False, True, True]
                result = wizard.run_setup()

        assert "profiles" in result
        assert "default" in result["profiles"]
        assert result["active_profile"] == "default"
        assert result["profiles"]["default"]["spell_language"] == "en_US"
        assert result["profiles"]["default"]["spell_check_enabled"] is True

    def test_fresh_rename_default(self, tmp_workspace):
        """Fresh install with renamed default profile."""
        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["personal", str(tmp_workspace), "en_US"]
            with patch("click.confirm") as mock_confirm:
                # 1. rename? yes, 2. multi? no, 3. git? no, 4. light theme? yes, 5. spell? yes
                mock_confirm.side_effect = [True, False, False, True, True]
                result = wizard.run_setup()

        assert "personal" in result["profiles"]
        assert "default" not in result["profiles"]
        assert result["active_profile"] == "personal"

    def test_fresh_multi_profile(self, tmp_workspace, tmp_path):
        """Fresh install with multiple profiles."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "work",          # additional profile names
                str(tmp_workspace),  # default archive
                "en_US",         # default spell language
                str(work_dir),   # work archive
                "hu_HU",         # work spell language
            ]
            with patch("click.confirm") as mock_confirm:
                # 1. rename default? no
                # 2. enable multi? yes
                # 3. init git for default? no
                # 4. light theme for default? yes
                # 5. enable spell check for default? yes
                # 6. setup others now? yes
                # 7. init git for work? no
                # 8. light theme for work? no (dark)
                # 9. enable spell check for work? yes
                mock_confirm.side_effect = [False, True, False, True, True, True, False, False, True]
                result = wizard.run_setup()

        assert "default" in result["profiles"]
        assert "work" in result["profiles"]
        assert Path(result["profiles"]["work"]["archive_dir"]).resolve() == work_dir.resolve()
        assert result["profiles"]["work"]["spell_language"] == "hu_HU"


class TestRunSetupExisting:
    """Tests for run_setup() with existing profiles."""

    def test_shows_existing(self, tmp_workspace, tmp_path):
        """Shows existing profiles and allows adding new ones."""
        existing = {
            "default": {"archive_dir": "/home/user/Writing"},
        }
        new_dir = tmp_path / "work"
        new_dir.mkdir()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "work",       # additional profile names
                str(new_dir), # work archive
                "en_US",      # work spell language
            ]
            with patch("click.confirm") as mock_confirm:
                # 1. rename default? no, 2. add more? yes, 3. git? no, 4. light theme? yes, 5. spell? yes
                mock_confirm.side_effect = [False, True, False, True, True]
                result = wizard.run_setup(existing_profiles=existing)

        assert "default" in result["profiles"]
        assert result["profiles"]["default"]["archive_dir"] == "/home/user/Writing"
        assert "work" in result["profiles"]
        assert result["profiles"]["work"]["archive_dir"] == str(new_dir)

    def test_existing_rename_default(self):
        """Existing user can rename the default profile."""
        existing = {
            "default": {"archive_dir": "/home/user/Writing"},
        }

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["personal"]  # new name for default
            with patch("click.confirm") as mock_confirm:
                # 1. rename? yes, 2. add more? no
                mock_confirm.side_effect = [True, False]
                result = wizard.run_setup(existing_profiles=existing)

        assert "personal" in result["profiles"]
        assert "default" not in result["profiles"]
        assert result["profiles"]["personal"]["archive_dir"] == "/home/user/Writing"
        assert result["active_profile"] == "personal"

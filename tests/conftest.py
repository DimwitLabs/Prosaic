"""Shared pytest fixtures for Prosaic tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clear_runtime_config_cache():
    """Reset the in-memory config cache between tests."""
    from prosaic import config as _config
    _config._runtime_config = None
    yield
    _config._runtime_config = None


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory and patch get_config_dir."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("PROSAIC_CONFIG_DIR", str(config_dir))
    return config_dir


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def legacy_config():
    """Sample legacy (v1) config dict."""
    return {
        "setup_complete": True,
        "archive_dir": "/home/user/Writing",
        "init_git": True,
        "git_remote": "https://github.com/user/writing.git",
        "git_inherited": False,
        "last_file": "/home/user/Writing/pieces/draft.md",
    }


@pytest.fixture
def v2_config():
    """Sample v2 config dict with profiles."""
    return {
        "app_version": "1.2.0",
        "setup_complete": True,
        "active_profile": "default",
        "profiles": {
            "default": {
                "archive_dir": "/home/user/Writing",
                "init_git": True,
                "git_remote": "https://github.com/user/writing.git",
                "git_inherited": False,
                "last_file": "/home/user/Writing/pieces/draft.md",
            }
        },
    }


@pytest.fixture
def write_config(tmp_config_dir):
    """Factory fixture to write config to temp directory."""
    def _write(config_data):
        config_path = tmp_config_dir / "settings.json"
        config_path.write_text(json.dumps(config_data, indent=2))
        return config_path
    return _write

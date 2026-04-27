"""Configuration management for Prosaic."""

import json
import os
import shutil
from importlib.metadata import version
from pathlib import Path

from prosaic.utils import read_text, write_text

try:
    from git import Repo
except ImportError:
    Repo = None

_active_profile: str = "default"
_just_migrated: bool = False
_runtime_config: dict | None = None

def _load_valid_languages() -> tuple[frozenset[str], dict[str, str]]:
    path = Path(__file__).parent / "VALID_LANGUAGES"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        codes = {}
        for line in lines:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                codes[parts[0].strip()] = parts[1].strip()
        return frozenset(codes.keys()), codes
    except OSError:
        return frozenset({"en_US", "en_GB"}), {"en_US": "English (US)", "en_GB": "English (Great Britain)"}

VALID_LANGUAGE_CODES, LANGUAGE_NAMES = _load_valid_languages()


def get_spell_check_enabled(profile_name: str | None = None) -> bool:
    """Return whether spell check is enabled for a profile."""
    return get_profile_config(profile_name).get("spell_check_enabled", True)


def set_spell_check_enabled(enabled: bool, profile_name: str | None = None) -> None:
    """Persist spell check enabled state for a profile."""
    profile = get_profile_config(profile_name)
    profile["spell_check_enabled"] = enabled
    save_profile_config(profile, profile_name)


def get_active_profile() -> str:
    """Get the currently active profile name."""
    return _active_profile


def set_active_profile(profile_name: str) -> None:
    """Set the active profile name."""
    global _active_profile
    _active_profile = profile_name


def was_just_migrated() -> bool:
    """Check if config was just migrated from legacy format.

    Returns True once after migration, then resets to False.
    """
    global _just_migrated
    result = _just_migrated
    _just_migrated = False
    return result


def get_app_version() -> str:
    """Get the app version from package metadata."""
    try:
        return version("prosaic-app")
    except Exception:
        return "0.0.0"


def get_config_dir() -> Path:
    """Get the config directory."""
    if env_dir := os.environ.get("PROSAIC_CONFIG_DIR"):
        return Path(env_dir).expanduser().resolve()
    if xdg_config := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg_config) / "prosaic"
    return Path.home() / ".config" / "prosaic"


def get_config_path() -> Path:
    """Get the config file path."""
    return get_config_dir() / "settings.json"


def get_backup_path() -> Path:
    """Get the backup config file path."""
    return get_config_dir() / "settings.backup.json"


def backup_config() -> Path | None:
    """Create a backup of legacy config before migration.

    Returns the backup path if created, None otherwise.
    """
    config_path = get_config_path()
    backup_path = get_backup_path()

    if not config_path.exists() or backup_path.exists():
        return None

    try:
        config = json.loads(read_text(config_path))
        if "app_version" not in config and config.get("setup_complete"):
            shutil.copy2(config_path, backup_path)
            return backup_path
    except (json.JSONDecodeError, OSError):
        pass

    return None


def migrate_config(config: dict) -> dict:
    """Migrate legacy flat config to v2 profiles structure.

    Returns the migrated config dict.
    """
    if "app_version" in config or not config:
        return config

    if not config.get("setup_complete"):
        return config

    profile_fields = [
        "archive_dir",
        "init_git",
        "git_remote",
        "git_inherited",
        "last_file",
    ]
    profile_data = {k: config[k] for k in profile_fields if k in config}

    migrated = {
        "app_version": get_app_version(),
        "setup_complete": True,  # Backward-compat shim for old Prosaic versions
        "active_profile": "default",
        "profiles": {
            "default": profile_data,
        },
    }

    return migrated


def load_config() -> dict:
    """Load configuration from settings.json.

    Migrates legacy configs to v2 format in memory. The migrated config is
    cached and only written to disk when save_config() is called explicitly
    (after setup completes), so the user's original file is never overwritten
    until they finish setup.
    """
    global _runtime_config, _just_migrated

    if _runtime_config is not None:
        return _runtime_config

    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        config = json.loads(read_text(config_path))
    except (json.JSONDecodeError, OSError):
        return {}

    if "app_version" not in config and config.get("setup_complete"):
        _just_migrated = True
        backup_config()
        config = migrate_config(config)
        _runtime_config = config  # cache in memory; main() saves after setup

    return config


def save_config(config: dict) -> None:
    """Save configuration to settings.json."""
    global _runtime_config
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(config_path, json.dumps(config, indent=2))
    _runtime_config = None  # clear cache; disk is now authoritative


def get_profile_config(profile_name: str | None = None) -> dict:
    """Get configuration for a specific profile.

    Args:
        profile_name: Profile name, or None to use active profile.

    Returns:
        Profile configuration dict (may be empty).
    """
    config = load_config()
    name = profile_name or get_active_profile()
    return config.get("profiles", {}).get(name, {})


def save_profile_config(profile_data: dict, profile_name: str | None = None) -> None:
    """Save configuration for a specific profile.

    Args:
        profile_data: Profile configuration dict.
        profile_name: Profile name, or None to use active profile.
    """
    config = load_config()
    name = profile_name or get_active_profile()

    if "profiles" not in config:
        config["profiles"] = {}

    config["profiles"][name] = profile_data
    save_config(config)


def list_profiles() -> list[str]:
    """Get list of all profile names."""
    config = load_config()
    return list(config.get("profiles", {}).keys())


def delete_profile(profile_name: str) -> bool:
    """Delete a profile from config.

    Args:
        profile_name: Profile to delete.

    Returns:
        True if deleted, False if profile doesn't exist or is the only one.
    """
    config = load_config()
    profiles = config.get("profiles", {})

    if profile_name not in profiles or len(profiles) <= 1:
        return False

    del profiles[profile_name]

    if config.get("active_profile") == profile_name:
        config["active_profile"] = next(iter(profiles.keys()))
        global _active_profile
        _active_profile = config["active_profile"]

    save_config(config)
    return True


def rename_profile(old_name: str, new_name: str) -> bool:
    """Rename a profile.

    Args:
        old_name: Current profile name.
        new_name: New profile name.

    Returns:
        True if renamed, False if old doesn't exist or new already exists.
    """
    global _active_profile
    config = load_config()
    profiles = config.get("profiles", {})

    if old_name not in profiles or new_name in profiles:
        return False

    profiles[new_name] = profiles.pop(old_name)

    if config.get("active_profile") == old_name or _active_profile == old_name:
        config["active_profile"] = new_name
        _active_profile = new_name

    save_config(config)
    return True


def update_profile_workspace(profile_name: str, archive_dir: str) -> bool:
    """Update the workspace directory for a profile.

    Args:
        profile_name: Profile to update.
        archive_dir: New workspace directory path.

    Returns:
        True if updated, False if profile doesn't exist.
    """
    config = load_config()
    profiles = config.get("profiles", {})

    if profile_name not in profiles:
        return False

    profiles[profile_name]["archive_dir"] = archive_dir
    save_config(config)
    return True


def get_workspace_dir() -> Path:
    """Get the archive directory from active profile config or default."""
    profile = get_profile_config()
    archive_dir = profile.get("archive_dir")
    if archive_dir:
        return Path(archive_dir).expanduser().resolve()
    return Path.home() / "Prosaic"


def get_pieces_dir() -> Path:
    """Get the pieces directory."""
    return get_workspace_dir() / "pieces"


def get_books_dir() -> Path:
    """Get the books directory."""
    return get_workspace_dir() / "books"


def get_notes_path() -> Path:
    """Get the notes.md path."""
    return get_workspace_dir() / "notes.md"


def get_last_file() -> Path | None:
    """Get the last edited file path from active profile."""
    profile = get_profile_config()
    last_file = profile.get("last_file")
    if last_file:
        path = Path(last_file)
        if path.exists() and path != get_notes_path():
            return path
    return None


def set_last_file(path: Path) -> None:
    """Set the last edited file path in active profile."""
    if path == get_notes_path():
        return
    profile = get_profile_config()
    profile["last_file"] = str(path)
    save_profile_config(profile)


def needs_language_setup(profile_name: str | None = None) -> bool:
    """Return True if this profile has no spell_language set yet."""
    return "spell_language" not in get_profile_config(profile_name)


def profiles_needing_language_setup() -> list[str]:
    """Return all profile names that have no spell_language set."""
    return [p for p in list_profiles() if needs_language_setup(p)]


def ensure_workspace() -> None:
    """Ensure the workspace structure exists."""
    dirs = [
        get_workspace_dir(),
        get_pieces_dir(),
        get_books_dir(),
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    notes = get_notes_path()
    if not notes.exists():
        write_text(notes, "# Notes\n\n")

    profile = get_profile_config()
    if profile.get("init_git", True) and Repo is not None:
        workspace = get_workspace_dir()
        if not (workspace / ".git").exists():
            try:
                repo = Repo.init(workspace)
                remote_url = profile.get("git_remote", "")
                if remote_url:
                    try:
                        repo.create_remote("origin", remote_url)
                    except Exception:
                        pass
            except Exception:
                pass

"""First-run setup wizard for Prosaic."""

import re
from pathlib import Path

import click

from prosaic.config import get_app_version, get_config_path, load_config
from prosaic.utils import write_text

try:
    from git import Repo
except ImportError:
    Repo = None


def needs_setup(profile_name: str = "default") -> bool:
    """Check if setup is needed for a profile.

    Args:
        profile_name: Profile to check.

    Returns:
        True if setup needed, False otherwise.
    """
    config_path = get_config_path()
    if not config_path.exists():
        return True

    config = load_config()

    if "profiles" not in config:
        return not config.get("setup_complete", False)

    profiles = config.get("profiles", {})
    profile = profiles.get(profile_name, {})
    return not profile.get("archive_dir")


def _prompt_git_remote() -> str:
    """Prompt for optional git remote URL."""
    click.echo()
    click.echo("enter a git remote url to sync your writing (optional)")
    click.echo("(press enter to skip)")
    return click.prompt("git remote", default="", show_default=False)


def _parse_profile_names(input_str: str) -> list[str]:
    """Parse comma or space separated profile names."""
    names = re.split(r"[,\s]+", input_str.strip())
    return [n.strip().lower() for n in names if n.strip()]


def _setup_single_profile(name: str) -> dict:
    """Set up a single profile (archive_dir + git prompts).

    Args:
        name: Profile name being configured.

    Returns:
        Profile configuration dict.
    """
    click.echo()
    click.secho(f"setting up profile: {name}", fg="cyan", bold=True)

    default_dir = str(Path.home() / "Prosaic")
    click.echo()
    click.echo("where should prosaic store your writing?")
    click.echo(f"(press enter for default: {default_dir})")
    archive_dir = click.prompt(
        "archive directory",
        default=default_dir,
        show_default=False,
    )
    archive_path = Path(archive_dir).expanduser().resolve()

    git_dir = archive_path / ".git"
    existing_git = git_dir.exists()
    init_git = False
    git_remote = ""

    if existing_git:
        click.echo()
        click.secho("git repository detected!", fg="cyan")
        init_git = True

        if Repo is not None:
            try:
                repo = Repo(archive_path)
                if repo.remotes:
                    git_remote = repo.remotes.origin.url
                    click.echo(f"  remote: {git_remote}")
                else:
                    click.echo("  local only (no remote configured)")
                    git_remote = _prompt_git_remote()
            except Exception:
                click.echo("  (could not read git details)")
        else:
            click.echo("  (git not available)")
    else:
        click.echo()
        init_git = click.confirm(
            "initialize git repository for version control?",
            default=True,
        )

        if init_git:
            git_remote = _prompt_git_remote()

    click.echo()
    use_light = click.confirm("use light theme as default?", default=True)
    theme = "light" if use_light else "dark"

    return {
        "archive_dir": str(archive_path),
        "init_git": init_git,
        "git_remote": git_remote,
        "git_inherited": existing_git,
        "theme": theme,
    }


def run_setup(
    profile_name: str = "default",
    existing_profiles: dict | None = None,
    single_profile_mode: bool = False,
) -> dict:
    """Run the interactive setup wizard.

    Args:
        profile_name: Profile to set up.
        existing_profiles: Dict of existing profile configs (or None for fresh).
        single_profile_mode: If True, skip multi-profile questions (--profile mode).

    Returns:
        Dict with 'profiles' (dict of name -> config) and 'active_profile'.
    """
    existing_profiles = existing_profiles or {}
    click.echo()

    if single_profile_mode:
        click.secho("welcome to prosaic", fg="yellow", bold=True)
        profile_data = _setup_single_profile(profile_name)

        click.echo()
        click.secho("setup complete!", fg="green", bold=True)
        click.echo(f"  profile: {profile_name}")
        click.echo(f"  archive: {profile_data['archive_dir']}")
        if profile_data["git_inherited"]:
            click.echo("  git: inherited existing repository")
        else:
            click.echo(f"  git: {'yes' if profile_data['init_git'] else 'no'}")
        if profile_data["git_remote"]:
            click.echo(f"  remote: {profile_data['git_remote']}")
        click.echo()

        return {
            "profiles": {profile_name: profile_data},
            "active_profile": profile_name,
        }

    if existing_profiles:
        click.secho("welcome back to prosaic", fg="yellow", bold=True)
        click.echo()
        click.echo("existing profiles:")
        for name, data in existing_profiles.items():
            archive = data.get("archive_dir", "not configured")
            click.echo(f"  {name}: {archive}")
    else:
        click.secho("welcome to prosaic", fg="yellow", bold=True)
        click.echo("let's set things up.")

    profiles_to_configure = {}
    default_profile_name = profile_name
    renamed_from = None

    can_rename = (
        not existing_profiles
        or (
            len(existing_profiles) == 1
            and "default" in existing_profiles
        )
    )
    if can_rename and default_profile_name == "default":
        click.echo()
        click.echo(f'your default profile is called "{default_profile_name}".')
        if click.confirm("would you like to rename it?", default=False):
            new_name = click.prompt("profile name").strip().lower()
            renamed_from = default_profile_name
            default_profile_name = new_name

    click.echo()
    if existing_profiles:
        add_more = click.confirm(
            "would you like to create additional profiles?", default=False
        )
    else:
        add_more = click.confirm(
            "would you like to enable multiple profiles?", default=False
        )

    additional_names = []
    if add_more:
        raw_input = click.prompt(
            "enter additional profile names (comma or space separated)"
        )
        additional_names = _parse_profile_names(raw_input)
        exclude_names = {default_profile_name}
        if renamed_from:
            exclude_names.add(renamed_from)
        additional_names = [n for n in additional_names if n not in exclude_names]

        if additional_names and not existing_profiles:
            click.echo(
                f'(the first profile "{default_profile_name}" will be your default)'
            )

    if existing_profiles:
        all_profile_names = additional_names
    else:
        all_profile_names = [default_profile_name] + additional_names

    configured_profiles = {}
    deferred_profiles = []

    for i, name in enumerate(all_profile_names):
        if i == 0 or not additional_names:
            profile_data = _setup_single_profile(name)
            configured_profiles[name] = profile_data
        else:
            if i == 1:
                click.echo()
                setup_now = click.confirm(
                    "would you like to set up the other profiles now?", default=False
                )

            if setup_now:
                profile_data = _setup_single_profile(name)
                configured_profiles[name] = profile_data
            else:
                deferred_profiles.append(name)

    final_profiles = dict(existing_profiles)
    final_profiles.update(configured_profiles)

    if renamed_from and renamed_from in final_profiles:
        final_profiles[default_profile_name] = final_profiles.pop(renamed_from)

    for name in deferred_profiles:
        if name not in final_profiles:
            final_profiles[name] = {}

    if renamed_from:
        active_profile = default_profile_name
    elif existing_profiles:
        active_profile = list(existing_profiles.keys())[0]
    else:
        active_profile = default_profile_name

    click.echo()
    click.secho("setup complete!", fg="green", bold=True)
    click.echo()

    configured_names = list(configured_profiles.keys())
    for name in configured_names:
        data = configured_profiles[name]
        
        markers = []
        if name == active_profile:
            markers.append("active")
        if renamed_from and name == default_profile_name:
            markers.append(f"renamed from '{renamed_from}'")
        
        header = f"  {name}"
        if markers:
            header += f" ({', '.join(markers)})"
        click.secho(header, bold=True)
        
        click.echo(f"    workspace: {data['archive_dir']}")
        if data.get("git_inherited"):
            click.echo("    git: inherited existing repository")
        else:
            click.echo(f"    git: {'yes' if data.get('init_git') else 'no'}")
        if data.get("git_remote"):
            click.echo(f"    remote: {data['git_remote']}")
        click.echo(f"    theme: {data.get('theme', 'light')}")
        click.echo()

    if deferred_profiles:
        click.echo(
            f"  other registered profiles: {', '.join(deferred_profiles)} "
            "(use --profile <name> to set up)"
        )
        click.echo()

    return {
        "profiles": final_profiles,
        "active_profile": active_profile,
    }


def setup_workspace(config: dict) -> None:
    """Create workspace directories based on config.

    Args:
        config: Profile configuration dict with archive_dir, init_git, etc.
    """
    archive_dir = Path(config.get("archive_dir", Path.home() / "Prosaic"))

    dirs = [
        archive_dir,
        archive_dir / "pieces",
        archive_dir / "books",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    notes = archive_dir / "notes.md"
    if not notes.exists():
        write_text(notes, "# Notes\n\n")

    metrics = archive_dir / "metrics.json"
    if not metrics.exists():
        write_text(metrics, '{"daily": {}, "sessions": []}')

    if config.get("init_git", True) and Repo is not None:
        git_dir = archive_dir / ".git"
        try:
            if git_dir.exists():
                repo = Repo(archive_dir)
            else:
                repo = Repo.init(archive_dir)

            remote_url = config.get("git_remote", "")
            if remote_url and not repo.remotes:
                try:
                    repo.create_remote("origin", remote_url)
                except Exception:
                    pass
        except Exception:
            pass
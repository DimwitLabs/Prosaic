"""Entry point for Prosaic."""

from pathlib import Path

import click
from textual.app import App
from textual.binding import Binding
from textual.screen import ModalScreen

from prosaic.config import (
    LANGUAGE_NAMES,
    VALID_LANGUAGE_CODES,
    ensure_workspace,
    get_active_profile,
    get_app_version,
    get_notes_path,
    get_profile_config,
    get_workspace_dir,
    load_config,
    needs_language_setup,
    profiles_needing_language_setup,
    save_config,
    save_profile_config,
    set_active_profile,
    set_last_file,
    set_spell_check_enabled,
    was_just_migrated,
)

from prosaic.core.metrics import MetricsTracker
from prosaic.screens import DashboardScreen, EditorScreen
from prosaic.themes import PROSAIC_DARK_CSS, PROSAIC_LIGHT_CSS
from prosaic.utils import read_text
from prosaic.widgets import LowercaseKeyPanel, SpellCheckTextArea
from prosaic.wizard import needs_setup, run_setup, setup_workspace


def _wrap_output(text: str) -> str:
    """Wrap text with equals line separators."""
    separator = "=" * 21
    return f"\n{separator}\n\n{text}\n{separator}\n"


def _get_reference_text() -> str:
    """Read REFERENCE file from package."""
    content = read_text(Path(__file__).parent / "REFERENCE")
    return _wrap_output(content)


def _get_license_text() -> str:
    """Read LICENSE file from package."""
    content = read_text(Path(__file__).parent / "LICENSE")
    return _wrap_output(content)


def _run_spell_setup(profile_name: str) -> None:
    """Run the one-time spell check setup for existing users upgrading to 1.5.0."""
    current_version = get_app_version()
    click.echo()
    click.secho(f"welcome to prosaic {current_version}!", fg="yellow", bold=True)
    click.echo(
        "this version brings a more powerful spell check with support for"
        " 80+ languages powered by hunspell."
    )
    click.echo()

    enable = click.confirm("enable spell check?", default=True)
    set_spell_check_enabled(enable, profile_name)

    if not enable:
        return

    click.echo()
    for code in sorted(VALID_LANGUAGE_CODES):
        name = LANGUAGE_NAMES.get(code, "")
        click.echo(f"  {code:<10}  {name}")
    click.echo()
    click.echo("you can also view this later with:  prosaic --languages")
    click.echo()
    while True:
        lang = click.prompt(
            f"language for '{profile_name}'",
            default="en_US",
            show_default=True,
        ).strip()
        if lang in VALID_LANGUAGE_CODES:
            click.secho(f"  {LANGUAGE_NAMES.get(lang, lang)}", fg="green")
            break
        click.secho(f"  unknown code '{lang}' — please enter a valid language code", fg="red")

    data = get_profile_config(profile_name)
    data["spell_language"] = lang
    save_profile_config(data, profile_name)

    others = [p for p in profiles_needing_language_setup() if p != profile_name]
    if others:
        click.echo()
        if click.confirm(f"configure other profiles now? ({', '.join(others)})", default=False):
            for other in others:
                click.echo()
                while True:
                    other_lang = click.prompt(
                        f"language for '{other}'",
                        default="en_US",
                        show_default=True,
                    ).strip()
                    if other_lang in VALID_LANGUAGE_CODES:
                        click.secho(f"  {LANGUAGE_NAMES.get(other_lang, other_lang)}", fg="green")
                        break
                    click.secho(f"  unknown code '{other_lang}' — please enter a valid language code", fg="red")
                other_data = get_profile_config(other)
                other_data["spell_language"] = other_lang
                save_profile_config(other_data, other)


class ProsaicApp(App):
    """Main Prosaic application."""

    TITLE = "prosaic"
    CSS = PROSAIC_LIGHT_CSS
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+q", "smart_quit", "quit", show=False, priority=True),
        Binding("ctrl+p", "toggle_keys", "key palette", priority=True),
        Binding("escape", "close_keys", "close", show=False, priority=True),
        Binding("up", "scroll_up", "scroll up", show=False),
        Binding("down", "scroll_down", "scroll down", show=False),
        Binding("left", "scroll_left", "scroll left", show=False),
        Binding("right", "scroll_right", "scroll right", show=False),
        Binding("home", "scroll_home", "scroll home", show=False),
        Binding("end", "scroll_end", "scroll end", show=False),
        Binding("pageup", "page_up", "page up", show=False),
        Binding("pagedown", "page_down", "page down", show=False),
        Binding("ctrl+pageup", "page_left", "page left", show=False),
        Binding("ctrl+pagedown", "page_right", "page right", show=False),
        Binding("tab", "focus_next", "focus next", show=False),
        Binding("shift+tab", "focus_previous", "focus previous", show=False),
    ]

    def __init__(
        self,
        light_mode: bool = True,
        initial_file: Path | None = None,
    ) -> None:
        super().__init__()
        self.light_mode = light_mode
        self.initial_file = initial_file
        self.notes_path = get_notes_path()
        ProsaicApp.CSS = PROSAIC_LIGHT_CSS if light_mode else PROSAIC_DARK_CSS

    def on_mount(self) -> None:
        ensure_workspace()
        self.metrics = MetricsTracker(get_workspace_dir())
        self.install_screen(DashboardScreen(self.metrics), name="dashboard")
        self.push_screen("dashboard")

        if self.initial_file:
            self._open_editor(self.initial_file)

    def _open_editor(self, file_path: Path | None = None, show_all_panes: bool = False) -> None:
        if file_path:
            set_last_file(file_path)

        self.push_screen(
            EditorScreen(
                self.metrics,
                initial_file=file_path,
                light_mode=self.light_mode,
                show_all_panes=show_all_panes,
            )
        )

    def toggle_theme(self) -> None:
        self.light_mode = not self.light_mode
        ProsaicApp.CSS = PROSAIC_LIGHT_CSS if self.light_mode else PROSAIC_DARK_CSS
        self.refresh_css(animate=False)

        try:
            screen = self.screen
            if isinstance(screen, EditorScreen):
                ta = screen.query_one("#editor", SpellCheckTextArea)
                ta.theme = "prosaic_light" if self.light_mode else "prosaic_dark"
                ta._build_highlight_map()
        except Exception:
            pass

    async def action_quit(self) -> None:
        self.exit()

    def action_smart_quit(self) -> None:
        """Close layers in sequence: KeyPanel > Modal > Screen."""
        screen = self.screen
        if screen.query("KeyPanel"):
            self.action_hide_help_panel()
            return
        if isinstance(screen, ModalScreen):
            if hasattr(screen, "action_cancel"):
                screen.action_cancel()
            elif hasattr(screen, "action_close"):
                screen.action_close()
            return
        if isinstance(screen, EditorScreen):
            screen.action_go_home()
        else:
            self.exit()

    def action_toggle_keys(self) -> None:
        """Toggle the key palette panel."""
        if self.screen.query("KeyPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    def action_close_keys(self) -> None:
        """Handle escape key: close KeyPanel, modal, or go back."""
        screen = self.screen
        if screen.query("KeyPanel"):
            self.action_hide_help_panel()
        elif isinstance(screen, ModalScreen):
            if hasattr(screen, "action_cancel"):
                screen.action_cancel()
            elif hasattr(screen, "action_close"):
                screen.action_close()
        elif hasattr(screen, "action_go_back"):
            screen.action_go_back()
        elif hasattr(screen, "action_go_home"):
            screen.action_go_home()
        elif hasattr(screen, "action_quit"):
            screen.action_quit()

    def action_show_help_panel(self) -> None:
        """Show help panel with lowercase bindings."""
        if not self.screen.query("KeyPanel"):
            self.screen.mount(LowercaseKeyPanel())

    def action_hide_help_panel(self) -> None:
        """Hide the help panel."""
        for panel in self.screen.query("KeyPanel"):
            panel.remove()


@click.command()
@click.option("--light/--dark", default=None, help="Use light or dark theme")
@click.option("--setup", is_flag=True, help="Run setup wizard again")
@click.option("--profile", default=None, help="Use a named profile (see --profiles)")
@click.option("--profiles", "show_profiles", is_flag=True, help="List available profiles")
@click.option("--languages", "show_languages", is_flag=True, help="List valid spell check language codes")
@click.option("--reference", is_flag=True, help="Show reference")
@click.option("--license", "show_license", is_flag=True, help="Show MIT license")
@click.argument("file", required=False, type=click.Path())
def main(
    light: bool | None,
    setup: bool,
    profile: str | None,
    show_profiles: bool,
    show_languages: bool,
    reference: bool,
    show_license: bool,
    file: str | None,
) -> None:
    """Prosaic - A writer-first terminal writing app."""
    if show_profiles:
        config = load_config()
        profiles = list(config.get("profiles", {}).keys())
        active = config.get("active_profile", "default")
        if profiles:
            click.echo("available profiles:")
            for name in profiles:
                marker = "*" if name == active else " "
                click.echo(f"  {marker} {name}")
            click.echo()
            click.echo("usage: prosaic --profile <name>")
        else:
            click.echo("no profiles configured. run: prosaic --setup")
        return

    if show_languages:
        click.echo("valid spell check language codes:")
        click.echo()
        for code in sorted(VALID_LANGUAGE_CODES):
            name = LANGUAGE_NAMES.get(code, "")
            click.echo(f"  {code:<10}  {name}")
        click.echo()
        click.echo("set language in manage profiles (m) or via  prosaic --profile <name>")
        return

    if reference:
        click.echo(_get_reference_text())
        return

    if show_license:
        click.echo(_get_license_text())
        return

    config = load_config()
    is_legacy_upgrade = was_just_migrated()
    profile_name = profile or config.get("active_profile", "default")
    set_active_profile(profile_name)

    current_version = get_app_version()

    if is_legacy_upgrade and not setup:
        click.echo()
        click.secho(f"hello from prosaic {current_version}!", fg="yellow", bold=True)
        click.echo()
        click.echo("looks like you just upgraded. we've automatically migrated")
        click.echo("your config to the new format and taken a backup just in case.")
        click.echo()
        click.echo("this version introduces profiles — separate workspaces for")
        click.echo("different writing projects (personal, work, fiction, etc.)")
        click.echo("your existing setup has been preserved as the 'default' profile.")
        click.echo()
        click.echo("you can always run  prosaic --setup  to configure more.")
        click.echo()
        run_profiles_setup = click.confirm("set up profiles now?", default=False)

        if not run_profiles_setup:
            click.echo()
            config["app_version"] = current_version
            save_config(config)
        else:
            setup = True

    existing_profiles = config.get("profiles", {})

    run_wizard = setup or needs_setup(profile_name)

    if run_wizard:
        if profile and not setup:
            result = run_setup(
                profile_name=profile_name,
                existing_profiles=existing_profiles,
                single_profile_mode=True,
            )
        else:
            result = run_setup(
                profile_name=profile_name,
                existing_profiles=existing_profiles if existing_profiles else None,
            )

        config["profiles"] = result["profiles"]
        config["active_profile"] = result["active_profile"]
        config["app_version"] = get_app_version()
        config["setup_complete"] = True

        save_config(config)

        for name, profile_data in result["profiles"].items():
            if profile_data.get("archive_dir"):
                setup_workspace(profile_data)

        set_active_profile(result["active_profile"])
        profile_name = result["active_profile"]

    if config.get("app_version") != current_version:
        config["app_version"] = current_version
        save_config(config)

    if needs_language_setup(profile_name):
        _run_spell_setup(profile_name)

    if light is None:
        profile_config = get_profile_config(get_active_profile())
        light_mode = profile_config.get("theme", "light") == "light"
    else:
        light_mode = light

    app = ProsaicApp(
        light_mode=light_mode,
        initial_file=Path(file) if file else None,
    )
    app.run()


if __name__ == "__main__":
    main()

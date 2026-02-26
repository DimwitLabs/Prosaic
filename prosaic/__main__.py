"""Entry point for Prosaic."""

from pathlib import Path

import click
from textual.app import App
from textual.binding import Binding

from prosaic.config import (
    ensure_workspace,
    get_notes_path,
    get_workspace_dir,
    save_config,
    set_last_file,
)
from prosaic.core.metrics import MetricsTracker
from prosaic.screens import DashboardScreen, EditorScreen
from prosaic.themes import PROSAIC_DARK_CSS, PROSAIC_LIGHT_CSS
from prosaic.widgets import LowercaseKeyPanel, SpellCheckTextArea
from prosaic.wizard import needs_setup, run_setup, setup_workspace


def _wrap_output(text: str) -> str:
    """Wrap text with equals line separators."""
    separator = "=" * 21
    return f"\n{separator}\n\n{text}\n{separator}\n"


def _get_reference_text() -> str:
    """Read REFERENCE file from package."""
    content = (Path(__file__).parent / "REFERENCE").read_text()
    return _wrap_output(content)


def _get_license_text() -> str:
    """Read LICENSE file from package."""
    content = (Path(__file__).parent / "LICENSE").read_text()
    return _wrap_output(content)


class ProsaicApp(App):
    """Main Prosaic application."""

    TITLE = "prosaic"
    CSS = PROSAIC_LIGHT_CSS
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+q", "smart_quit", "quit", show=False, priority=True),
        Binding("ctrl+p", "toggle_keys", "keys", priority=True),
        Binding("escape", "close_keys", "close", show=False),
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
        screen = self.screen
        if isinstance(screen, EditorScreen):
            screen.action_go_home()
        else:
            self.exit()

    def action_toggle_keys(self) -> None:
        if self.screen.query("KeyPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    def action_close_keys(self) -> None:
        if self.screen.query("KeyPanel"):
            self.action_hide_help_panel()

    def action_show_help_panel(self) -> None:
        """Show help panel with lowercase bindings."""
        if not self.screen.query("KeyPanel"):
            self.screen.mount(LowercaseKeyPanel())


@click.command()
@click.option("--light/--dark", default=True, help="Use light or dark theme")
@click.option("--setup", is_flag=True, help="Run setup wizard again")
@click.option("--reference", is_flag=True, help="Show reference")
@click.option("--license", "show_license", is_flag=True, help="Show MIT license")
@click.argument("file", required=False, type=click.Path())
def main(light: bool, setup: bool, reference: bool, show_license: bool, file: str | None) -> None:
    """Prosaic - A writer-first terminal writing app."""
    if reference:
        click.echo(_get_reference_text())
        return

    if show_license:
        click.echo(_get_license_text())
        return

    if setup or needs_setup():
        config = run_setup()
        save_config(config)
        setup_workspace(config)

    app = ProsaicApp(
        light_mode=light,
        initial_file=Path(file) if file else None,
    )
    app.run()


if __name__ == "__main__":
    main()

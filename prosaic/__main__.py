"""Entry point for Prosaic."""

from pathlib import Path

import click
from textual.app import App
from textual.binding import Binding

from prosaic.app import HelpScreen, NewBookModal, NewPieceModal
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
from prosaic.widgets import SpellCheckTextArea
from prosaic.wizard import needs_setup, run_setup, setup_workspace


class ProsaicApp(App):
    """Main Prosaic application."""

    TITLE = "prosaic"
    CSS = PROSAIC_LIGHT_CSS
    BINDINGS = [
        Binding("ctrl+q", "smart_quit", "quit", show=False, priority=True),
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

        if self.initial_file:
            self._open_editor(self.initial_file)
        else:
            self.push_screen("dashboard")

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

    def _open_notes(self) -> None:
        self.push_screen(
            EditorScreen(
                self.metrics,
                initial_file=self.notes_path,
                light_mode=self.light_mode,
                add_note=True,
            )
        )

    def _open_notes_readonly(self) -> None:
        self.push_screen(
            EditorScreen(
                self.metrics,
                initial_file=self.notes_path,
                light_mode=self.light_mode,
                reader_mode_initial=True,
            )
        )

    def _handle_new_piece(self, result: Path | None) -> None:
        if result:
            self._open_editor(result)

    def _handle_new_book(self, result: Path | None) -> None:
        if result:
            self._open_editor(result)

    def action_new_piece(self) -> None:
        self.push_screen(NewPieceModal(), callback=self._handle_new_piece)

    def action_new_book(self) -> None:
        self.push_screen(NewBookModal(), callback=self._handle_new_book)

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
        elif isinstance(screen, DashboardScreen):
            self.exit()
        elif len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.exit()


@click.command()
@click.option("--light/--dark", default=True, help="Use light or dark theme")
@click.option("--setup", is_flag=True, help="Run setup wizard again")
@click.argument("file", required=False, type=click.Path())
def main(light: bool, setup: bool, file: str | None) -> None:
    """Prosaic - A writer-first terminal writing app."""
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

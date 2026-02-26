"""Dashboard screen."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from prosaic.app import FileFindModal, HelpScreen, NewBookModal, NewPieceModal, StartWritingModal
from prosaic.config import get_last_file, set_last_file
from prosaic.core.metrics import MetricsTracker
from prosaic.screens.editor import EditorScreen

QUOTE = (
    "in these random impressions, and with no desire to be other than random, "
    "i indifferently narrate my fact-less autobiography, my lifeless history. "
    "these are my confessions, and if in them i say nothing, "
    "it's because i have nothing to say."
)
QUOTE_ATTR = "fernando pessoa, the book of disquiet"


class DashboardScreen(Screen, inherit_bindings=False):
    """Home screen with menu and daily stats."""

    BINDINGS = [
        Binding("tab", "app.focus_next", "focus next", show=False),
        Binding("shift+tab", "app.focus_previous", "focus previous", show=False),
        Binding("ctrl+c,super+c", "screen.copy_text", "copy", show=False),
        Binding("c", "continue_writing", "continue writing", show=False),
        Binding("s", "start_writing", "start writing"),
        Binding("p", "new_piece", "write a piece"),
        Binding("b", "new_book", "work on a book"),
        Binding("n", "add_note", "add a note"),
        Binding("r", "read_notes", "read notes"),
        Binding("f", "find_piece", "find files"),
        Binding("q", "quit", "quit"),
        Binding("f1", "show_help", "help"),
    ]

    def __init__(self, metrics: MetricsTracker, **kwargs) -> None:
        super().__init__(**kwargs)
        self.metrics = metrics
        self.last_file = get_last_file()

    def compose(self) -> ComposeResult:
        with Container(id="dashboard-container"):
            with Vertical(id="dashboard"):
                yield Static("prosaic", id="dashboard-title")

                with Vertical(id="dashboard-menu"):
                    with Horizontal(classes="menu-item", id="continue-item"):
                        yield Static(
                            "continue writing",
                            classes="menu-label",
                        )
                        yield Static("(c)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("start writing", classes="menu-label")
                        yield Static("(s)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("write a piece", classes="menu-label")
                        yield Static("(p)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("work on a book", classes="menu-label")
                        yield Static("(b)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("add a note", classes="menu-label")
                        yield Static("(n)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("read notes", classes="menu-label")
                        yield Static("(r)", classes="menu-key")
                    with Horizontal(classes="menu-item"):
                        yield Static("find files", classes="menu-label")
                        yield Static("(f)", classes="menu-key")

                stats = self.metrics.get_today_stats()
                yield Static(
                    f"{stats['words']:,} words",
                    id="dashboard-stats",
                )

                yield Static("", id="dashboard-separator")
                yield Static(QUOTE, id="dashboard-quote")
                yield Static(QUOTE_ATTR, id="dashboard-quote-attr")
                yield Static("help (f1)   quit (q)", id="dashboard-footer")

    def on_mount(self) -> None:
        """Hide continue item if no last file."""
        if not self.last_file:
            self.query_one("#continue-item").display = False

    def on_screen_resume(self) -> None:
        """Refresh stats and continue item when returning to dashboard."""
        stats = self.metrics.get_today_stats()
        stats_widget = self.query_one("#dashboard-stats", Static)
        stats_widget.update(f"{stats['words']:,} words")

        self.last_file = get_last_file()
        continue_item = self.query_one("#continue-item")
        continue_item.display = self.last_file is not None

    def _make_open_callback(self, show_all_panes: bool = False):
        """Create a callback that opens the editor with the result."""
        def callback(result: Path | None) -> None:
            if result:
                self.app._open_editor(result, show_all_panes=show_all_panes)
        return callback

    def action_new_piece(self) -> None:
        self.app.push_screen(NewPieceModal(), callback=self._make_open_callback())

    def action_new_book(self) -> None:
        self.app.push_screen(NewBookModal(), callback=self._make_open_callback())

    def action_continue_writing(self) -> None:
        if self.last_file and self.last_file.exists():
            self.app._open_editor(self.last_file)

    def action_start_writing(self) -> None:
        self.app.push_screen(StartWritingModal(), callback=self._make_open_callback(show_all_panes=True))

    def action_add_note(self) -> None:
        self.app.push_screen(
            EditorScreen(
                self.metrics,
                initial_file=self.app.notes_path,
                light_mode=self.app.light_mode,
                add_note=True,
            )
        )

    def action_read_notes(self) -> None:
        self.app.push_screen(
            EditorScreen(
                self.metrics,
                initial_file=self.app.notes_path,
                light_mode=self.app.light_mode,
                reader_mode_initial=True,
            )
        )

    def action_find_piece(self) -> None:
        self.app.push_screen(FileFindModal(), callback=self._handle_find_result)

    def _handle_find_result(self, result: Path | None) -> None:
        if result:
            set_last_file(result)
            self.app.push_screen(
                EditorScreen(
                    self.metrics,
                    initial_file=result,
                    light_mode=self.app.light_mode,
                )
            )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_quit(self) -> None:
        self.app.exit()

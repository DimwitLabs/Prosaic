"""Prosaic modals and dialogs."""

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from prosaic.config import get_books_dir, get_pieces_dir, get_workspace_dir
from prosaic.utils import write_text

HELP_TEXT = """
shortcuts

navigation
  tab       next
  shift+tab previous

dashboard
  s         start writing
  p         write a piece
  b         work on a book
  n         add a note
  r         read notes
  f         find files
  f1        help
  q         quit
  ctrl+p    keys

editor
  ctrl+e    toggle file tree
  ctrl+o    toggle outline
  ctrl+s    save
  ctrl+q    go home
  ctrl+p    keys
  f1        help
  f5        focus mode
  f6        reader mode

editing
  ctrl+z    undo
  ctrl+y    redo
  ctrl+x    cut
  ctrl+c    copy
  ctrl+v    paste
  ctrl+a    select all
  ctrl+k    toggle comment

status
  ○ / ●     autosave (idle / saved)
  [+] / [·] editor (unsaved / saved)
  * / + / ? git (modified / staged / untracked)

press escape or q to close
"""


class CreateFileModal(ModalScreen[Path | None]):
    """Base modal for creating files."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+q", "cancel", "cancel", show=False, priority=True),
    ]

    TITLE: str = ""
    PROMPT: str = "enter a title (or leave blank for timestamp):"
    PLACEHOLDER: str = "my-file"

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.TITLE, id="dialog-title")
            yield Static(self.PROMPT)
            yield Input(placeholder=self.PLACEHOLDER, id="title-input")

    def on_mount(self) -> None:
        self.query_one("#title-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._create_file()

    def _slugify(self, title: str) -> str:
        """Convert title to filename slug."""
        slug = title.lower().replace(" ", "-")
        return "".join(c for c in slug if c.isalnum() or c == "-")

    def _get_filename(self, title: str) -> str:
        """Generate filename from title or timestamp."""
        if title:
            return f"{self._slugify(title)}.md"
        return datetime.now().strftime("%Y%m%d%H%M%S") + ".md"

    def _get_target_dir(self) -> Path:
        """Return directory to create file in. Override in subclass."""
        return get_workspace_dir()

    def _get_initial_content(self, title: str) -> str:
        """Return initial file content. Override in subclass."""
        return ""

    def _create_file(self) -> None:
        title = self.query_one("#title-input", Input).value.strip()
        target_dir = self._get_target_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / self._get_filename(title)
        write_text(file_path, self._get_initial_content(title))
        self.dismiss(file_path)

    def action_cancel(self) -> None:
        self.dismiss(None)


class NewPieceModal(CreateFileModal):
    """Modal for creating a new piece."""

    TITLE = "write a piece"
    PLACEHOLDER = "my-new-piece"

    def _get_target_dir(self) -> Path:
        return get_pieces_dir()

    def _get_initial_content(self, title: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug_str = self._slugify(title) if title else datetime.now().strftime("%Y%m%d%H%M%S")
        return f'''---
title: "{title}"
date: {date_str}
slug: {slug_str}
---

'''


class StartWritingModal(CreateFileModal):
    """Modal for starting a writing session."""

    TITLE = "start writing"
    PROMPT = "enter a filename (or leave blank for timestamp):"
    PLACEHOLDER = "my-document"


class NewBookModal(CreateFileModal):
    """Modal for creating a new book."""

    TITLE = "work on a book"
    PLACEHOLDER = "my-new-book"

    def _get_target_dir(self) -> Path:
        return get_books_dir()

    def _get_initial_content(self, title: str) -> str:
        return f"# {title}\n\n" if title else ""


class _FileItem(ListItem):
    """List item carrying a Path reference."""

    def __init__(self, path: Path, workspace: Path) -> None:
        filename = path.stem

        if path.name == "notes.md":
            file_type = "n"
        else:
            try:
                rel_path = path.relative_to(workspace)
                parts = rel_path.parts
                if len(parts) > 1:
                    folder = parts[0]
                    if folder == "pieces":
                        file_type = "p"
                    elif folder == "books":
                        file_type = "b"
                    else:
                        file_type = "d"
                else:
                    file_type = "d"
            except ValueError:
                file_type = ""

        if file_type:
            display = f"{filename} • {file_type}"
        else:
            display = filename
        super().__init__(Label(display))
        self.path = path


class FileFindModal(ModalScreen[Path | None]):
    """Modal for finding files."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+q", "cancel", "cancel", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="find-dialog"):
            yield Static("find files", id="dialog-title")
            yield Input(placeholder="type to filter...", id="find-input")
            yield ListView(id="find-list")
            yield Static("(b)ook • (d)raft • (n)ote • (p)iece", id="find-legend")

    def on_mount(self) -> None:
        self.query_one("#find-input", Input).focus()
        self._refresh_list("")

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_list(event.value.strip())

    def _refresh_list(self, query: str) -> None:
        workspace_dir = get_workspace_dir()
        find_list = self.query_one("#find-list", ListView)
        find_list.clear()

        if not workspace_dir.exists():
            return

        files = sorted(
            workspace_dir.rglob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if query:
            files = [f for f in files if query.lower() in f.stem.lower()]

        for f in files[:20]:
            find_list.append(_FileItem(f, workspace_dir))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _FileItem):
            self.dismiss(event.item.path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        find_list = self.query_one("#find-list", ListView)
        idx = find_list.index
        items = list(find_list.query(_FileItem))
        if idx is not None and 0 <= idx < len(items):
            self.dismiss(items[idx].path)
        elif items:
            self.dismiss(items[0].path)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen):
    """Help screen showing keybindings."""

    BINDINGS = [
        Binding("escape", "close", "close"),
        Binding("q", "close", "close", show=False),
        Binding("ctrl+q", "close", "close", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(HELP_TEXT.strip())

    def action_close(self) -> None:
        self.dismiss()


__all__ = ["FileFindModal", "HelpScreen", "NewBookModal", "NewPieceModal", "StartWritingModal"]

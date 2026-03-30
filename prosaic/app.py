"""Prosaic modals and dialogs."""

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from prosaic.config import get_books_dir, get_pieces_dir, get_workspace_dir
from prosaic.core.book import (
    compile_manuscript,
    create_book_structure,
    get_all_books,
    get_book_title,
    get_chapters,
    is_new_format,
    migrate_legacy_book,
)
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
  ctrl+m    compile manuscript
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

    def _strip_md_extension(self, title: str) -> str:
        """Strip .md extension if user included it."""
        if title.lower().endswith(".md"):
            return title[:-3]
        return title

    def _get_filename(self, title: str) -> str:
        """Generate filename from title or timestamp."""
        if title:
            title = self._strip_md_extension(title)
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
        if file_path.exists():
            self.notify(f"File already exists: {file_path.name}", severity="error")
            return
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
    """Modal for creating a new book (directory structure)."""

    TITLE = "new book"
    PLACEHOLDER = "my-new-book"

    def _create_file(self) -> None:
        title = self.query_one("#title-input", Input).value.strip()
        books_dir = get_books_dir()
        books_dir.mkdir(parents=True, exist_ok=True)
        book_dir = create_book_structure(books_dir, title)
        self.dismiss(book_dir)


class _BookItem(ListItem):
    """List item carrying a book Path reference."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.is_create_new = False
        if is_new_format(path):
            label = get_book_title(path)
        else:
            label = f"{path.stem} (legacy)"
        super().__init__(Label(label))


class _CreateNewBookItem(ListItem):
    """Sentinel list item for creating a new book."""

    def __init__(self) -> None:
        self.path = None
        self.is_create_new = True
        super().__init__(Label("+ create new book"))


class BookSelectModal(ModalScreen[Path | None]):
    """Modal for selecting or creating a book."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+q", "cancel", "cancel", show=False, priority=True),
        Binding("m", "migrate", "migrate", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="find-dialog"):
            yield Static("work on a book", id="dialog-title")
            yield Input(placeholder="filter books...", id="find-input")
            yield ListView(id="find-list")
            yield Static("(m) migrate legacy  •  (esc) cancel", id="find-legend")

    def on_mount(self) -> None:
        self.query_one("#find-input", Input).focus()
        self._refresh_list("")

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_list(event.value.strip())

    def _refresh_list(self, query: str) -> None:
        find_list = self.query_one("#find-list", ListView)
        find_list.clear()
        find_list.append(_CreateNewBookItem())
        books = get_all_books(get_books_dir())
        if query:
            books = [b for b in books if query.lower() in b.stem.lower()]
        for book in books:
            find_list.append(_BookItem(book))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, _CreateNewBookItem):
            def _on_created(book_dir: Path | None) -> None:
                if book_dir:
                    self.dismiss(book_dir)
            self.app.push_screen(NewBookModal(), callback=_on_created)
        elif isinstance(item, _BookItem):
            self.dismiss(item.path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        find_list = self.query_one("#find-list", ListView)
        idx = find_list.index
        items = list(find_list.query(ListItem))
        if idx is not None and 0 <= idx < len(items):
            selected = items[idx]
        elif items:
            selected = items[0]
        else:
            self.dismiss(None)
            return

        if isinstance(selected, _CreateNewBookItem):
            def _on_created(book_dir: Path | None) -> None:
                if book_dir:
                    self.dismiss(book_dir)
            self.app.push_screen(NewBookModal(), callback=_on_created)
        elif isinstance(selected, _BookItem):
            self.dismiss(selected.path)

    def action_migrate(self) -> None:
        find_list = self.query_one("#find-list", ListView)
        idx = find_list.index
        items = list(find_list.query(ListItem))
        if idx is None or idx >= len(items):
            return
        item = items[idx]
        if not isinstance(item, _BookItem) or item.path is None:
            return
        if is_new_format(item.path):
            self.notify("Already in new format")
            return
        try:
            migrate_legacy_book(item.path)
            self.notify(f"Migrated '{item.path.stem}' to new format")
            self._refresh_list(self.query_one("#find-input", Input).value.strip())
        except Exception as exc:
            self.notify(f"Migration failed: {exc}", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(None)


class _ChapterItem(ListItem):
    """List item carrying a chapter file Path."""

    def __init__(self, path: Path, label: str | None = None) -> None:
        self.path = path
        super().__init__(Label(label or path.name))


class ChapterSelectModal(ModalScreen[Path | None]):
    """Modal for selecting or creating a chapter within a book."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+q", "cancel", "cancel", show=False, priority=True),
        Binding("m", "compile", "compile", show=False),
        Binding("ctrl+m", "compile", "compile", show=False, priority=True),
    ]

    def __init__(self, book_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._book_dir = book_dir

    def compose(self) -> ComposeResult:
        title = get_book_title(self._book_dir).title()
        with Vertical(id="find-dialog"):
            yield Static(title, id="dialog-title")
            yield ListView(id="find-list")
            yield Static(
                "(m) compile manuscript  •  (esc) back",
                id="find-legend",
            )

    def on_mount(self) -> None:
        self._refresh_list()
        self.query_one("#find-list", ListView).focus()

    def _refresh_list(self) -> None:
        find_list = self.query_one("#find-list", ListView)
        find_list.clear()
        find_list.append(_ChapterItem(
            self._book_dir / "chapters" / "__new__",
            label="+ create new chapter",
        ))
        chapters_md = self._book_dir / "chapters.md"
        manuscript_md = self._book_dir / "manuscript.md"
        if chapters_md.exists():
            find_list.append(_ChapterItem(chapters_md, label="chapters.md — edit order"))
        if manuscript_md.exists():
            find_list.append(_ChapterItem(manuscript_md, label="manuscript.md — read only"))
        for chapter in get_chapters(self._book_dir):
            find_list.append(_ChapterItem(chapter))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, _ChapterItem):
            return
        if item.path.name == "__new__":
            def _on_created(chapter_path: Path | None) -> None:
                if chapter_path:
                    self.dismiss(chapter_path)
            self.app.push_screen(
                NewChapterModal(self._book_dir),
                callback=_on_created,
            )
        else:
            self.dismiss(item.path)

    def action_compile(self) -> None:
        try:
            compile_manuscript(self._book_dir)
            self.notify("Manuscript compiled")
        except Exception as exc:
            self.notify(f"Compile failed: {exc}", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(None)


class NewChapterModal(CreateFileModal):
    """Modal for creating a new chapter within a book."""

    TITLE = "new chapter"
    PLACEHOLDER = "chapter-title"

    def __init__(self, book_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._book_dir = book_dir

    def _get_target_dir(self) -> Path:
        return self._book_dir / "chapters"

    def _get_initial_content(self, title: str) -> str:
        heading = title.replace("-", " ").title() if title else "New Chapter"
        return f"## {heading}\n\n"

    def _create_file(self) -> None:
        title = self.query_one("#title-input", Input).value.strip()
        target_dir = self._get_target_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / self._get_filename(title)
        if file_path.exists():
            self.notify(f"File already exists: {file_path.name}", severity="error")
            return
        write_text(file_path, self._get_initial_content(title))

        # Append to chapters.md if not already listed
        chapters_file = self._book_dir / "chapters.md"
        if chapters_file.exists():
            existing = chapters_file.read_text(encoding="utf-8")
            if file_path.name not in existing.splitlines():
                chapters_file.write_text(
                    existing.rstrip("\n") + "\n" + file_path.name + "\n",
                    encoding="utf-8",
                )
        else:
            write_text(chapters_file, file_path.name + "\n")

        self.dismiss(file_path)


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


__all__ = [
    "BookSelectModal",
    "ChapterSelectModal",
    "FileFindModal",
    "HelpScreen",
    "NewBookModal",
    "NewChapterModal",
    "NewPieceModal",
    "StartWritingModal",
]

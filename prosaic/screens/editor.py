"""Editor screen."""

import asyncio
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Static, TextArea

from prosaic.app import HelpScreen
from prosaic.config import get_books_dir, get_workspace_dir
from prosaic.core import count_characters, count_words
from prosaic.core.metrics import MetricsTracker
from prosaic.utils import read_text, write_text
from prosaic.widgets import FileTree, OutlinePanel, SpellCheckTextArea, StatusBar


class EditorScreen(Screen, inherit_bindings=False):
    """Main writing screen with editor, file tree, and outline."""

    BINDINGS = [
        Binding("tab", "app.focus_next", "focus next", show=False),
        Binding("shift+tab", "app.focus_previous", "focus previous", show=False),
        Binding("ctrl+c,super+c", "screen.copy_text", "copy", show=False),
        Binding("ctrl+e", "toggle_tree", "tree", priority=True),
        Binding("ctrl+s", "save", "save", priority=True),
        Binding("ctrl+m", "compile_manuscript", "compile", show=False, priority=True),
        Binding("ctrl+o", "toggle_outline", "outline"),
        Binding("f5", "toggle_focus", "focus mode"),
        Binding("f6", "toggle_reader", "reader mode"),
        Binding("f1", "show_help", "help"),
    ]

    show_tree: reactive[bool] = reactive(True)
    show_outline: reactive[bool] = reactive(False)
    focus_mode: reactive[bool] = reactive(False)
    reader_mode: reactive[bool] = reactive(False)
    current_file: reactive[Path | None] = reactive(None)
    modified: reactive[bool] = reactive(False)

    def __init__(
        self,
        metrics: MetricsTracker,
        initial_file: Path | None = None,
        light_mode: bool = True,
        add_note: bool = False,
        reader_mode_initial: bool = False,
        show_all_panes: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.metrics = metrics
        self._initial_file = initial_file
        self._light_mode = light_mode
        self._add_note = add_note
        self._reader_mode_initial = reader_mode_initial
        self._show_all_panes = show_all_panes
        self._is_book = False
        self._is_chapter = False
        self._is_manuscript = False
        self._book_dir: Path | None = None

    def compose(self) -> ComposeResult:
        ta_theme = "prosaic_light" if self._light_mode else "prosaic_dark"
        with Horizontal(id="editor-layout"):
            yield FileTree(get_workspace_dir(), id="file-tree")
            with Vertical(id="editor-container"):
                yield SpellCheckTextArea(
                    id="editor",
                    language="markdown",
                    soft_wrap=True,
                    theme=ta_theme,
                )
            outline = OutlinePanel(id="outline")
            outline.display = False
            yield outline
        yield StatusBar(id="statusbar")

    def on_mount(self) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.focus()
        self.set_interval(10, self._autosave)

        if self._initial_file and self._initial_file.exists():
            self._load_file(self._initial_file)
            books_dir = get_books_dir()
            try:
                rel = self._initial_file.relative_to(books_dir)
                parts = rel.parts
                if len(parts) >= 3 and parts[1] == "chapters":
                    self._is_chapter = True
                    self._book_dir = books_dir / parts[0]
                elif len(parts) == 2 and parts[1] == "manuscript.md":
                    self._is_manuscript = True
                    self._book_dir = books_dir / parts[0]
                else:
                    self._is_book = True
            except ValueError:
                pass

        if self._reader_mode_initial or self._is_manuscript:
            self.reader_mode = True
        elif self._is_chapter:
            self.show_tree = True
            self.show_outline = False
        elif self._add_note or self._is_book:
            self.show_tree = False
            self.show_outline = True
        elif self._show_all_panes:
            self.show_tree = True
            self.show_outline = True
        else:
            self.show_tree = True
            self.show_outline = False

    def _load_file(self, path: Path) -> None:
        if not path.exists():
            return

        content = read_text(path)

        if self._add_note:
            heading = datetime.now().strftime("## %Y-%m-%d %H:%M")
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"\n{heading}\n\n"
            write_text(path, content)

        editor = self.query_one("#editor", TextArea)
        editor.load_text(content)

        if self._add_note:
            lines = content.split("\n")
            editor.move_cursor((len(lines) - 1, 0))

        self.current_file = path
        self.modified = False

        outline = self.query_one("#outline", OutlinePanel)
        outline.update_headings(content)

        statusbar = self.query_one("#statusbar", StatusBar)
        statusbar.filename = path.name
        statusbar.modified = False
        statusbar.update_git_for_file(path)

        self._update_stats(content)
        self.metrics.set_baseline(count_words(content))
        # Delay expand to let tree finish loading
        self.set_timer(0.1, self._expand_to_current_file)

    def _expand_to_current_file(self) -> None:
        """Expand the file tree to show the current file."""
        if not self.current_file:
            return
        file_tree = self.query_one("#file-tree", FileTree)
        file_tree.expand_path(self.current_file.parent)

    def _save_file(self, silent: bool = False) -> None:
        if self.current_file is None:
            return

        editor = self.query_one("#editor", TextArea)
        content = editor.text
        write_text(self.current_file, content)
        self.modified = False
        self.metrics.record_save(count_words(content), self.current_file)

        if not silent:
            self.notify(f"Saved {self.current_file.name}")

        if self._is_chapter and self._book_dir:
            from prosaic.core.book import compile_manuscript
            try:
                compile_manuscript(self._book_dir)
            except Exception:
                pass

    async def _autosave(self) -> None:
        """Autosave current file in background."""
        if self.current_file is None or not self.modified:
            return

        try:
            editor = self.query_one("#editor", TextArea)
            content = editor.text
            file_path = self.current_file

            await asyncio.to_thread(write_text, file_path, content)

            self.modified = False
            self.metrics.record_save(count_words(content), file_path)

            statusbar = self.query_one("#statusbar", StatusBar)
            statusbar.flash_autosave()
            self.call_later(lambda: statusbar.update_git_for_file(file_path))
        except Exception:
            pass

    def _update_stats(self, content: str) -> None:
        words = count_words(content)
        chars = count_characters(content)
        try:
            statusbar = self.query_one("#statusbar", StatusBar)
            statusbar.words = words
            statusbar.characters = chars
        except Exception:
            pass

    def watch_show_tree(self, show: bool) -> None:
        self.query_one("#file-tree", FileTree).display = show

    def watch_show_outline(self, show: bool) -> None:
        self.query_one("#outline", OutlinePanel).display = show

    def watch_focus_mode(self, focus: bool) -> None:
        if focus:
            self.add_class("focus-mode")
            self.show_tree = False
            self.show_outline = False
        else:
            self.remove_class("focus-mode")
            if not self.reader_mode:
                self._restore_panes()

    def watch_reader_mode(self, reader: bool) -> None:
        editor = self.query_one("#editor", TextArea)
        if reader:
            self.add_class("reader-mode")
            if self._reader_mode_initial or self._is_manuscript:
                self.show_tree = False
                self.show_outline = True
            else:
                self.show_tree = False
                self.show_outline = False
            editor.read_only = True
        else:
            self.remove_class("reader-mode")
            if not self.focus_mode:
                self._restore_panes()
            editor.read_only = False

    def _restore_panes(self) -> None:
        """Restore pane visibility based on context."""
        if self._is_chapter:
            self.show_tree = True
            self.show_outline = False
        elif self._add_note or self._is_book or self._reader_mode_initial or self._is_manuscript:
            self.show_tree = False
            self.show_outline = True
        elif self._show_all_panes:
            self.show_tree = True
            self.show_outline = True
        else:
            self.show_tree = True
            self.show_outline = False

    def watch_current_file(self, path: Path | None) -> None:
        try:
            statusbar = self.query_one("#statusbar", StatusBar)
            statusbar.filename = path.name if path else "untitled"
        except Exception:
            pass

    def watch_modified(self, modified: bool) -> None:
        try:
            statusbar = self.query_one("#statusbar", StatusBar)
            statusbar.modified = modified
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self.modified = True
        content = event.text_area.text
        self.query_one("#outline", OutlinePanel).update_headings(content)
        self._update_stats(content)

    def on_file_tree_file_selected(self, event: FileTree.FileSelected) -> None:
        if event.path.suffix == ".md":
            if self.modified:
                self._save_file(silent=True)
            self._load_file(event.path)

    def on_outline_panel_heading_selected(
        self,
        event: OutlinePanel.HeadingSelected,
    ) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.move_cursor((event.line - 1, 0))
        editor.focus()

    def action_toggle_tree(self) -> None:
        self.show_tree = not self.show_tree

    def action_toggle_outline(self) -> None:
        self.show_outline = not self.show_outline

    def action_toggle_focus(self) -> None:
        if self.focus_mode:
            self.focus_mode = False
            self.notify("Focus mode off")
        else:
            self.focus_mode = True
            self.reader_mode = False
            self.notify("Focus mode on")

    def action_toggle_reader(self) -> None:
        if self.reader_mode:
            self.reader_mode = False
            self.notify("Reader mode off")
        else:
            self.reader_mode = True
            self.focus_mode = False
            self.notify("Reader mode on")

    def action_save(self) -> None:
        self._save_file()

    def action_go_home(self) -> None:
        if self.modified:
            self._save_file(silent=True)
        elif self._is_chapter and self._book_dir:
            from prosaic.core.book import compile_manuscript
            try:
                compile_manuscript(self._book_dir)
            except Exception:
                pass
        self.app.pop_screen()

    def action_compile_manuscript(self) -> None:
        if self._book_dir:
            from prosaic.core.book import compile_manuscript
            try:
                compile_manuscript(self._book_dir)
                self.notify("Manuscript compiled")
            except Exception as exc:
                self.notify(f"Compile failed: {exc}", severity="error")

    def on_unmount(self) -> None:
        if self.modified and self.current_file:
            try:
                editor = self.query_one("#editor", TextArea)
                write_text(self.current_file, editor.text)
                if self._is_chapter and self._book_dir:
                    from prosaic.core.book import compile_manuscript
                    compile_manuscript(self._book_dir)
            except Exception:
                pass

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

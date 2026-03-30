"""File tree widget for workspace navigation."""

from collections.abc import Iterable
from pathlib import Path

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DirectoryTree, Static


class FilteredDirectoryTree(DirectoryTree, inherit_bindings=False):
    """Directory tree with emoji-free labels and hidden-file filtering."""

    HIDDEN_FILES = {".git", ".DS_Store", "metrics.json", "__pycache__"}

    BINDINGS = [
        Binding("enter", "select_cursor", "open"),
        Binding("space", "toggle_node", "expand"),
        Binding("shift+left", "cursor_parent", "cursor to parent", show=False),
        Binding("shift+right", "cursor_parent_next_sibling", "cursor to next ancestor", show=False),
        Binding("shift+up", "cursor_previous_sibling", "cursor to previous sibling", show=False),
        Binding("shift+down", "cursor_next_sibling", "cursor to next sibling", show=False),
        Binding("shift+space", "toggle_expand_all", "expand or collapse all", show=False),
        Binding("up", "cursor_up", "cursor up", show=False),
        Binding("down", "cursor_down", "cursor down", show=False),
    ]

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [
            path
            for path in paths
            if path.name not in self.HIDDEN_FILES and not path.name.startswith(".")
        ]

    def render_label(self, node, base_style, style):
        label = (
            node._label.plain if hasattr(node._label, "plain") else str(node._label)
        )
        if node._allow_expand:
            prefix = "▾ " if node.is_expanded else "▸ "
        else:
            prefix = "  "
        return Text.assemble((prefix, base_style), (label, style))


class FileTree(Vertical):
    """File tree panel for the workspace."""

    class FileSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.root = root

    def compose(self):
        yield Static("files", id="tree-title", classes="panel-title")
        yield FilteredDirectoryTree(self.root, id="directory-tree")

    def expand_path(self, path: Path) -> None:
        """Expand directories leading to the given path."""
        tree = self.query_one("#directory-tree", FilteredDirectoryTree)
        
        try:
            rel_parts = path.relative_to(self.root).parts
        except ValueError:
            return
        
        dirs_to_expand: list[Path] = []
        current = self.root
        for part in rel_parts:
            current = current / part
            if current.is_dir():
                dirs_to_expand.append(current)
        
        self._pending_expands = dirs_to_expand
        self._do_expand_step(tree.root)
    
    def _do_expand_step(self, node) -> None:
        """Expand one level, then schedule next."""
        if not hasattr(self, "_pending_expands") or not self._pending_expands:
            return
        
        target = self._pending_expands[0]
        
        if node.is_collapsed:
            node.expand()
            self.set_timer(0.05, lambda: self._do_expand_step(node))
            return
        
        for child in node.children:
            if hasattr(child, "data") and child.data and hasattr(child.data, "path"):
                if child.data.path == target:
                    self._pending_expands.pop(0)
                    if self._pending_expands:
                        self._do_expand_step(child)
                    else:
                        child.expand()
                    return

    def on_directory_tree_file_selected(
        self,
        event: DirectoryTree.FileSelected,
    ) -> None:
        self.post_message(self.FileSelected(event.path))

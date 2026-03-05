"""Status bar widget."""

from pathlib import Path

from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

try:
    from git import InvalidGitRepositoryError, Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None
    InvalidGitRepositoryError = Exception


def get_git_status(file_path: Path | None) -> str:
    """Get git status for a file."""
    if not GIT_AVAILABLE or file_path is None or Repo is None:
        return ""

    try:
        repo = Repo(file_path.parent, search_parent_directories=True)
        if repo.bare:
            return ""

        try:
            branch = repo.active_branch.name
        except TypeError:
            return ""

        try:
            rel_path = str(file_path.relative_to(Path(repo.working_dir)))
        except ValueError:
            return branch

        if not repo.head.is_valid():
            if rel_path in repo.untracked_files:
                return f"{branch} ?"
            return branch

        if rel_path in [d.a_path for d in repo.index.diff(None)]:
            return f"{branch} *"
        elif rel_path in [d.a_path for d in repo.index.diff("HEAD")]:
            return f"{branch} +"
        elif rel_path in repo.untracked_files:
            return f"{branch} ?"
        else:
            return branch
    except (InvalidGitRepositoryError, Exception):
        return ""


class StatusBar(Horizontal):
    """Status bar showing file info, git status, and stats."""

    filename: reactive[str] = reactive("untitled")
    words: reactive[int] = reactive(0)
    characters: reactive[int] = reactive(0)
    modified: reactive[bool] = reactive(False)
    git_status: reactive[str] = reactive("")

    def compose(self):
        yield Static("○", id="autosave")
        yield Static("untitled", id="filename")
        yield Static("", id="modified")
        yield Static("", id="git")
        yield Static("", classes="spacer")
        yield Static("0 words", id="word-count")
        yield Static("·", classes="sep")
        yield Static("0 chars", id="char-count")

    def on_mount(self) -> None:
        self._refresh_all()

    def _refresh_all(self) -> None:
        try:
            self.query_one("#filename", Static).update(self.filename)
            self.query_one("#modified", Static).update(
                " [+]" if self.modified else " [·]"
            )
            self.query_one("#git", Static).update(
                f"  {self.git_status}" if self.git_status else ""
            )
            self.query_one("#word-count", Static).update(f"{self.words:,} words")
            self.query_one("#char-count", Static).update(f"{self.characters:,} chars")
        except Exception:
            pass

    def watch_filename(self, filename: str) -> None:
        try:
            self.query_one("#filename", Static).update(filename)
        except Exception:
            pass

    def watch_modified(self, modified: bool) -> None:
        try:
            self.query_one("#modified", Static).update(" [+]" if modified else " [·]")
        except Exception:
            pass

    def watch_git_status(self, status: str) -> None:
        try:
            self.query_one("#git", Static).update(f"  {status}" if status else "")
        except Exception:
            pass

    def watch_words(self, words: int) -> None:
        try:
            self.query_one("#word-count", Static).update(f"{words:,} words")
        except Exception:
            pass

    def watch_characters(self, chars: int) -> None:
        try:
            self.query_one("#char-count", Static).update(f"{chars:,} chars")
        except Exception:
            pass

    def update_git_for_file(self, file_path: Path | None) -> None:
        self.git_status = get_git_status(file_path)

    def flash_autosave(self) -> None:
        """Briefly show autosave indicator."""
        try:
            indicator = self.query_one("#autosave", Static)
            indicator.update("●")
            self.set_timer(1.5, lambda: indicator.update("○"))
        except Exception:
            pass

"""Custom KeyPanel with lowercase binding descriptions."""

from textual.binding import Binding
from textual.widgets._key_panel import KeyPanel


class LowercaseKeyPanel(KeyPanel, inherit_bindings=False):
    """KeyPanel subclass with lowercase binding descriptions."""

    BINDINGS = [
        Binding("escape", "close_panel", "close", show=False, priority=True),
        Binding("ctrl+q", "close_panel", "close", show=False, priority=True),
        Binding("up", "scroll_up", "scroll up", show=False),
        Binding("down", "scroll_down", "scroll down", show=False),
        Binding("left", "scroll_left", "scroll left", show=False),
        Binding("right", "scroll_right", "scroll right", show=False),
        Binding("home", "scroll_home", "scroll home", show=False),
        Binding("end", "scroll_end", "scroll end", show=False),
        Binding("pageup", "page_up", "page up", show=False),
        Binding("pagedown", "page_down", "page down", show=False),
        Binding("ctrl+pageup", "page_left", "page left", show=False),
        Binding("ctrl+pagedown", "page_right", "page_right", show=False),
    ]

    def action_close_panel(self) -> None:
        """Close this panel."""
        self.app.action_hide_help_panel()

"""Outline panel showing document headings."""

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from prosaic.core.markdown import Heading, extract_headings


class OutlineListView(ListView, inherit_bindings=False):
    """ListView with visible lowercase bindings."""

    BINDINGS = [
        Binding("enter", "select_cursor", "go to"),
        Binding("up", "cursor_up", "up", show=False),
        Binding("down", "cursor_down", "down", show=False),
    ]


class OutlineItem(ListItem):
    """A single item in the outline."""

    def __init__(self, heading: Heading, **kwargs) -> None:
        super().__init__(**kwargs)
        self.heading = heading
        self.add_class(f"outline-item--h{heading.level}")

    def compose(self):
        yield Label(self.heading.text)


class OutlinePanel(Vertical):
    """Outline panel showing document structure."""

    class HeadingSelected(Message):
        def __init__(self, line: int) -> None:
            self.line = line
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._headings: list[Heading] = []

    def compose(self):
        yield Static("outline", id="outline-title", classes="panel-title")
        yield OutlineListView(id="outline-list")

    def update_headings(self, content: str) -> None:
        self._headings = extract_headings(content)
        outline_list = self.query_one("#outline-list", OutlineListView)
        outline_list.clear()
        for heading in self._headings:
            outline_list.append(OutlineItem(heading, classes="outline-item"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, OutlineItem):
            self.post_message(self.HeadingSelected(event.item.heading.line))

"""Tests for OutlinePanel updating in place while typing."""

import asyncio

from textual.app import App
from textual.widgets import Label

from prosaic.widgets.outline import OutlineItem, OutlinePanel


class _OutlineApp(App):
    def compose(self):
        yield OutlinePanel()


def _labels(panel):
    return [str(item.query_one(Label).render()) for item in panel.query(OutlineItem)]


def test_outline_updates_in_place():
    async def run():
        app = _OutlineApp()
        async with app.run_test() as pilot:
            panel = app.query_one(OutlinePanel)
            panel.update_headings("# One\n\ntext\n\n## Two")
            await pilot.pause()
            items = list(panel.query(OutlineItem))

            panel.update_headings("# One\n\nmore text\n\n## Two")
            panel.update_headings("# One\n\nmore text\n\n\n### Two!")
            await pilot.pause()
            assert list(panel.query(OutlineItem)) == items
            assert _labels(panel) == ["One", "Two!"]
            assert items[1].heading.line == 6
            assert items[1].has_class("outline-item--h3")
            assert not items[1].has_class("outline-item--h2")

            panel.update_headings("# One\n\n## Two\n\n## Three")
            panel.update_headings("# One\n\n## Two\n\n## Three!")
            await pilot.pause()
            assert _labels(panel) == ["One", "Two", "Three!"]

            panel.update_headings("# One")
            await pilot.pause()
            assert _labels(panel) == ["One"]

    asyncio.run(run())

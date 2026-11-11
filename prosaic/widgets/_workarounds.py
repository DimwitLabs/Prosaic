"""Memory leak workarounds that reach into Textual and tree-sitter internals.

Everything here depends on private APIs, so a Textual upgrade can break it.
Delete each function once its upstream bug is fixed:

- release_theme_watcher: https://github.com/Textualize/textual/issues/6666
- clear_styles_cache: https://github.com/Textualize/textual/issues/6665
- release_syntax_tree: tree-sitter Tree cycle, not reported upstream yet

Thanks to Georgii Antipin (@carbongo) for tracking these down.
"""

from textual._styles_cache import StylesCache
from textual.widget import Widget


def release_theme_watcher(widget: Widget) -> None:
    """Drop the widget's app.theme watcher so it can be garbage collected."""
    try:
        watchers = getattr(widget.app, "__watchers", {}).get("theme", [])
        watchers[:] = [(node, cb) for node, cb in watchers if node is not widget]
    except Exception:
        pass


def clear_styles_cache() -> None:
    """Clear the shared style cache that keeps closed widgets alive."""
    StylesCache.get_inner_outer.cache_clear()


def release_syntax_tree(document) -> None:
    """Drop a document's tree-sitter tree, which otherwise keeps it alive."""
    if hasattr(document, "_syntax_tree"):
        document._syntax_tree = None

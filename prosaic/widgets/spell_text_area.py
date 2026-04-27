"""TextArea subclass with live spell-check underlines and markdown highlighting."""

import re

from rich.style import Style
from spellchecker import SpellChecker
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import TextArea
from textual.widgets.text_area import TextAreaTheme

_LIGHT_MARKER = Style(color="#b8a090")
_DARK_MARKER = Style(color="#6a5a4a")

PROSAIC_LIGHT_TA = TextAreaTheme(
    name="prosaic_light",
    base_style=Style(color="#5a3d35", bgcolor="#fffffc"),
    gutter_style=Style(color="#8a6d60", bgcolor="#fffffc"),
    cursor_style=Style(color="#fffffc", bgcolor="#703327"),
    cursor_line_style=Style(bgcolor="#fffffc"),
    cursor_line_gutter_style=Style(color="#5a3d35", bgcolor="#fffffc"),
    bracket_matching_style=Style(bgcolor="#e8d8c0", bold=True),
    selection_style=Style(bgcolor="#c9b89a"),
    syntax_styles={
        "string": Style(color="#715e12"),
        "comment": Style(color="#8a6d60", italic=True),
        "keyword": Style(color="#703327", bold=True),
        "heading": Style(color="#703327", bold=True),
        "heading.marker": Style(color="#8a6d60"),
        "bold": Style(bold=True),
        "bold.marker": _LIGHT_MARKER,
        "italic": Style(italic=True, color="#7a5d55"),
        "italic.marker": _LIGHT_MARKER,
        "strikethrough": Style(strike=True),
        "link.label": Style(color="#4a6da0"),
        "link.uri": Style(color="#715e12", underline=True),
        "inline_code": Style(color="#715e12", bgcolor="#f0ece0"),
        "code.marker": _LIGHT_MARKER,
        "list.marker": Style(color="#8a6d60"),
    },
)

PROSAIC_DARK_TA = TextAreaTheme(
    name="prosaic_dark",
    base_style=Style(color="#e8d5c4", bgcolor="#1a1a1a"),
    gutter_style=Style(color="#8a7a6a", bgcolor="#1a1a1a"),
    cursor_style=Style(color="#1a1a1a", bgcolor="#dcae91"),
    cursor_line_style=Style(bgcolor="#1a1a1a"),
    cursor_line_gutter_style=Style(color="#e8d5c4", bgcolor="#1a1a1a"),
    bracket_matching_style=Style(bgcolor="#4a4030", bold=True),
    selection_style=Style(bgcolor="#5a4a3a"),
    syntax_styles={
        "string": Style(color="#c9a86c"),
        "comment": Style(color="#8a7a6a", italic=True),
        "keyword": Style(color="#dcae91", bold=True),
        "heading": Style(color="#dcae91", bold=True),
        "heading.marker": Style(color="#8a7a6a"),
        "bold": Style(bold=True),
        "bold.marker": _DARK_MARKER,
        "italic": Style(italic=True, color="#c8b5a4"),
        "italic.marker": _DARK_MARKER,
        "strikethrough": Style(strike=True),
        "link.label": Style(color="#7aa2d0"),
        "link.uri": Style(color="#c9a86c", underline=True),
        "inline_code": Style(color="#c9a86c", bgcolor="#2a2520"),
        "code.marker": _DARK_MARKER,
        "list.marker": Style(color="#8a7a6a"),
    },
)

_SKIP_LINE = re.compile(r"^(#{1,6}\s|```|---|\s*[-*+]\s|\s*\d+\.\s|>\s|!\[)")
_WORD = re.compile(r"\b([a-zA-Z']{3,})\b")
_SPELL_STYLE = Style(underline=True, color="#c24038")

_BOLD_ASTERISK = re.compile(r"(\*\*)([^*]+)(\*\*)")
_BOLD_UNDERSCORE = re.compile(r"(__)([^_]+)(__)")
_ITALIC_ASTERISK = re.compile(r"(?<!\*)(\*)([^*]+)(\*)(?!\*)")
_ITALIC_UNDERSCORE = re.compile(r"(?<!_)(_)([^_]+)(_)(?!_)")
_INLINE_CODE = re.compile(r"(`)([^`]+)(`)")



class SpellCheckTextArea(TextArea, inherit_bindings=False):
    """TextArea with live spell-check underlines and markdown highlighting."""

    spell_check_enabled: reactive[bool] = reactive(True)

    BINDINGS = [
        Binding("ctrl+a", "select_all", "select all"),
        Binding("ctrl+k", "toggle_comment", "comment", priority=True),
        Binding("up", "cursor_up", "cursor up", show=False),
        Binding("down", "cursor_down", "cursor down", show=False),
        Binding("left", "cursor_left", "cursor left", show=False),
        Binding("right", "cursor_right", "cursor right", show=False),
        Binding("ctrl+left", "cursor_word_left", "cursor word left", show=False),
        Binding("ctrl+right", "cursor_word_right", "cursor word right", show=False),
        Binding("home,ctrl+a", "cursor_line_start", "cursor line start", show=False),
        Binding("end,ctrl+e", "cursor_line_end", "cursor line end", show=False),
        Binding("pageup", "cursor_page_up", "cursor page up", show=False),
        Binding("pagedown", "cursor_page_down", "cursor page down", show=False),
        Binding("ctrl+shift+left", "cursor_word_left(True)", "cursor left word select", show=False),
        Binding("ctrl+shift+right", "cursor_word_right(True)", "cursor right word select", show=False),
        Binding("shift+home", "cursor_line_start(True)", "cursor line start select", show=False),
        Binding("shift+end", "cursor_line_end(True)", "cursor line end select", show=False),
        Binding("shift+up", "cursor_up(True)", "cursor up select", show=False),
        Binding("shift+down", "cursor_down(True)", "cursor down select", show=False),
        Binding("shift+left", "cursor_left(True)", "cursor left select", show=False),
        Binding("shift+right", "cursor_right(True)", "cursor right select", show=False),
        Binding("f8", "select_line", "select line", show=False),
        Binding("f9", "select_all", "select all", show=False),
        Binding("backspace", "delete_left", "delete character left", show=False),
        Binding("ctrl+w", "delete_word_left", "delete left to start of word", show=False),
        Binding("delete,ctrl+d", "delete_right", "delete character right", show=False),
        Binding("ctrl+f", "delete_word_right", "delete right to start of word", show=False),
        Binding("ctrl+x", "cut", "cut", show=False),
        Binding("ctrl+c,super+c", "copy", "copy", show=False),
        Binding("ctrl+v", "paste", "paste", show=False),
        Binding("ctrl+u", "delete_to_start_of_line", "delete to line start", show=False),
        Binding("ctrl+shift+k", "delete_line", "delete line", show=False),
        Binding("ctrl+z", "undo", "undo", show=False),
        Binding("ctrl+y", "redo", "redo", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        self._spell: SpellChecker = SpellChecker()
        self._misspelled: dict[int, list[tuple[int, int]]] = {}
        self._md_highlights: dict[int, list[tuple[int, int, str]]] = {}
        requested_theme = kwargs.pop("theme", "prosaic_light")
        super().__init__(*args, **kwargs)
        self.register_theme(PROSAIC_LIGHT_TA)
        self.register_theme(PROSAIC_DARK_TA)
        self.theme = requested_theme

    def _scan_inline_markdown(self, text: str) -> None:
        """Scan for inline markdown elements (bold, italic, code)."""
        self._md_highlights.clear()
        in_frontmatter = False
        in_code_block = False

        for row, line in enumerate(text.split("\n")):
            stripped = line.strip()

            if row == 0 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            highlights: list[tuple[int, int, str]] = []

            for m in _INLINE_CODE.finditer(line):
                highlights.append((m.start(1), m.end(1), "code.marker"))
                highlights.append((m.start(2), m.end(2), "inline_code"))
                highlights.append((m.start(3), m.end(3), "code.marker"))

            for m in _BOLD_ASTERISK.finditer(line):
                highlights.append((m.start(1), m.end(1), "bold.marker"))
                highlights.append((m.start(2), m.end(2), "bold"))
                highlights.append((m.start(3), m.end(3), "bold.marker"))

            for m in _BOLD_UNDERSCORE.finditer(line):
                highlights.append((m.start(1), m.end(1), "bold.marker"))
                highlights.append((m.start(2), m.end(2), "bold"))
                highlights.append((m.start(3), m.end(3), "bold.marker"))

            for m in _ITALIC_ASTERISK.finditer(line):
                highlights.append((m.start(1), m.end(1), "italic.marker"))
                highlights.append((m.start(2), m.end(2), "italic"))
                highlights.append((m.start(3), m.end(3), "italic.marker"))

            for m in _ITALIC_UNDERSCORE.finditer(line):
                highlights.append((m.start(1), m.end(1), "italic.marker"))
                highlights.append((m.start(2), m.end(2), "italic"))
                highlights.append((m.start(3), m.end(3), "italic.marker"))

            if highlights:
                self._md_highlights[row] = highlights

    def _scan_spelling(self, text: str) -> None:
        self._misspelled.clear()
        if not self.spell_check_enabled:
            return
        in_frontmatter = False
        in_code_block = False

        for row, line in enumerate(text.split("\n")):
            stripped = line.strip()

            if row == 0 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            if not stripped or _SKIP_LINE.match(stripped):
                continue

            spans: list[tuple[int, int]] = []
            for m in _WORD.finditer(line):
                word = m.group(1).strip("'")
                if self._spell.unknown([word]):
                    spans.append((m.start(), m.end()))
            if spans:
                self._misspelled[row] = spans

    def _build_highlight_map(self) -> None:
        try:
            if self._theme is not None:
                self._theme.syntax_styles["spell.error"] = _SPELL_STYLE
        except Exception:
            pass

        self._scan_spelling(self.text)
        self._scan_inline_markdown(self.text)
        super()._build_highlight_map()

        for row, spans in self._misspelled.items():
            if row not in self._highlights:
                self._highlights[row] = []
            for col_s, col_e in spans:
                self._highlights[row].append((col_s, col_e, "spell.error"))

        for row, highlights in self._md_highlights.items():
            if row not in self._highlights:
                self._highlights[row] = []
            for col_s, col_e, style in highlights:
                self._highlights[row].append((col_s, col_e, style))

    def watch_spell_check_enabled(self, enabled: bool) -> None:
        self._build_highlight_map()
        self.refresh()

    def action_toggle_spell_check(self) -> None:
        self.spell_check_enabled = not self.spell_check_enabled

    def action_toggle_comment(self) -> None:
        """Toggle markdown comment on current line."""
        row, _ = self.cursor_location
        line = self.document.get_line(row)
        line_len = len(line)
        stripped = line.strip()

        start = (row, 0)
        end = (row, line_len)

        if stripped.startswith("[") and stripped.endswith("]: #"):
            new_text = stripped[1:-4]
            new_col = len(new_text)
        else:
            new_text = f"[{line}]: #"
            new_col = len(new_text)

        self.replace(new_text, start, end)
        self.move_cursor((row, new_col))

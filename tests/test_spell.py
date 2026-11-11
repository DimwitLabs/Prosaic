"""Tests for SpellCheckTextArea spell scanning behaviour."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from prosaic.widgets import spell_text_area
from prosaic.widgets.spell_text_area import SpellCheckTextArea


@pytest.fixture(autouse=True)
def _fresh_dictionaries():
    spell_text_area._load_dictionary.cache_clear()
    yield
    spell_text_area._load_dictionary.cache_clear()


def _make_scan_target(spell_instance, enabled=True):
    """Return a plain namespace that satisfies _scan_spelling's attribute reads."""
    ns = SimpleNamespace(
        _spell=spell_instance,
        _ensure_spell=lambda: spell_instance,
        _spell_lines={},
        _misspelled={},
        spell_check_enabled=enabled,
    )
    return ns


class TestInitSpell:
    def test_returns_none_when_phunspell_raises(self):
        mock_phunspell = MagicMock(side_effect=Exception("bad language code"))
        with patch("prosaic.widgets.spell_text_area.Phunspell", mock_phunspell):
            ta = SpellCheckTextArea.__new__(SpellCheckTextArea)
            result = ta._init_spell("xx_XX")
            assert result is None

    def test_returns_spell_instance_on_success(self):
        mock_instance = MagicMock()
        mock_phunspell = MagicMock(return_value=mock_instance)
        with patch("prosaic.widgets.spell_text_area.Phunspell", mock_phunspell):
            ta = SpellCheckTextArea.__new__(SpellCheckTextArea)
            result = ta._init_spell("en_US")
            assert result is mock_instance
            mock_phunspell.assert_called_once_with("en_US")


class TestScanSpelling:
    def test_no_misspellings_when_spell_is_none(self):
        ns = _make_scan_target(None)
        SpellCheckTextArea._scan_spelling(ns, "hello wrold")
        assert ns._misspelled == {}

    def test_detects_misspelled_word(self):
        mock_spell = MagicMock()
        mock_spell.lookup.side_effect = lambda w: w == "hello"
        ns = _make_scan_target(mock_spell)
        SpellCheckTextArea._scan_spelling(ns, "hello wrold")
        assert any(ns._misspelled.values())

    def test_no_misspellings_for_correct_words(self):
        mock_spell = MagicMock()
        mock_spell.lookup.return_value = True
        ns = _make_scan_target(mock_spell)
        SpellCheckTextArea._scan_spelling(ns, "hello world")
        assert ns._misspelled == {}

    def test_skips_frontmatter(self):
        mock_spell = MagicMock()
        mock_spell.lookup.return_value = False
        ns = _make_scan_target(mock_spell)
        SpellCheckTextArea._scan_spelling(ns, "---\ntitle: wrold\n---\n\nhello")
        misspelled_rows = list(ns._misspelled.keys())
        assert 0 not in misspelled_rows
        assert 1 not in misspelled_rows
        assert 2 not in misspelled_rows

    def test_no_scan_when_disabled(self):
        mock_spell = MagicMock()
        ns = _make_scan_target(mock_spell, enabled=False)
        SpellCheckTextArea._scan_spelling(ns, "wrold")
        assert ns._misspelled == {}
        mock_spell.lookup.assert_not_called()


class TestSpellCaching:
    def test_dictionary_shared_between_editors(self):
        mock_phunspell = MagicMock(return_value=MagicMock())
        with patch("prosaic.widgets.spell_text_area.Phunspell", mock_phunspell):
            a = SpellCheckTextArea.__new__(SpellCheckTextArea)
            b = SpellCheckTextArea.__new__(SpellCheckTextArea)
            assert a._init_spell("en_GB") is b._init_spell("en_GB")
            mock_phunspell.assert_called_once_with("en_GB")

    def test_rescans_only_changed_lines(self):
        mock_spell = MagicMock()
        mock_spell.lookup.side_effect = lambda w: w != "wrold"
        ns = _make_scan_target(mock_spell)
        SpellCheckTextArea._scan_spelling(ns, "hello wrold\nsecond line here")
        first_calls = mock_spell.lookup.call_count
        SpellCheckTextArea._scan_spelling(ns, "hello wrold\nsecond line here, edited")
        assert mock_spell.lookup.call_count - first_calls == 4  # only the edited line
        assert ns._misspelled == {0: [(6, 11)]}

    def test_dictionary_not_loaded_while_disabled(self):
        mock_spell = MagicMock()
        ns = _make_scan_target(mock_spell, enabled=False)
        ns._ensure_spell = MagicMock(return_value=mock_spell)
        SpellCheckTextArea._scan_spelling(ns, "hello wrold")
        ns._ensure_spell.assert_not_called()

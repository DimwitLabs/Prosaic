"""Typing in a 30k-word chapter with spell check on should not lag."""

import asyncio
import random
import time

from textual.app import App

from prosaic.widgets.spell_text_area import SpellCheckTextArea

LONG_CHAPTER_WORDS = 30_000
TYPED_TEXT = "the quiet garden waited for her letter. "
MAX_MS_PER_KEY = 50

_VOCABULARY = (
    "the a an and but or so yet of in on at by for with from into over under "
    "after before while because though she he they we it her his their our "
    "house garden window door street river morning evening night light shadow "
    "letter voice silence memory story question answer reason moment winter "
    "summer rain wind road train station city village kitchen table chair "
    "walked waited listened remembered wrote opened closed turned watched "
    "wondered laughed carried followed believed noticed whispered returned "
    "quiet slow bright cold warm old young small long strange familiar gentle "
    "always never often again almost perhaps already still only nearly softly"
).split()


def _chapter(word_count: int) -> str:
    """Build a seeded markdown chapter with headings, emphasis and a few typos."""
    rng = random.Random(word_count)
    paragraphs = ["---\ntitle: lag test\n---", "# Chapter One"]
    written = 0
    while written < word_count:
        if written and written % 1500 < 120:
            paragraphs.append(f"## Part {written // 1500 + 1}")
        sentences = []
        for _ in range(rng.randint(3, 7)):
            size = min(rng.randint(8, 20), word_count - written)
            if size <= 0:
                break
            words = rng.choices(_VOCABULARY, k=size)
            if rng.random() < 0.1:
                words[rng.randrange(size)] = "wrold"
            if rng.random() < 0.15:
                i = rng.randrange(size)
                words[i] = f"*{words[i]}*"
            sentences.append(" ".join(words).capitalize() + ".")
            written += size
        paragraphs.append(" ".join(sentences))
    return "\n\n".join(paragraphs) + "\n"


class _EditorApp(App):
    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def compose(self):
        yield SpellCheckTextArea(
            self._text,
            language="markdown",
            soft_wrap=True,
            spell_language="en_US",
        )


async def _seconds_per_key(text: str) -> float:
    """Time each edit, including the highlight rebuild, while typing mid-chapter.

    Rendering between keys runs but is left out of the timing, so the harness's
    fixed overhead cannot hide a cost that grows with the chapter.
    """
    app = _EditorApp(text)
    async with app.run_test(size=(100, 40)) as pilot:
        editor = app.query_one(SpellCheckTextArea)
        editor.focus()
        editor.move_cursor((editor.document.line_count // 2, 0))
        editor.insert("x")
        await pilot.pause()
        elapsed = 0.0
        for char in TYPED_TEXT:
            start = time.perf_counter()
            editor.insert(char)
            elapsed += time.perf_counter() - start
            await pilot.pause()
        return elapsed / len(TYPED_TEXT)


def test_chapter_generator_hits_word_count():
    assert len(_chapter(LONG_CHAPTER_WORDS).split()) >= LONG_CHAPTER_WORDS


def test_typing_in_long_chapter_does_not_lag():
    ms_per_key = asyncio.run(_seconds_per_key(_chapter(LONG_CHAPTER_WORDS))) * 1000
    print(f"\nper key at {LONG_CHAPTER_WORDS} words: {ms_per_key:.1f} ms")
    assert ms_per_key < MAX_MS_PER_KEY, (
        f"typing in {LONG_CHAPTER_WORDS} words took {ms_per_key:.1f} ms per key, "
        f"over the {MAX_MS_PER_KEY} ms budget"
    )

"""Closing an editor should free it, its document and its style cache.

Each check runs the real app in a fresh interpreter, opens and closes a
30k-word chapter a few times, and counts what is still alive afterwards.
The workarounds in prosaic/widgets/_workarounds.py are switched off one at a
time to prove each one still stops a leak; when Textual fixes the bug
upstream, its check fails and the workaround can be deleted.
"""

import asyncio
import gc
import json
import os
import subprocess
import sys
import tempfile
import tracemalloc
import weakref
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CYCLES = 3
LEAKS = {
    "release_theme_watcher": ("editors", "https://github.com/Textualize/textual/issues/6666"),
    "release_syntax_tree": ("documents", "the tree-sitter Tree cycle"),
    "clear_styles_cache": ("style_caches", "https://github.com/Textualize/textual/issues/6665"),
}


@cache
def _probe(*disabled: str) -> dict:
    """Run the probe in a fresh interpreter, so runs never share caches or leaks."""
    result = subprocess.run(
        [sys.executable, "-m", "tests.test_editor_memory", *disabled],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_closed_editors_are_freed():
    result = _probe()
    assert result["editors"] == 0, result
    assert result["documents"] == 0, result
    assert result["style_caches"] == 0, result


@pytest.mark.parametrize("workaround", LEAKS)
def test_workaround_still_stops_a_leak(workaround):
    leaked, upstream = LEAKS[workaround]
    result = _probe(workaround)
    assert result[leaked] > 0, (
        f"With {workaround} off, no {leaked} leaked. The upstream bug ({upstream}) "
        f"looks fixed, so remove {workaround} from prosaic/widgets/_workarounds.py."
    )


def test_workarounds_cut_memory_kept_after_closing():
    with_fixes = _probe()["kept_mb"]
    without_fixes = _probe(*LEAKS)["kept_mb"]
    print(f"\nkept after {CYCLES} closes: {with_fixes} MB with fixes, {without_fixes} MB without")
    assert with_fixes < without_fixes / 2


def _setup_workspace(tmp: Path) -> Path:
    """Point Prosaic at a throwaway config and workspace holding one long chapter."""
    os.environ["PROSAIC_CONFIG_DIR"] = str(tmp / "config")
    workspace = tmp / "workspace"
    (workspace / "pieces").mkdir(parents=True)

    from prosaic.config import save_config, set_active_profile
    from tests.test_typing_lag import LONG_CHAPTER_WORDS, _chapter

    save_config({
        "app_version": "test",
        "setup_complete": True,
        "active_profile": "default",
        "profiles": {
            "default": {
                "archive_dir": str(workspace),
                "init_git": False,
                "spell_language": "en_US",
                "spell_check_enabled": True,
            }
        },
    })
    set_active_profile("default")
    chapter = workspace / "pieces" / "chapter.md"
    chapter.write_text(_chapter(LONG_CHAPTER_WORDS))
    return chapter


def _disable(workarounds: list[str]) -> None:
    from prosaic.widgets import spell_text_area

    for name in workarounds:
        setattr(spell_text_area, name, lambda *args: None)


async def _open_and_close(chapter: Path) -> dict:
    """Warm up once, then count what survives CYCLES editor opens and closes."""
    from prosaic.__main__ import ProsaicApp
    from prosaic.screens import EditorScreen

    app = ProsaicApp(light_mode=True)
    refs: dict[str, list[weakref.ref]] = {"editors": [], "documents": [], "style_caches": []}
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        async def cycle(track: bool) -> None:
            app._open_editor(chapter)
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, EditorScreen)
            if track:
                editor = screen.query_one("#editor")
                refs["editors"].append(weakref.ref(editor))
                refs["documents"].append(weakref.ref(editor.document))
                refs["style_caches"].append(weakref.ref(editor._styles_cache))
                del editor
            screen.action_go_home()
            del screen
            await pilot.pause()

        await cycle(track=False)
        gc.collect()
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        for _ in range(CYCLES):
            await cycle(track=True)
        for _ in range(5):
            await pilot.pause(0.05)
        gc.collect()
        kept = tracemalloc.get_traced_memory()[0] - baseline
        tracemalloc.stop()

    counts = {kind: sum(ref() is not None for ref in kept_refs) for kind, kept_refs in refs.items()}
    return {**counts, "kept_mb": round(kept / 1_000_000, 1)}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        chapter = _setup_workspace(Path(tmp))
        _disable(sys.argv[1:])
        print(json.dumps(asyncio.run(_open_and_close(chapter))))

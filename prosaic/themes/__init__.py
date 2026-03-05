"""Prosaic themes."""

from pathlib import Path

from prosaic.utils import read_text

_THEMES_DIR = Path(__file__).parent


def _load_css(filename: str) -> str:
    """Load CSS from a .tcss file."""
    return read_text(_THEMES_DIR / filename)


PROSAIC_LIGHT_CSS = _load_css("light.tcss")
PROSAIC_DARK_CSS = _load_css("dark.tcss")

__all__ = ["PROSAIC_LIGHT_CSS", "PROSAIC_DARK_CSS"]

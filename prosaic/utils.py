"""Utility functions for Prosaic."""

from pathlib import Path


def read_text(path: Path) -> str:
    """Read file with UTF-8 encoding.

    Args:
        path: Path to the file.

    Returns:
        File contents as string.
    """
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Write file with UTF-8 encoding.

    Args:
        path: Path to the file.
        content: Content to write.
    """
    path.write_text(content, encoding="utf-8")

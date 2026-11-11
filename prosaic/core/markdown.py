"""Markdown processing utilities."""

import re
from dataclasses import dataclass


@dataclass
class Heading:
    """Represents a markdown heading."""

    level: int
    text: str
    line: int


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3 :].lstrip()
    return content


def strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks from content."""
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"^(?:    |\t).*$", "", content, flags=re.MULTILINE)
    return content


def strip_markdown(content: str) -> str:
    """Strip markdown syntax from content for word counting."""
    content = strip_frontmatter(content)
    content = strip_code_blocks(content)
    content = re.sub(r"`[^`]+`", "", content)
    content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    content = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", content)
    content = re.sub(r"^\[[^\]]+\]:.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
    content = re.sub(r"__([^_]+)__", r"\1", content)
    content = re.sub(r"\*([^*]+)\*", r"\1", content)
    content = re.sub(r"_([^_]+)_", r"\1", content)
    content = re.sub(r"~~([^~]+)~~", r"\1", content)
    content = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
    content = re.sub(r"^>\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r"^[-*_]{3,}$", "", content, flags=re.MULTILINE)
    content = re.sub(r"^[\s]*[-*+]\s+", "", content, flags=re.MULTILINE)
    content = re.sub(r"^[\s]*\d+\.\s+", "", content, flags=re.MULTILINE)
    return content


def _count_visible(stripped: str) -> int:
    return len(stripped.replace(" ", "").replace("\n", "").replace("\t", ""))


def count_words(content: str) -> int:
    """Count words in markdown content, excluding syntax."""
    return len(strip_markdown(content).split())


def count_characters(content: str, include_spaces: bool = False) -> int:
    """Count characters in markdown content, excluding syntax."""
    stripped = strip_markdown(content)
    return len(stripped) if include_spaces else _count_visible(stripped)


def count_words_and_characters(content: str) -> tuple[int, int]:
    """Count words and characters with a single markdown strip."""
    stripped = strip_markdown(content)
    return len(stripped.split()), _count_visible(stripped)


def extract_headings(content: str) -> list[Heading]:
    """Extract all headings from markdown content."""
    headings = []
    for i, line in enumerate(content.split("\n")):
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append(Heading(level=level, text=text, line=i + 1))
    return headings

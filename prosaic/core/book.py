"""Book management utilities."""

import re
from pathlib import Path

from prosaic.core.markdown import extract_headings
from prosaic.utils import read_text, write_text

MANUSCRIPT_NOTICE = "[auto-generated — edit chapters individually]: #\n\n"
CHAPTERS_DIR = "chapters"
CHAPTERS_FILE = "chapters.md"
MANUSCRIPT_FILE = "manuscript.md"


def is_new_format(path: Path) -> bool:
    """True if path is a new-format book directory (not a legacy .md file)."""
    return path.is_dir() and (path / CHAPTERS_DIR).exists()


def get_all_books(books_dir: Path) -> list[Path]:
    """Returns all book paths sorted by modification time (newest first).

    Includes new-format directories and legacy .md files.
    """
    if not books_dir.exists():
        return []

    books: list[Path] = []

    for item in books_dir.iterdir():
        if item.is_dir() and (item / CHAPTERS_DIR).exists():
            books.append(item)
        elif item.is_file() and item.suffix == ".md":
            books.append(item)

    return sorted(books, key=lambda p: p.stat().st_mtime, reverse=True)


def get_book_title(book_path: Path) -> str:
    """Returns a display title from the book directory/filename."""
    return book_path.stem.replace("-", " ").replace("_", " ")


def _slugify(title: str) -> str:
    slug = title.lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", slug)


def create_book_structure(books_dir: Path, name: str) -> Path:
    """Creates a new-format book directory structure.

    Creates:
        books_dir/name/
        books_dir/name/chapters/
        books_dir/name/chapters.md
        books_dir/name/manuscript.md

    Returns the book directory path.
    """
    slug = _slugify(name) if name else None
    if not slug:
        from datetime import datetime
        slug = datetime.now().strftime("%Y%m%d%H%M%S")

    book_dir = books_dir / slug
    book_dir.mkdir(parents=True, exist_ok=True)
    (book_dir / CHAPTERS_DIR).mkdir(exist_ok=True)
    write_text(book_dir / CHAPTERS_FILE, "")
    title = name if name else get_book_title(book_dir)
    write_text(
        book_dir / MANUSCRIPT_FILE,
        f"{MANUSCRIPT_NOTICE}# {title}\n\n",
    )
    return book_dir


def get_chapters(book_dir: Path) -> list[Path]:
    """Returns chapter file paths in chapters.md order.

    Falls back to alphabetical order if chapters.md is missing or empty.
    Any filenames in chapters.md that don't exist on disk are silently skipped.
    Any files on disk not listed in chapters.md are appended alphabetically.
    """
    chapters_dir = book_dir / CHAPTERS_DIR
    chapters_file = book_dir / CHAPTERS_FILE

    all_files = {p.name: p for p in chapters_dir.glob("*.md")} if chapters_dir.exists() else {}

    ordered: list[Path] = []
    listed: set[str] = set()

    if chapters_file.exists():
        for line in read_text(chapters_file).splitlines():
            name = line.strip()
            if name and name in all_files:
                ordered.append(all_files[name])
                listed.add(name)

    for name in sorted(all_files):
        if name not in listed:
            ordered.append(all_files[name])

    return ordered


def compile_manuscript(book_dir: Path) -> None:
    """Compiles all chapters into manuscript.md in chapters.md order."""
    chapters = get_chapters(book_dir)
    title = get_book_title(book_dir).title()

    parts: list[str] = [f"{MANUSCRIPT_NOTICE}# {title}"]

    for chapter_path in chapters:
        content = read_text(chapter_path).strip()
        if content:
            parts.append(content)

    manuscript = "\n\n---\n\n".join(parts) + "\n"
    write_text(book_dir / MANUSCRIPT_FILE, manuscript)


def _has_prose(lines: list[str]) -> bool:
    """True if any line is non-empty and not a heading."""
    return any(ln.strip() and not re.match(r"^#{1,6}\s", ln) for ln in lines)


def _collect_chapter_sections(
    lines: list[str], headings: list
) -> list[tuple[list[str], int]]:
    """Return ordered list of (section_lines, original_level) for all chapter sections.

    Every non-H1 heading starts a new section that runs to just before the next
    heading (of any level). This is the simplest and most predictable rule:
    each heading in the document becomes one chapter file.

    Prose before the first heading (excluding the H1 title) becomes a preface
    section (level 0) if it contains non-empty, non-heading content.
    """
    h1 = next((h for h in headings if h.level == 1), None)
    non_h1 = [h for h in headings if h.level > 1]
    total_lines = len(lines)
    sections: list[tuple[list[str], int]] = []

    if not non_h1:
        return []

    # Preamble: lines after H1 (or from start) and before first heading
    preamble_start = h1.line if h1 else 0
    preamble_lines = lines[preamble_start : non_h1[0].line - 1]
    if _has_prose(preamble_lines):
        sections.append((preamble_lines, 0))

    for i, h in enumerate(non_h1):
        next_h = non_h1[i + 1] if i + 1 < len(non_h1) else None
        end = (next_h.line - 1) if next_h else total_lines
        sections.append((lines[h.line - 1 : end], h.level))

    return sections


def _normalise_section(section_lines: list[str], original_level: int) -> str:
    """Return section text with its leading heading normalised to H2.

    original_level 0  → bare prose wrapped with '## Preface'
    original_level 2  → no change needed
    original_level 3+ → replace only the first line's heading markers with '##'
                         (each section has exactly one heading — the first line)
    """
    if original_level == 0:
        return "## Preface\n\n" + "".join(section_lines).strip()

    if original_level == 2:
        return "".join(section_lines).strip()

    first_ln = section_lines[0]
    m = re.match(r"^(#{1,6})", first_ln)
    if m:
        first_ln = "##" + first_ln[len(m.group(1)):]
    return (first_ln + "".join(section_lines[1:])).strip()


def migrate_legacy_book(md_path: Path) -> Path:
    """Converts a legacy single .md book into the new directory structure.

    Every non-H1 heading in the source file becomes its own chapter file.
    The heading is normalised to H2 in the output. Prose before the first
    heading (e.g. a dedication) becomes preface.md if non-empty.

    Renames the original .md file to .md.bak for safety.
    Returns the new book directory path.
    """
    content = read_text(md_path)
    headings = extract_headings(content)
    lines = content.splitlines(keepends=True)

    book_dir = md_path.parent / md_path.stem
    book_dir.mkdir(exist_ok=True)
    chapters_dir = book_dir / CHAPTERS_DIR
    chapters_dir.mkdir(exist_ok=True)

    sections = _collect_chapter_sections(lines, headings)

    if not sections:
        # No heading structure — single chapter wrapping all content
        body = content
        if headings and headings[0].level == 1:
            body = "".join(lines[headings[0].line :]).strip()
        write_text(chapters_dir / "chapter-one.md", f"## Chapter One\n\n{body}\n")
        chapter_names = ["chapter-one.md"]
    else:
        chapter_names: list[str] = []
        used_slugs: dict[str, int] = {}

        for section_lines, original_level in sections:
            if not "".join(section_lines).strip():
                continue

            section_text = _normalise_section(section_lines, original_level)

            if original_level == 0:
                heading_text = "Preface"
            else:
                first_line = section_lines[0].strip()
                m = re.match(r"^#{1,6}\s+(.+)$", first_line)
                heading_text = m.group(1).strip() if m else "Chapter"

            slug = _slugify(heading_text) or "chapter"
            count = used_slugs.get(slug, 0)
            used_slugs[slug] = count + 1
            filename = f"{slug}-{count + 1}.md" if count else f"{slug}.md"

            write_text(chapters_dir / filename, section_text + "\n")
            chapter_names.append(filename)

    write_text(book_dir / CHAPTERS_FILE, "\n".join(chapter_names) + "\n")
    compile_manuscript(book_dir)

    bak_path = md_path.with_suffix(".md.bak")
    md_path.rename(bak_path)

    return book_dir

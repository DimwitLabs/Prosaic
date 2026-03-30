"""Tests for prosaic.core.book module."""

from pathlib import Path

import pytest

from prosaic.core.book import (
    compile_manuscript,
    create_book_structure,
    get_all_books,
    get_book_title,
    get_chapters,
    is_new_format,
    migrate_legacy_book,
)


def _make_book(tmp_path: Path, name: str, chapters: list[tuple[str, str]] | None = None) -> Path:
    """Helper: create a new-format book with optional chapters."""
    books_dir = tmp_path / "books"
    book_dir = create_book_structure(books_dir, name)
    if chapters:
        for filename, content in chapters:
            (book_dir / "chapters" / filename).write_text(content, encoding="utf-8")
        (book_dir / "chapters.md").write_text(
            "\n".join(f for f, _ in chapters) + "\n", encoding="utf-8"
        )
    return book_dir


class TestIsNewFormat:
    def test_directory_with_chapters_subdir_is_new_format(self, tmp_path):
        book_dir = tmp_path / "my-book"
        book_dir.mkdir()
        (book_dir / "chapters").mkdir()
        assert is_new_format(book_dir) is True

    def test_directory_without_chapters_subdir_is_not_new_format(self, tmp_path):
        book_dir = tmp_path / "my-book"
        book_dir.mkdir()
        assert is_new_format(book_dir) is False

    def test_md_file_is_not_new_format(self, tmp_path):
        md = tmp_path / "my-book.md"
        md.write_text("# My Book\n", encoding="utf-8")
        assert is_new_format(md) is False


class TestGetAllBooks:
    def test_returns_empty_when_books_dir_missing(self, tmp_path):
        assert get_all_books(tmp_path / "nonexistent") == []

    def test_returns_new_format_directories(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        result = get_all_books(books_dir)
        assert book_dir in result

    def test_returns_legacy_md_files(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        legacy = books_dir / "old-book.md"
        legacy.write_text("# Old Book\n", encoding="utf-8")
        result = get_all_books(books_dir)
        assert legacy in result

    def test_excludes_non_md_files(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        txt_file = books_dir / "notes.txt"
        txt_file.write_text("notes", encoding="utf-8")
        result = get_all_books(books_dir)
        assert txt_file not in result

    def test_excludes_plain_directories(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        plain_dir = books_dir / "not-a-book"
        plain_dir.mkdir()
        result = get_all_books(books_dir)
        assert plain_dir not in result


class TestGetBookTitle:
    def test_converts_hyphens_to_spaces(self, tmp_path):
        book = tmp_path / "my-novel"
        assert get_book_title(book) == "my novel"

    def test_converts_underscores_to_spaces(self, tmp_path):
        book = tmp_path / "my_novel"
        assert get_book_title(book) == "my novel"

    def test_plain_name_unchanged(self, tmp_path):
        book = tmp_path / "mynovel"
        assert get_book_title(book) == "mynovel"


class TestCreateBookStructure:
    def test_creates_book_directory(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        assert book_dir.is_dir()

    def test_creates_chapters_subdirectory(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        assert (book_dir / "chapters").is_dir()

    def test_creates_chapters_md(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        assert (book_dir / "chapters.md").exists()

    def test_creates_manuscript_md(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        assert (book_dir / "manuscript.md").exists()

    def test_manuscript_contains_auto_gen_notice(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "my-novel")
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert "auto-generated" in content

    def test_slugifies_title(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "My Great Novel")
        assert book_dir.name == "my-great-novel"

    def test_uses_timestamp_when_no_title(self, tmp_path):
        books_dir = tmp_path / "books"
        book_dir = create_book_structure(books_dir, "")
        assert book_dir.is_dir()


class TestGetChapters:
    def test_returns_empty_when_no_chapters(self, tmp_path):
        book_dir = _make_book(tmp_path, "empty-book")
        assert get_chapters(book_dir) == []

    def test_returns_chapters_in_chapters_md_order(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-book",
            [
                ("chapter-two.md", "## Chapter Two\n\nSecond."),
                ("chapter-one.md", "## Chapter One\n\nFirst."),
            ],
        )
        # Rewrite chapters.md to put one before two
        (book_dir / "chapters.md").write_text(
            "chapter-one.md\nchapter-two.md\n", encoding="utf-8"
        )
        chapters = get_chapters(book_dir)
        assert chapters[0].name == "chapter-one.md"
        assert chapters[1].name == "chapter-two.md"

    def test_falls_back_to_alphabetical_when_chapters_md_empty(self, tmp_path):
        book_dir = _make_book(tmp_path, "my-book")
        (book_dir / "chapters.md").write_text("", encoding="utf-8")
        for name in ("zz-last.md", "aa-first.md"):
            (book_dir / "chapters" / name).write_text(f"## {name}\n\n", encoding="utf-8")
        chapters = get_chapters(book_dir)
        assert chapters[0].name == "aa-first.md"
        assert chapters[1].name == "zz-last.md"

    def test_skips_missing_files_listed_in_chapters_md(self, tmp_path):
        book_dir = _make_book(tmp_path, "my-book")
        (book_dir / "chapters" / "exists.md").write_text("## Exists\n\n", encoding="utf-8")
        (book_dir / "chapters.md").write_text(
            "nonexistent.md\nexists.md\n", encoding="utf-8"
        )
        chapters = get_chapters(book_dir)
        assert len(chapters) == 1
        assert chapters[0].name == "exists.md"

    def test_appends_unlisted_files_alphabetically(self, tmp_path):
        book_dir = _make_book(tmp_path, "my-book")
        (book_dir / "chapters" / "chapter-one.md").write_text("## One\n\n", encoding="utf-8")
        (book_dir / "chapters" / "chapter-two.md").write_text("## Two\n\n", encoding="utf-8")
        (book_dir / "chapters.md").write_text("chapter-one.md\n", encoding="utf-8")
        chapters = get_chapters(book_dir)
        assert len(chapters) == 2
        assert chapters[0].name == "chapter-one.md"
        assert chapters[1].name == "chapter-two.md"


class TestCompileManuscript:
    def test_creates_manuscript_file(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-book",
            [("chapter-one.md", "## Chapter One\n\nHello world.")],
        )
        compile_manuscript(book_dir)
        assert (book_dir / "manuscript.md").exists()

    def test_manuscript_contains_auto_gen_notice(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-book",
            [("chapter-one.md", "## Chapter One\n\nContent.")],
        )
        compile_manuscript(book_dir)
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert "auto-generated" in content

    def test_manuscript_contains_book_title(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-great-novel",
            [("chapter-one.md", "## Chapter One\n\nContent.")],
        )
        compile_manuscript(book_dir)
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert "My Great Novel" in content

    def test_manuscript_contains_all_chapter_content(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-book",
            [
                ("chapter-one.md", "## Chapter One\n\nFirst chapter."),
                ("chapter-two.md", "## Chapter Two\n\nSecond chapter."),
            ],
        )
        compile_manuscript(book_dir)
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert "First chapter." in content
        assert "Second chapter." in content

    def test_manuscript_respects_chapter_order(self, tmp_path):
        book_dir = _make_book(tmp_path, "my-book")
        (book_dir / "chapters" / "chapter-a.md").write_text("## A\n\nA content.", encoding="utf-8")
        (book_dir / "chapters" / "chapter-b.md").write_text("## B\n\nB content.", encoding="utf-8")
        (book_dir / "chapters.md").write_text(
            "chapter-b.md\nchapter-a.md\n", encoding="utf-8"
        )
        compile_manuscript(book_dir)
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert content.index("B content.") < content.index("A content.")

    def test_manuscript_ends_with_newline(self, tmp_path):
        book_dir = _make_book(
            tmp_path,
            "my-book",
            [("chapter-one.md", "## Chapter One\n\nContent.")],
        )
        compile_manuscript(book_dir)
        content = (book_dir / "manuscript.md").read_text(encoding="utf-8")
        assert content.endswith("\n")


class TestMigrateLegacyBook:
    def _legacy(self, books_dir: Path, name: str, content: str) -> Path:
        books_dir.mkdir(parents=True, exist_ok=True)
        md = books_dir / f"{name}.md"
        md.write_text(content, encoding="utf-8")
        return md

    def test_returns_new_book_directory(self, tmp_path):
        books_dir = tmp_path / "books"
        md = self._legacy(books_dir, "my-novel", "# My Novel\n\n## Chapter One\n\nHello.\n")
        book_dir = migrate_legacy_book(md)
        assert book_dir.is_dir()

    def test_renames_original_to_bak(self, tmp_path):
        books_dir = tmp_path / "books"
        md = self._legacy(books_dir, "my-novel", "# My Novel\n\n## Chapter One\n\nHello.\n")
        migrate_legacy_book(md)
        assert not md.exists()
        assert (books_dir / "my-novel.md.bak").exists()

    def test_creates_chapters_directory(self, tmp_path):
        books_dir = tmp_path / "books"
        md = self._legacy(books_dir, "my-novel", "# My Novel\n\n## Chapter One\n\nHello.\n")
        book_dir = migrate_legacy_book(md)
        assert (book_dir / "chapters").is_dir()

    def test_splits_by_h2_headings(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "# My Novel\n\n## Chapter One\n\nFirst.\n\n## Chapter Two\n\nSecond.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 2

    def test_chapter_files_start_with_h2(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "# My Novel\n\n## Chapter One\n\nContent.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 1
        text = chapter_files[0].read_text(encoding="utf-8")
        assert text.startswith("## ")

    def test_creates_chapters_md(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "# My Novel\n\n## Chapter One\n\nFirst.\n\n## Chapter Two\n\nSecond.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        assert (book_dir / "chapters.md").exists()
        chapters_content = (book_dir / "chapters.md").read_text(encoding="utf-8")
        assert chapters_content.strip() != ""

    def test_creates_manuscript_md(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "# My Novel\n\n## Chapter One\n\nContent.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        assert (book_dir / "manuscript.md").exists()

    def test_no_headings_creates_single_chapter(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "Just some content without headings.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 1

    def test_h3_fallback_when_no_h2(self, tmp_path):
        books_dir = tmp_path / "books"
        content = "# My Novel\n\n### Scene One\n\nFirst.\n\n### Scene Two\n\nSecond.\n"
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 2

    def test_splits_on_every_heading(self, tmp_path):
        """Every non-H1 heading becomes its own chapter file."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "## Part One\n\n"
            "### Chapter One\n\nLots of content here for the first chapter.\n\n"
            "### Chapter Two\n\nLots of content here for the second chapter.\n\n"
            "## Part Two\n\n"
            "### Chapter Three\n\nLots of content here for the third chapter.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = sorted((book_dir / "chapters").glob("*.md"))
        # Each heading becomes its own file: Part One, Ch1, Ch2, Part Two, Ch3
        assert len(chapter_files) == 5

    def test_h3_headings_normalised_to_h2(self, tmp_path):
        """H3 headings are normalised to H2 in chapter files."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "### Chapter One\n\nContent.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 1
        text = chapter_files[0].read_text(encoding="utf-8")
        assert text.startswith("## ")

    def test_h2_headings_stay_h2(self, tmp_path):
        """H2 headings remain as H2 in chapter files."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "## Chapter One\n\n"
            "Content.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        assert len(chapter_files) == 1
        text = chapter_files[0].read_text(encoding="utf-8")
        assert "## Chapter One" in text
        assert "### Chapter One" not in text

    def test_heading_content_separation(self, tmp_path):
        """Heading and content are properly separated in chapter files."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "## Chapter One\n\nFirst line of prose.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        chapter_files = list((book_dir / "chapters").glob("*.md"))
        text = chapter_files[0].read_text(encoding="utf-8")
        assert "## Chapter One" in text
        assert "First line of prose." in text

    def test_preamble_prose_creates_preface_chapter(self, tmp_path):
        """Prose before the first chapter heading becomes a preface.md file."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "This is the book's introduction.\n\n"
            "## Chapter One\n\nChapter content.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        assert (book_dir / "chapters" / "preface.md").exists()
        preface = (book_dir / "chapters" / "preface.md").read_text(encoding="utf-8")
        assert "introduction" in preface

    def test_preamble_prose_listed_first_in_chapters_md(self, tmp_path):
        """preface.md appears before chapter files in chapters.md."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "Introduction prose.\n\n"
            "## Chapter One\n\nContent.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        order = (book_dir / "chapters.md").read_text(encoding="utf-8").splitlines()
        assert order[0] == "preface.md"

    def test_part_headers_only_do_not_create_preface(self, tmp_path):
        """Part headings (H2) before chapters should NOT create a preface file."""
        books_dir = tmp_path / "books"
        content = (
            "# My Novel\n\n"
            "## Part One\n\n"
            "### Chapter One\n\nContent.\n"
        )
        md = self._legacy(books_dir, "my-novel", content)
        book_dir = migrate_legacy_book(md)
        assert not (book_dir / "chapters" / "preface.md").exists()

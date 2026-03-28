"""Tests for prosaic.app module."""

import pytest
from pathlib import Path

from prosaic.app import CreateFileModal


class TestCreateFileModal:
    """Tests for CreateFileModal base class."""

    def test_strip_md_extension_removes_md(self):
        """Should strip .md extension from title."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._strip_md_extension("my-file.md") == "my-file"
        assert modal._strip_md_extension("my-file.MD") == "my-file"
        assert modal._strip_md_extension("my-file.Md") == "my-file"

    def test_strip_md_extension_preserves_other(self):
        """Should preserve titles without .md extension."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._strip_md_extension("my-file") == "my-file"
        assert modal._strip_md_extension("my-file.txt") == "my-file.txt"
        assert modal._strip_md_extension("my.md.file") == "my.md.file"

    def test_get_filename_strips_md_before_adding(self):
        """Should not double .md extension."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._get_filename("my-file.md") == "my-file.md"
        assert modal._get_filename("My File.md") == "my-file.md"

    def test_get_filename_adds_md_extension(self):
        """Should add .md extension to titles without it."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._get_filename("my-file") == "my-file.md"
        assert modal._get_filename("My File") == "my-file.md"

    def test_slugify_handles_spaces(self):
        """Should convert spaces to hyphens."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._slugify("My New File") == "my-new-file"

    def test_slugify_removes_special_chars(self):
        """Should remove special characters."""
        modal = CreateFileModal.__new__(CreateFileModal)
        assert modal._slugify("Hello, World!") == "hello-world"
        assert modal._slugify("file@name#test") == "filenametest"

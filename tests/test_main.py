"""Tests for prosaic.__main__ CLI."""

import pytest
from click.testing import CliRunner

from prosaic import __main__ as cli
from prosaic.__main__ import main


@pytest.fixture
def launched(monkeypatch):
    """Stub out setup and the TUI, recording the file the app would open."""
    opened = []

    class FakeApp:
        def __init__(self, light_mode, initial_file):
            opened.append(initial_file)

        def run(self):
            pass

    monkeypatch.setattr(cli, "ProsaicApp", FakeApp)
    monkeypatch.setattr(cli, "needs_setup", lambda name: False)
    monkeypatch.setattr(cli, "needs_language_setup", lambda name: False)
    return opened


def test_directory_file_argument_is_rejected(tmp_path, tmp_config_dir, launched):
    """Should exit with a usage error instead of starting the app."""
    result = CliRunner().invoke(main, [str(tmp_path)])
    assert result.exit_code == 2
    assert "is a directory" in result.output
    assert launched == []


def test_existing_file_argument_opens(tmp_path, tmp_config_dir, launched):
    """Should start the app with an existing file."""
    path = tmp_path / "chapter.md"
    path.write_text("hello")
    result = CliRunner().invoke(main, [str(path)])
    assert result.exit_code == 0, result.output
    assert launched == [path]


def test_missing_file_argument_opens(tmp_path, tmp_config_dir, launched):
    """Should still accept a path that does not exist yet."""
    path = tmp_path / "new.md"
    result = CliRunner().invoke(main, [str(path)])
    assert result.exit_code == 0, result.output
    assert launched == [path]

"""Tests for the prosaic CLI entry point (prosaic.__main__)."""

from click.testing import CliRunner

from prosaic.__main__ import main


class TestDirectoryArgument:
    """Tests for passing a directory as the file argument."""

    def test_directory_argument_rejected(self, tmp_config_dir):
        """A directory exits with a clean error instead of launching the app."""
        target = tmp_config_dir / "subdir"
        target.mkdir()

        result = CliRunner().invoke(main, [str(target)])

        assert result.exit_code != 0
        assert "is a directory" in result.output
        assert isinstance(result.exception, SystemExit)

    def test_nonexistent_file_still_accepted(self, tmp_config_dir, monkeypatch):
        """A nonexistent path is still treated as a new file, not an error."""
        from prosaic import __main__ as main_module

        captured = {}

        class FakeApp:
            def __init__(self, light_mode, initial_file):
                captured["initial_file"] = initial_file

            def run(self):
                return None

        monkeypatch.setattr(main_module, "ProsaicApp", FakeApp)
        monkeypatch.setattr(main_module, "was_just_migrated", lambda: False)
        monkeypatch.setattr(main_module, "needs_setup", lambda *a: False)
        monkeypatch.setattr(
            main_module, "needs_language_setup", lambda *a: False
        )

        new_file = tmp_config_dir / "draft.md"
        result = CliRunner().invoke(main, [str(new_file)])

        assert result.exit_code == 0
        assert captured["initial_file"] is not None
        assert str(captured["initial_file"]) == str(new_file)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-02-23

### Fixed

- Updated README for PyPI.

## [1.0.0] - 2026-02-23

### Added

- **Start writing mode**: Quick writing session with all panes open (`s` keybinding).
- **Find files type indicators**: File list shows type abbreviations (b/d/n/p) with legend below.
- Landing page at `prosaic.dimwit.me` with Prosaic light theme styling.
- Anti-features section on landing page (lock-in, AI writing, subscriptions, telemetry).
- GitHub issue and PR templates.
- GitHub Action for automatic PyPI publishing on tags.
- Cross-platform testing workflow (Ubuntu, macOS, Windows × Python 3.11-3.13).
- Published to PyPI as `prosaic-app` (`pipx install prosaic-app`).
- Badges to `README.md`.

### Fixed

- `ctrl+c` now correctly copies text instead of quitting (use `ctrl+q` to quit).
- Selection highlighting now clearly visible (improved contrast for both light and dark themes).
- Markdown syntax highlighting for emphasis, bold, links, code spans, blockquotes, and list markers.
- Find Files now searches entire workspace recursively and displays relative paths.
- **Inline markdown formatting**: Bold, italic, and inline code properly styled with dimmed markers.
- Active pane borders remain curved (round) instead of changing to solid.

## [0.1.1] - 2026-02-21

### Added

- **Continue writing mode**: Resume your last edited document with `c` keybinding on dashboard.
- Last file tracking stored in `settings.json`.

### Changed

- All imports moved to module level following PEP 8 conventions.
- `git.Repo` import uses `try/except ImportError` pattern for optional dependency.

## [0.1.0] - 2026-02-20

### Added

- Initial release of Prosaic writing app.
- Dashboard with pieces, books, notes, and file finder.
- Markdown editor with live outline and word counting.
- Focus mode and reader mode.
- Daily metrics tracking.
- Git-ready archive with automatic initialization.
- Git repository detection during setup wizard with remote URL inheritance.
- XDG-compliant config location (`~/.config/prosaic/`) with `XDG_CONFIG_HOME` support.
- `PROSAIC_CONFIG_DIR` environment variable for custom config path override.
- Light and dark themes.

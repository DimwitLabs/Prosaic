# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.2] - 2026-03-05

### Changed

- Update web links in `pyproject.toml` to the new ones.

## [1.3.1] - 2026-03-05

### Fixed

- F6 keybinding conflict: moved select line to F8, select all to F9.
- Focus and reader modes are now mutually exclusive.
- Pane defaults now apply correctly when switching contexts.

### Changed

- Documentation updated to match exact menu labels.

## [1.3.0] - 2026-03-05

### Added

- **Autosave**: Files automatically save every 10 seconds with visual indicator in the status bar.
- **Git friendliness:** remote URL example and explainer text in setup wizard.

### Fixed

- UTF-8 encoding for all file operations with tests (fixes Windows compatibility).

### Changed

- Reader and notes modes now hide tree and show outline, with padding fix for reader mode.

## [1.2.1] - 2026-03-03

### Changed

- Added upgrade instructions to README.
- Updated example settings.json to v2 profiles format.
- Added missing keybindings to README (`ctrl+k`, `ctrl+p`, `f1`).

### Fixed

- Input text too light in light mode modals.

## [1.2.0] - 2026-03-03

### Added

- **Profiles**: Maintain separate workspaces for different writing projects (personal, work, fiction, etc.).
- `--profile <name>` flag to use or create a specific profile.
- `--profiles` flag to list all configured profiles.
- Profile management screen accessible from dashboard (`m` key).
- Per-profile theme preference (light/dark).
- Set default profile option in edit modal (`ctrl+d`).
- Automatic migration from legacy config to v2 profiles format with backup.

### Changed

- Escape key now works consistently on all screens.
- Modal backgrounds now match the app background (no overlay).

## [1.1.1] - 2026-02-26

- Prosaic has now moved from [DeepanshKhurana/Prosaic](https://github.com/DeepanshKhurana/Prosaic) to [DimwitLabs/Prosaic](https://github.com/DimwitLabs/Prosaic)

## [1.1.0] - 2026-02-26

### Added

- `ctrl+k` to toggle markdown comments using `[text]: #` syntax.
- `ctrl+p` opens key palette showing all keybindings.
- `f1` shows help screen on all screens.

### Changed

- All keybinding descriptions are now lowercase for consistency.

### Fixed

- Escape and `ctrl+q` now consistently close layers in sequence (modals, key palette, screens).
- Modals can now be closed with escape or `ctrl+q`.

### Refactored

- DRY modals with `CreateFileModal` base class.
- Dashboard action handlers use `_make_open_callback` helper.

## [1.0.3] - 2026-02-23

### Added

- `--reference` flag to show quick reference in terminal.
- `--license` flag to show MIT license.
- CLI usage section in README.

### Fixed

- Opening file directly then closing shows dashboard instead of blank screen.

## [1.0.2] - 2026-02-23

### Changed

- Removed PyPI version badge (shields.io caching caused stale display).

## [1.0.1] - 2026-02-23

### Fixed

- README with correct badges and links for PyPI display.

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

"""Profile management screen."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Static

from prosaic.config import (
    VALID_LANGUAGE_CODES,
    delete_profile,
    get_active_profile,
    list_profiles,
    get_profile_config,
    load_config,
    rename_profile,
    save_config,
    save_profile_config,
    get_spell_check_enabled,
)


def _validated_language(lang: str) -> str:
    return lang if lang in VALID_LANGUAGE_CODES else "en_US"


class EditProfileModal(ModalScreen[bool]):
    """Modal for editing the current profile."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+t", "toggle_theme", "toggle theme", priority=True),
        Binding("ctrl+d", "toggle_default", "toggle default", priority=True),
        Binding("ctrl+k", "toggle_spell_check", "toggle spell check", priority=True),
    ]

    def __init__(self, profile_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.profile_name = profile_name
        self.profile_config = get_profile_config(profile_name)
        self._theme = self.profile_config.get("theme", "light")
        self._spell_check_enabled = self.profile_config.get("spell_check_enabled", True)
        config = load_config()
        self._is_default = config.get("active_profile") == profile_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"edit profile: {self.profile_name}", id="dialog-title")

            yield Static("profile name:")
            yield Input(
                value=self.profile_name,
                id="profile-name-input",
            )

            yield Static("workspace directory:")
            yield Input(
                value=self.profile_config.get("archive_dir", ""),
                placeholder="~/Writing",
                id="workspace-input",
            )

            yield Static("git remote (optional):")
            yield Input(
                value=self.profile_config.get("git_remote", ""),
                placeholder="https://github.com/user/repo.git",
                id="git-remote-input",
            )

            yield Static("spell language (e.g. en_US, hu_HU, fr_FR):")
            yield Input(
                value=self.profile_config.get("spell_language", "en_US"),
                max_length=20,
                id="language-input",
            )
            yield Static("", id="language-error", classes="dialog-hint")

            yield Static(f"theme: {self._theme}  (ctrl+t) toggle", id="theme-display")
            default_marker = "yes" if self._is_default else "no"
            yield Static(f"default: {default_marker}  (ctrl+d) toggle", id="default-display")
            spell_marker = "on" if self._spell_check_enabled else "off"
            yield Static(f"spell check: {spell_marker}  (ctrl+k) toggle", id="spell-check-display")
            yield Static("(theme/language changes require restart)", classes="dialog-hint")

            yield Static("(enter) save  (esc) cancel", classes="dialog-hint")

    def on_mount(self) -> None:
        self.query_one("#profile-name-input", Input).focus()

    def action_toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        self.query_one("#theme-display", Static).update(f"theme: {self._theme}  (ctrl+t) toggle")

    def action_toggle_spell_check(self) -> None:
        self._spell_check_enabled = not self._spell_check_enabled
        marker = "on" if self._spell_check_enabled else "off"
        self.query_one("#spell-check-display", Static).update(f"spell check: {marker}  (ctrl+k) toggle")

    def action_toggle_default(self) -> None:
        self._is_default = not self._is_default
        marker = "yes" if self._is_default else "no"
        self.query_one("#default-display", Static).update(f"default: {marker}  (ctrl+d) toggle")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._save_profile()

    def _save_profile(self) -> None:
        new_name = self.query_one("#profile-name-input", Input).value.strip().lower()
        new_workspace = self.query_one("#workspace-input", Input).value.strip()
        git_remote = self.query_one("#git-remote-input", Input).value.strip()
        raw_lang = self.query_one("#language-input", Input).value.strip()

        if not new_name or not new_workspace:
            return

        lang = _validated_language(raw_lang)
        if lang != raw_lang:
            self.query_one("#language-error", Static).update(
                f"unknown language '{raw_lang}' — defaulting to en_US"
            )

        workspace_path = Path(new_workspace).expanduser().resolve()

        target_name = new_name
        if new_name != self.profile_name:
            if not rename_profile(self.profile_name, new_name):
                return

        profile = get_profile_config(target_name)
        profile["archive_dir"] = str(workspace_path)
        profile["git_remote"] = git_remote
        profile["theme"] = self._theme
        profile["spell_language"] = lang
        profile["spell_check_enabled"] = self._spell_check_enabled
        if "init_git" not in profile:
            profile["init_git"] = True
        save_profile_config(profile, target_name)

        if self._is_default:
            config = load_config()
            config["active_profile"] = target_name
            save_config(config)

        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class NewProfileModal(ModalScreen[str | None]):
    """Modal for creating a new profile."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("ctrl+t", "toggle_theme", "toggle theme", priority=True),
        Binding("ctrl+k", "toggle_spell_check", "toggle spell check", priority=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._theme = "light"
        self._spell_check_enabled = True

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("new profile", id="dialog-title")

            yield Static("profile name:")
            yield Input(
                placeholder="work",
                id="profile-name-input",
            )

            yield Static("workspace directory:")
            yield Input(
                placeholder="~/Writing",
                id="workspace-input",
            )

            yield Static("git remote (optional):")
            yield Input(
                placeholder="https://github.com/user/repo.git",
                id="git-remote-input",
            )

            yield Static(f"theme: {self._theme}  (ctrl+t) toggle", id="theme-display")
            spell_marker = "on" if self._spell_check_enabled else "off"
            yield Static(f"spell check: {spell_marker}  (ctrl+k) toggle", id="spell-check-display")

            yield Static("spell language (e.g. en_US, hu_HU, fr_FR):")
            yield Input(
                value="en_US",
                placeholder="en_US",
                max_length=20,
                id="language-input",
            )
            yield Static("", id="language-error", classes="dialog-hint")

            yield Static("(enter) create  (esc) cancel", classes="dialog-hint")

    def on_mount(self) -> None:
        self.query_one("#profile-name-input", Input).focus()

    def action_toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        self.query_one("#theme-display", Static).update(f"theme: {self._theme}  (ctrl+t) toggle")

    def action_toggle_spell_check(self) -> None:
        self._spell_check_enabled = not self._spell_check_enabled
        marker = "on" if self._spell_check_enabled else "off"
        self.query_one("#spell-check-display", Static).update(f"spell check: {marker}  (ctrl+k) toggle")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._create_profile()

    def _create_profile(self) -> None:
        name = self.query_one("#profile-name-input", Input).value.strip().lower()
        workspace = self.query_one("#workspace-input", Input).value.strip()
        git_remote = self.query_one("#git-remote-input", Input).value.strip()
        raw_lang = self.query_one("#language-input", Input).value.strip()

        if not name or not workspace:
            return

        if name in list_profiles():
            return

        lang = _validated_language(raw_lang)
        if lang != raw_lang:
            self.query_one("#language-error", Static).update(
                f"unknown language '{raw_lang}' — defaulting to en_US"
            )

        workspace_path = Path(workspace).expanduser().resolve()

        profile_data = {
            "archive_dir": str(workspace_path),
            "init_git": True,
            "git_remote": git_remote,
            "theme": self._theme,
            "spell_language": lang,
            "spell_check_enabled": self._spell_check_enabled,
        }
        save_profile_config(profile_data, name)

        self.dismiss(name)

    def action_cancel(self) -> None:
        self.dismiss(None)


class DeleteConfirmModal(ModalScreen[bool]):
    """Modal for confirming profile deletion."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel"),
        Binding("y", "confirm", "yes"),
        Binding("n", "cancel", "no"),
    ]

    def __init__(self, profile_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("delete profile", id="dialog-title")
            yield Static(
                f"delete '{self.profile_name}'?\n\n"
                "files will not be deleted."
            )
            yield Static("(y) yes  (n) no", classes="dialog-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ProfilesScreen(Screen):
    """Screen for viewing and managing profiles."""

    BINDINGS = [
        Binding("escape", "go_back", "back"),
        Binding("q", "go_back", "back"),
        Binding("e", "edit_current", "edit"),
        Binding("n", "new_profile", "new"),
        Binding("d", "delete_current", "delete"),
    ]

    def compose(self) -> ComposeResult:
        active = get_active_profile()
        config = get_profile_config(active)
        workspace = config.get("archive_dir", "not set")
        if workspace and workspace != "not set":
            workspace = Path(workspace).name
        git_remote = config.get("git_remote", "")
        git_enabled = config.get("init_git", True)
        theme_name = config.get("theme", "light")

        other_profiles = [p for p in list_profiles() if p != active]

        with Container(id="profiles-container"):
            with Vertical(id="profiles-panel"):
                yield Static("manage profile", id="profiles-title")

                yield Static(f"{active}", classes="profile-current-name")
                yield Static(f"  dir: {workspace}", classes="profile-detail")
                if git_remote:
                    remote_display = git_remote if len(git_remote) <= 30 else git_remote[:27] + "..."
                    yield Static(f"  git: {remote_display}", classes="profile-detail")
                else:
                    yield Static(f"  git: {'yes' if git_enabled else 'no'}", classes="profile-detail")
                yield Static(f"  theme: {theme_name}", classes="profile-detail")
                spell_lang = config.get("spell_language", "en_US")
                spell_enabled = config.get("spell_check_enabled", True)
                yield Static(f"  language: {spell_lang}", classes="profile-detail")
                yield Static(f"  spell check: {'on' if spell_enabled else 'off'}", classes="profile-detail")

                if other_profiles:
                    yield Static("", classes="profile-spacer")
                    others_list = ", ".join(other_profiles)
                    yield Static(f"other: {others_list}", classes="profile-other")
                    yield Static(
                        "use: prosaic --profile <name>",
                        classes="profile-hint",
                    )

                yield Static("", classes="profile-spacer")
                yield Static(
                    "(e) edit  (n) new  (d) delete  (q) back",
                    id="profiles-footer",
                )

    def action_edit_current(self) -> None:
        active = get_active_profile()

        def handle_edit(result: bool) -> None:
            if result:
                self.app.pop_screen()
                self.app.push_screen(ProfilesScreen())

        self.app.push_screen(EditProfileModal(active), callback=handle_edit)

    def action_new_profile(self) -> None:
        def handle_new(name: str | None) -> None:
            if name:
                self.app.pop_screen()
                self.app.push_screen(ProfilesScreen())

        self.app.push_screen(NewProfileModal(), callback=handle_new)

    def action_delete_current(self) -> None:
        active = get_active_profile()
        profiles = list_profiles()

        if len(profiles) <= 1:
            return

        def handle_delete(confirmed: bool) -> None:
            if confirmed:
                delete_profile(active)
                self.app.exit(
                    message=f"Profile '{active}' deleted. "
                    f"Restart with: prosaic --profile {list_profiles()[0]}"
                )

        self.app.push_screen(DeleteConfirmModal(active), callback=handle_delete)

    def action_go_back(self) -> None:
        self.app.pop_screen()

"""Minimal first-launch UI for Pokémon TCG Live."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from .installer import InstallError, install_ptcgl
from .launcher import LaunchError, launch_game
from .runtime import RuntimePaths


class FirstLaunchApplication(Adw.Application):
    """Small setup window shown only while the game is being provisioned."""

    def __init__(self, paths: RuntimePaths) -> None:
        super().__init__(application_id="io.github.PTCGLLinux")
        self.paths = paths
        self.window: Adw.ApplicationWindow | None = None
        self.title_label: Gtk.Label | None = None
        self.status_label: Gtk.Label | None = None
        self.spinner: Gtk.Spinner | None = None
        self.close_button: Gtk.Button | None = None
        self.started = False

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Pokémon TCG Live")
        self.window.set_default_size(460, 250)
        self.window.set_resizable(False)
        self.window.set_deletable(False)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        content.set_margin_top(38)
        content.set_margin_bottom(38)
        content.set_margin_start(42)
        content.set_margin_end(42)
        content.set_valign(Gtk.Align.CENTER)

        self.title_label = Gtk.Label(
            label="Preparing Pokémon TCG Live"
        )
        self.title_label.add_css_class("title-2")

        self.status_label = Gtk.Label(
            label=(
                "Setting up the compatibility environment and "
                "installing the game.\n"
                "This is only required on first launch."
            )
        )
        self.status_label.set_wrap(True)
        self.status_label.set_justify(Gtk.Justification.CENTER)
        self.status_label.add_css_class("dim-label")

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.start()

        self.close_button = Gtk.Button(label="Close")
        self.close_button.set_halign(Gtk.Align.CENTER)
        self.close_button.set_visible(False)
        self.close_button.connect(
            "clicked",
            lambda _button: self.quit(),
        )

        content.append(self.title_label)
        content.append(self.status_label)
        content.append(self.spinner)
        content.append(self.close_button)

        self.window.set_content(content)
        self.window.present()

        if not self.started:
            self.started = True
            threading.Thread(
                target=self._install_worker,
                name="ptcgl-installer",
                daemon=True,
            ).start()

    def _install_worker(self) -> None:
        try:
            install_ptcgl(paths=self.paths)
        except InstallError as exc:
            GLib.idle_add(
                self._show_error,
                f"Installation failed.\n\n{exc}",
            )
            return
        except Exception:
            GLib.idle_add(
                self._show_error,
                "Installation failed because of an unexpected error.",
            )
            return

        GLib.idle_add(self._installation_complete)

    def _installation_complete(self) -> bool:
        if self.window is not None:
            self.window.set_visible(False)

        threading.Thread(
            target=self._game_worker,
            name="ptcgl-game",
            daemon=False,
        ).start()

        return False

    def _game_worker(self) -> None:
        try:
            launch_game(paths=self.paths)
        except LaunchError as exc:
            GLib.idle_add(
                self._show_error,
                f"Pokémon TCG Live could not be started.\n\n{exc}",
            )
            return
        except Exception:
            GLib.idle_add(
                self._show_error,
                "Pokémon TCG Live could not be started.",
            )
            return

        GLib.idle_add(self.quit)

    def _show_error(self, message: str) -> bool:
        if self.window is None:
            return False

        self.window.set_visible(True)
        self.window.set_deletable(True)

        if self.title_label is not None:
            self.title_label.set_text("Unable to prepare Pokémon TCG Live")

        if self.status_label is not None:
            self.status_label.set_text(message)

        if self.spinner is not None:
            self.spinner.stop()
            self.spinner.set_visible(False)

        if self.close_button is not None:
            self.close_button.set_visible(True)

        self.window.present()
        return False


def run_first_launch(paths: RuntimePaths) -> int:
    """Run the first-launch setup UI."""

    app = FirstLaunchApplication(paths)
    return app.run([])

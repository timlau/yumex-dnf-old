# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version..Win
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to
#    the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import argparse
import logging
import sys

import gi  # noqa: F401
from gi.repository import Gio, Gtk  # isort:skip

from yumex.common import CONFIG, dbus_dnfsystem, logger_setup
from yumex.gui.window import Window

logger = logging.getLogger("yumex")


class YumexApplication(Gtk.Application):
    """Main application."""

    def __init__(self):
        Gtk.Application.__init__(
            self,
            application_id="dk.yumex.yumex-ui",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        self.connect("activate", self.on_activate)
        self.connect("command-line", self.on_command_line)
        self.connect("shutdown", self.on_shutdown)
        self.running = False
        self.args = None
        self.dont_close = False
        self.window = None
        self.install_mode = False
        self.current_args = None

    def on_activate(self, app):
        if not self.running:
            self.window = Window(
                self,
                use_headerbar=CONFIG.conf.headerbar,
                install_mode=self.install_mode,
            )
            app.add_window(self.window)
            self.running = True
            self.window.show()
        else:
            self.window.present()
            if self.install_mode and self.window.can_close():
                self.window.rerun_installmode(self.current_args)

    def on_command_line(self, app, args):
        parser = argparse.ArgumentParser(prog="app")
        parser.add_argument("-d", "--debug", action="store_true")
        parser.add_argument(
            "-y", "--yes", action="store_true", help="Answer yes/ok to all questions"
        )
        parser.add_argument(
            "--exit",
            action="store_true",
            help="tell dnfdaemon dbus services used by yumex to exit",
        )
        parser.add_argument(
            "-I", "--install", type=str, metavar="PACKAGE", help="Install Package"
        )
        parser.add_argument(
            "-R", "--remove", type=str, metavar="PACKAGE", help="Remove Package"
        )
        parser.add_argument(
            "--updateall", action="store_true", help="apply all available updates"
        )
        if not self.running:
            # First run
            self.args = parser.parse_args(args.get_arguments()[1:])
            if self.args.exit:  # kill dnf daemon and quit
                dbus_dnfsystem("Exit")
                sys.exit(0)

            if self.args.debug:
                logger_setup(loglvl=logging.DEBUG)
            else:
                logger_setup()
            if self.args.install or self.args.remove or self.args.updateall:
                self.install_mode = True
        else:
            # Second Run
            # parse cmdline in a non quitting way
            self.current_args = parser.parse_known_args(args.get_arguments()[1:])[0]
            if self.current_args.exit:
                if self.window.can_close():
                    self.quit()
                else:
                    logger.info("Application is busy")
            if (
                self.current_args.install
                or self.current_args.remove
                or self.current_args.updateall
            ):
                self.install_mode = True
        self.activate()
        return 0

    def on_shutdown(self, app):
        if self.window and not self.install_mode:
            CONFIG.conf.info_paned = self.window.main_paned.get_position()
            if self.window.cur_maximized:
                CONFIG.conf.win_maximized = True
            else:
                CONFIG.conf.win_width = self.window.cur_width
                CONFIG.conf.win_height = self.window.cur_height
                CONFIG.conf.win_maximized = False
            self.window.release_root_backend(quit_dnfdaemon=True)
        logger.info("Saving config on exit")
        CONFIG.write()
        return 0

# -*- coding: utf-8 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 -2021 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
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

import gi  # pylint: disable=unused-import
from gi.repository import Gdk, GLib, Gtk  # isort:skip

import logging
import os.path
import re
import sys

import yumex.common.const as const
import yumex.common as common

from yumex.common import CONFIG
from yumex.gui.dialogs.errordialog import ErrorDialog
from yumex.gui.dialogs.transactionresult import TransactionResult

from yumex.base import BaseYumex

logger = logging.getLogger("yumex")


# pylint: disable=no-member
class BaseWindow(Gtk.ApplicationWindow, BaseYumex):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(
            self, title="Yum Extender - Powered by DNF", application=app
        )
        BaseYumex.__init__(self)
        self.get_style_context().add_class("yumex-dnf-window")
        self.app = app
        self.connect("delete_event", self.on_delete_event)
        icon = Gtk.IconTheme.get_default().load_icon("yumex-dnf", 128, 0)
        self.set_icon(icon)
        self.ui = Gtk.Builder()
        self.ui.set_translation_domain("yumex-dnf")
        self.ui.add_from_file(const.UI_DIR + "/yumex.ui")
        # transaction result dialog
        self.transaction_result = TransactionResult(self)
        self.error_dialog = ErrorDialog(self)
        self.cur_height = None
        self.cur_width = None
        self.cur_maximized = None

    def get_ui(self, widget_name):
        return self.ui.get_object(widget_name)

    def can_close(self):
        """Check if yumex is idle and can be closed"""
        if self.is_working:
            return False
        else:
            return True

    # noinspection PyUnusedLocal
    def on_delete_event(self, *_args):
        if self.is_working:
            self.iconify()
            return True
        else:
            self.app.quit()

    def apply_css(self, css_fn):
        """apply a css for custom styling"""
        if css_fn:
            screen = Gdk.Screen.get_default()
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(css_fn)
            except GLib.Error as e:
                logger.error(f"Error in theme: {e} ")
            context = Gtk.StyleContext()
            context.add_provider_for_screen(
                screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )
            logger.debug(f"loading custom styling : {css_fn}")

    def load_colors(self, theme_fn):
        color_table = {}
        colors = [
            "color_install",
            "color_update",
            "color_downgrade",
            "color_normal",
            "color_obsolete",
        ]
        regex = re.compile(r"@define-color\s(\w*)\s*(#\w{6}|@\w*)\s*;")
        if common.check_dark_theme():
            backup_color = "#ffffff"
        else:
            backup_color = "#000000"
        with open(theme_fn, "r", encoding="UTF-8") as reader:
            lines = reader.readlines()
        for line in lines:
            if line.startswith("@define-color"):
                match = regex.search(line)
                if len(match.groups()) == 2:
                    color_table[match.group(1)] = match.group(2)
                    logger.debug(f" --> Color:  {match.group(1)} = {match.group(2)}")
        logger.debug(f"loaded {len(color_table)} colors from {theme_fn}")
        for color in colors:
            if color in color_table:
                color_value = color_table[color]
                if color_value.startswith("@"):  # lookup macro color
                    key = color_value[1:]  # dump the @
                    if key in color_table:
                        color_value = color_table[key]
                    else:
                        logger.info(
                            f"Unknown Color alias : {color_value} default to {backup_color}"
                        )
                        color_value = backup_color
                setattr(CONFIG.session, color, color_value)
                logger.debug(f"  --> updated color : {color} to: {color_value}")

    def load_theme(self):
        theme_fn = os.path.join(const.THEME_DIR, CONFIG.conf.theme)
        logger.debug(f"looking for {theme_fn}")
        if os.path.exists(theme_fn):
            self.apply_css(theme_fn)
            self.load_colors(theme_fn)

    def load_custom_styling(self):
        """Load custom .css styling from current theme."""
        # Use Dark Theme
        gtk_settings = Gtk.Settings.get_default()
        gtk_settings.set_property(
            "gtk-application-prefer-dark-theme", CONFIG.conf.use_dark
        )
        css_fn = None
        theme = gtk_settings.props.gtk_theme_name
        logger.debug(f"current theme : {theme}")
        css_postfix = f"{theme}/apps/yumex.css"
        for css_prefix in [os.path.expanduser("~/.themes"), "/usr/share/themes"]:
            css_file = os.path.join(css_prefix, css_postfix)
            logger.debug(f"looking for {css_file}")
            if os.path.exists(css_file):
                css_fn = css_file
                break
        if css_fn:
            self.apply_css(css_fn)
        else:
            self.load_theme()

    # noinspection PyUnusedLocal
    def on_window_state(self, widget, event):
        # save window current maximized state
        self.cur_maximized = event.new_window_state & Gdk.WindowState.MAXIMIZED != 0

    def on_window_changed(self, widget, data):
        size = widget.get_size()
        if isinstance(size, tuple):
            self.cur_height = size[1]
            self.cur_width = size[0]
        else:
            self.cur_height = size.height
            self.cur_width = size.width

    def exception_handler(self, e):
        """Called if exception occours in methods with the
        @ExceptionHandler decorator.
        """
        close = True
        msg = str(e)
        logger.error(f"EXCEPTION : {msg} ")
        err, errmsg = self._parse_error(msg)
        logger.debug(f"err:  [{err}] - msg: {errmsg}")
        if err == "LockedError":
            errmsg = "dnf is locked by another process \n" "\nYum Extender will exit"
            close = False
        elif err == "AccessDeniedError":
            errmsg = "Root backend was not authorized and can't continue"
            close = True
        elif err == "FatalError":
            errmsg = "Fatal error in yumex backend"
            close = False
        elif err == "NoReply":
            errmsg = "DNF Dbus backend is not responding \n" "\nYum Extender will exit"
            close = False
        if errmsg == "":
            errmsg = msg
        self.error_dialog.show(errmsg)
        # try to exit the backends, ignore errors
        if close:
            try:
                self.release_root_backend(quit_dnfdaemon=True)
            except Exception:  # pylint: disable=broad-except
                pass
        Gtk.main_quit()
        sys.exit(1)

    def set_working(self, state, insensitive=True, splash=False):
        """Set the working state.

        - show/hide the progress spinner
        - show busy/normal mousepointer
        - make gui insensitive/sensitive
        - set/unset the woring state in the status icon
        based on the state.
        """
        self.is_working = state
        if state:
            self._set_busy_cursor(insensitive)
            if splash and CONFIG.conf.show_splash:
                self.working_splash.show()
            if insensitive:
                self._disable_buttons(False)
        else:
            self.infobar.hide()
            self._set_normal_cursor()
            if splash and CONFIG.conf.show_splash:
                self.working_splash.hide()
            if insensitive:
                self._disable_buttons(True)

    def _disable_buttons(self, state):
        insensitive_widgets = [
            "left_header",
            "right_header",
            "package_sidebar",
            "content_box",
        ]
        for widget in insensitive_widgets:
            self.ui.get_object(widget).set_sensitive(state)

    def _set_busy_cursor(self, insensitive=False):
        """Set busy cursor in main window."""
        win = self.get_window()
        if win is not None:
            win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        common.do_gtk_events()

    def _set_normal_cursor(self):
        """Set Normal cursor in main window."""
        win = self.get_window()
        if win is not None:
            win.set_cursor(None)
        common.do_gtk_events()

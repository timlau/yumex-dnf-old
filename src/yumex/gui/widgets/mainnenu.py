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


import logging
from gi.repository import Gio, GObject, Gtk, GLib
from yumex.common import _

G_TRUE = GLib.Variant.new_boolean(True)
G_FALSE = GLib.Variant.new_boolean(False)

logger = logging.getLogger('yumex.gui.widget')
class MainMenu(Gio.Menu):
    __gsignals__ = {'menu-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,
                                      GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, win):
        super(MainMenu, self).__init__()
        self.win = win
        self._button = self.win.get_ui('mainmenu_button')
        self._button.connect('clicked', self._on_button)
        self._popover = Gtk.Popover.new_from_model(self._button,
                                                   self)
        gen_menu = Gio.Menu()
        self._add_menu(gen_menu, _("Preferences"), 'pref')
        self._add_menu(gen_menu, _("Refresh Metadata"), 'reload')
        self._add_menu(gen_menu, _("Quit"), 'quit')
        self.append_section(_('Main Menu'), gen_menu)
        help_menu = Gio.Menu()
        self._add_menu(help_menu, _("About"), 'about')
        self._add_menu(help_menu, _("Keyboard Shortcuts"), 'shortcuts')
        self._add_menu(help_menu, _("Documentation"), 'docs')
        self.append_section(_("Help"), help_menu)

    def _add_menu(self, menu, label, name):
        # menu
        menu.append(label, 'win.{}'.format(name))
        # action
        action = Gio.SimpleAction.new(name, None)
        self.win.add_action(action)
        action.connect('activate', self._on_menu, name)
        return action

    def _on_menu(self, action, state, action_name):
        state = action.get_state()
        data = None
        if state == G_TRUE:
            action.change_state(G_FALSE)
            data = False
        elif state == G_FALSE:
            action.change_state(G_TRUE)
            data = True
        self.emit('menu-changed', action_name, data)

    def _on_button(self, button):
        self._popover.show_all()



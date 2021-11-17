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
from gi.repository import GLib, GObject, Gtk
from yumex.common import CONFIG, _

logger = logging.getLogger('yumex.gui.widget')
G_TRUE = GLib.Variant.new_boolean(True)
G_FALSE = GLib.Variant.new_boolean(False)


class SearchBar(GObject.GObject):
    """Handling the search UI."""

    __gsignals__ = {
        'search': (GObject.SignalFlags.RUN_FIRST, None, (
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_PYOBJECT,
        ))
    }

    FIELDS = ['name', 'summary', 'description']
    TYPES = ['prefix', 'keyword', 'fields']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self.search_type = CONFIG.conf.search_default
        self.search_fields = CONFIG.conf.search_fields
        self.active = False
        # widgets
        self._bar = self.win.get_ui('search_bar')
        # Searchbar togglebutton
        self._toggle = self.win.get_ui('sch_togglebutton')
        self._toggle.connect('toggled', self.on_toggle)
        # Search Entry
        self._entry = self.win.get_ui('search_entry')
        self._entry.connect('activate', self.on_entry_activate)
        self._entry.connect('icon-press', self.on_entry_icon)
        # Search Options
        self._options = self.win.get_ui('search-options')
        self._options_button = self.win.get_ui('sch_options_button')
        self._options_button.connect('clicked', self.on_options_button)
        # Search Spinner
        self._spinner = self.win.get_ui('search_spinner')
        self._spinner.stop()
        # setup field checkboxes
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            if key in self.search_fields:
                wid.set_active(True)
            wid.connect('toggled', self.on_fields_changed, key)
        # set fields sensitive if type == 'fields'
        self._set_fields_sensitive(self.search_type == 'fields')
        # setup search type radiobuttons
        for key in SearchBar.TYPES:
            wid = self.win.get_ui('sch_opt_%s' % key)
            if key == self.search_type:
                wid.set_active(True)
            wid.connect('toggled', self.on_type_changed, key)
        # setup search option popover
        self.opt_popover = self.win.get_ui('sch_opt_popover')

    def show_spinner(self, state=True):
        """Set is spinner in searchbar is running."""
        if state:
            self._spinner.start()
        else:
            self._spinner.stop()

    def toggle(self):
        self._toggle.set_active(not self._toggle.get_active())

    def _set_fields_sensitive(self, state=True):
        """Set sensitivity of field checkboxes."""
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            wid.set_sensitive(state)

    def _get_active_field(self):
        """Get the active search fields, based on checkbox states."""
        active = []
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            if wid.get_active():
                active.append(key)
        return active

    def _set_focus(self):
        """Set focus on search entry and move cursor to end of text."""
        self._entry.grab_focus()
        self._entry.emit('move-cursor', Gtk.MovementStep.BUFFER_ENDS, 1, False)

    def on_options_button(self, widget):
        """Search Option button is toggled."""
        if self.opt_popover.get_visible():
            self.opt_popover.hide()
            self._set_focus()
        else:
            self.opt_popover.show_all()

    def on_toggle(self, widget=None):
        """Search Toggle button is toggled."""
        self._bar.set_search_mode(not self._bar.get_search_mode())
        if self._bar.get_search_mode():
            self._set_focus()
        self.active = self._bar.get_search_mode()

    def on_type_changed(self, widget, key):
        """Search type is changed."""
        if widget.get_active():
            self.search_type = key
            CONFIG.conf.search_default = key
            if self.search_type == 'fields':
                self._set_fields_sensitive(True)
            else:
                self._set_fields_sensitive(False)

    def on_fields_changed(self, widget, key):
        """Search fields is changed."""
        self.search_fields = self._get_active_field()
        CONFIG.conf.search_fields = self.search_fields

    def on_entry_activate(self, widget):
        """Seach entry is activated"""
        # make sure search option is hidden
        self.signal()

    def on_entry_icon(self, widget, icon_pos, event):
        """Search icon press callback."""
        # clear icon pressed
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            self._entry.set_text('')
            self._entry.emit('activate')

    def signal(self):
        """Emit a seach signal with key, search type & fields."""
        txt = self._entry.get_text()
        if self.search_type == 'fields':
            self.emit('search', txt, self.search_type, self.search_fields)
        else:
            self.emit('search', txt, self.search_type, [])

    def reset(self):
        self._entry.set_text('')

    def hide(self):
        if self.active:
            self._bar.set_search_mode(False)

    def show(self):
        if self.active:
            self._bar.set_search_mode(True)
            self._set_focus()

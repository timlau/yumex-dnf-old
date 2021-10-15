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
import yumex.common.const as const
from gi.repository import GObject, Gtk
from yumex.common import CONFIG, _

logger = logging.getLogger('yumex.gui.widget')


class ExtraFilters(GObject.GObject):
    __gsignals__ = {'changed': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_STRING,
                                 GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, win):
        super(ExtraFilters, self).__init__()
        self.win = win
        self.all_archs = const.PLATFORM_ARCH
        self.current_archs = None
        self._button = self.win.get_ui('button_more_filters')
        self._button.connect('clicked', self._on_button)
        self._popover = self.win.get_ui('more_filters_popover')
        self._arch_box = self.win.get_ui('box_archs')
        self._setup_archs()
        self.newest_only = self.win.get_ui('cb_newest_only')
        self.newest_only.set_active(CONFIG.conf.newest_only)
        self.newest_only.connect('toggled', self._on_newest)

    def popup(self):
        self._on_button(self._button)

    def _on_button(self, button):
        self._popover.show_all()

    def _setup_archs(self):
        if not CONFIG.conf.archs:
            CONFIG.conf.archs = list(self.all_archs)
            CONFIG.write()
        self.current_archs = set(CONFIG.conf.archs)
        for arch in self.all_archs:
            cb = Gtk.CheckButton(label=arch)
            self._arch_box.pack_start(cb, True, True, 0)
            if arch in CONFIG.conf.archs:
                cb.set_active(True)
            else:
                cb.set_active(False)
            cb.show()
            cb.connect('toggled', self._on_arch)

    def _on_arch(self, widget):
        state = widget.get_active()
        label = widget.get_label()
        if state:
            self.current_archs.add(label)
        else:
            self.current_archs.remove(label)
        CONFIG.conf.archs = list(self.current_archs)
        CONFIG.write()
        self.emit("changed", 'arch', list(self.current_archs))

    def _on_newest(self, widget):
        state = widget.get_active()
        self.emit('changed', 'newest_only', state)


class FilterSidebar(GObject.GObject):
    """Sidebar selector widget. """

    __gsignals__ = {'sidebar-changed': (GObject.SignalFlags.RUN_FIRST,
                                        None,
                                        (GObject.TYPE_STRING,))}

    INDEX = {0: 'updates', 1: 'installed', 2: 'available', 3: 'all'}

    def __init__(self, parent):
        GObject.GObject.__init__(self)
        self._lb = parent.get_ui('pkg_listbox')
        self._parent = parent
        self._current = None
        self._lb.unselect_all()
        self._lb.connect('row-selected', self.on_toggled)

    def on_toggled(self, widget, row):
        """Active filter is changed."""
        if row:
            ndx = row.get_index()
            key = FilterSidebar.INDEX[ndx]
            if key != self._current:
                self.emit('sidebar_changed', key)
                self._current = key

    def set_active(self, key):
        """Set the active item based on key."""
        if self._current == key:
            self.emit('sidebar_changed', key)
        else:
            row_name = 'pkg_flt_row_' + key
            row = self._parent.get_ui(row_name)
            self._lb.select_row(row)


class Filters(GObject.GObject):
    """Handling the package filter UI."""

    __gsignals__ = {'filter-changed': (GObject.SignalFlags.RUN_FIRST,
                                       None,
                                       (GObject.TYPE_STRING,)
                                       )}

    FILTERS = ['updates', 'installed', 'available', 'all']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self._sidebar = FilterSidebar(self.win)
        self.current = 'updates'
        self._sidebar.connect('sidebar-changed', self.on_toggled)

    def on_toggled(self, widget, flt):
        """Active filter is changed."""
        self.current = flt
        self.emit('filter-changed', flt)

    def set_active(self, flt):
        """Set the active filter."""
        self._sidebar.set_active(flt)

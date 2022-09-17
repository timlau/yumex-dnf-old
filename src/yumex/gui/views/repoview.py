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

from gi.repository import Gtk
from yumex.common import _
from yumex.gui.views.selectionview import SelectionView

logger = logging.getLogger("yumex.gui.views")


class RepoView(SelectionView):
    """
    This class controls the repo TreeView
    """

    def __init__(self):
        SelectionView.__init__(self)
        self.headers = [_("Repository"), _("Filename")]
        self.store = self.setup_view()
        self.state = "normal"
        self._last_selected = []

    def on_toggled(self, widget, path):
        """Repo select/unselect handler"""
        iterator = self.store.get_iter(path)
        state = self.store.get_value(iterator, 0)
        self.store.set_value(iterator, 0, not state)

    def on_section_header_clicked(self, widget):
        """Selection column header clicked"""
        if self.state == "normal":  # deselect all
            self._last_selected = self.get_selected()
            self.select_all(state=False)
            self.state = "deselected"
        elif self.state == "deselected":  # select all
            self.state = "selected"
            self.select_all(state=True)
        elif self.state == "selected":  # select previous selected
            self.state = "normal"
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def setup_view(self):
        """Create models and columns for the Repo TextView"""
        store = Gtk.ListStore("gboolean", str, str, "gboolean")
        self.set_model(store)
        # Setup Selection Column
        col = self.create_selection_column_num(
            0, tooltip=_("Click here to switch between\n" " none/all/default selected")
        )
        col.set_clickable(True)
        col.connect("clicked", self.on_section_header_clicked)

        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()  # gpgcheck
        cell2.set_property("icon-name", "dialog-password-symbolic")
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)

        # Setup reponame & repofile column's
        self.create_text_column_num(_("Repository"), 1)
        self.create_text_column_num(_("Name"), 2)
        self.set_search_column(1)
        self.set_reorderable(False)
        return store

    def populate(self, data):
        """Populate a repo liststore with data"""
        self.store.clear()
        for state, ident, name, gpg in data:
            self.store.append([state, ident, name, gpg])

    def new_pixbuf(self, column, cell, model, iterator, data):
        gpg = model.get_value(iterator, 3)
        if gpg:
            cell.set_property("visible", True)
        else:
            cell.set_property("visible", False)

    def get_selected(self):
        selected = []
        for elem in self.store:
            state = elem[0]
            name = elem[1]
            if state:
                selected.append(name)
        return selected

    def get_notselected(self):
        notselected = []
        for elem in self.store:
            state = elem[0]
            name = elem[1]
            if not state:
                notselected.append(name)
        return notselected

    def select_by_keys(self, keys):
        iterator = self.store.get_iter_first()
        while iterator is not None:
            repoid = self.store.get_value(iterator, 1)
            if repoid in keys:
                self.store.set_value(iterator, 0, True)
            else:
                self.store.set_value(iterator, 0, False)
            iterator = self.store.iter_next(iterator)

    def select_all(self, state=True):
        """Set repo selection for all repos."""
        iterator = self.store.get_iter_first()
        while iterator is not None:
            self.store.set_value(iterator, 0, state)
            iterator = self.store.iter_next(iterator)

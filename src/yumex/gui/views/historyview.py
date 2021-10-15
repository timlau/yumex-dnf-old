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
import os

from gi.repository import Gtk
from yumex.common import _
from yumex.gui.views.historypackageview import HistoryPackageView

logger = logging.getLogger('yumex.gui.views')


class HistoryView(Gtk.TreeView):
    """ History View Class"""

    def __init__(self, base):
        Gtk.TreeView.__init__(self)
        self.model = self.setup_view()
        self.base = base
        self.pkg_view = HistoryPackageView(self.base)
        self.connect('cursor-changed', self.on_cursor_changed)
        self.is_populated = False

    def setup_view(self):
        """ Create Notebook list for single page  """
        model = Gtk.TreeStore(str, int)
        self.set_model(model)
        cell1 = Gtk.CellRendererText()
        column1 = Gtk.TreeViewColumn(_("History (Date/Time)"), cell1, markup=0)
        column1.set_resizable(False)
        column1.set_fixed_width(200)
        self.append_column(column1)
        model.set_sort_column_id(0, Gtk.SortType.DESCENDING)
        return model

    def reset(self):
        self.model.clear()
        self.is_populated = False
        self.pkg_view.reset()

    def populate(self, data):
        self.pkg_view.reset()
        self.model.clear()
        main = {}
        for tid, dt in data:
            da, t = dt.split('T')
            y, m, d = da.split('-')
            # year
            if y not in main:
                ycat = self.model.append(None, [y, -1])
                main[y] = (ycat, {})
            ycat, mdict = main[y]
            # month
            if m not in mdict:
                mcat = self.model.append(ycat, [m, -1])
                mdict[m] = (mcat, {})
            mcat, ddict = mdict[m]
            # day
            if d not in ddict:
                dcat = self.model.append(mcat, [d, -1])
                ddict[d] = dcat
            dcat = ddict[d]
            self.model.append(dcat, [t, tid])
        self.collapse_all()
        path = Gtk.TreePath.new_from_string("0:0:0:0")
        self.expand_to_path(path)
        self.get_selection().select_path(path)
        self.on_cursor_changed(self)
        self.is_populated = True

    def on_cursor_changed(self, widget):
        """
        a new History element is selected in history view
        """
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model is not None and iterator is not None:
                tid = model.get_value(iterator, 1)
                if tid != -1:
                    pkgs = self.base.get_root_backend().GetHistoryPackages(tid)
                    self.pkg_view.populate(pkgs)

    def get_selected(self):
        """Return the currently selected history tid"""
        if self.get_selection():
            (model, iterator) = self.get_selection().get_selected()
            if model is not None and iterator is not None:
                tid = model.get_value(iterator, 1)
                return tid
        else:
            return 0

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

import yumex.misc as misc
from gi.repository import Gdk, GdkPixbuf, GObject, Gtk
from yumex import const
from yumex.misc import CONFIG, TimeFunction, _, doGtkEvents, ngettext

logger = logging.getLogger('yumex.gui.views')


class SelectionView(Gtk.TreeView):
    """
    A Base view with an selection column
    """

    def __init__(self):
        """
        init the view
        """
        Gtk.TreeView.__init__(self)
        self.store = None

    def create_text_column_num(self, hdr, colno, resize=True, size=None,
                               markup=False):
        """
        Create a TreeViewColumn with data from a TreeStore column
        @param hdr: column header text
        @param colno: TreeStore column to get the data from
        @param resize: is resizable
        @param size:
        @param markup:
        """
        cell = Gtk.CellRendererText()
        if markup:
            column = Gtk.TreeViewColumn(hdr, cell, markup=colno)
        else:
            column = Gtk.TreeViewColumn(hdr, cell, text=colno)
        column.set_resizable(resize)
        if size:
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_fixed_width(size)
        self.append_column(column)
        return column

    def create_text_column(self, hdr, prop, size, sortcol=None,
                           click_handler=None, tooltip=None):
        """
        Create a TreeViewColumn with text and set
        the sorting properties and add it to the view
        """
        cell = Gtk.CellRendererText()  # Size Column
        column = Gtk.TreeViewColumn(hdr, cell)
        column.set_resizable(True)
        column.set_cell_data_func(cell, self.get_data_text, prop)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(size)
        if sortcol:
            column.set_sort_column_id(sortcol)
            # column.set_sort_indicator(True)
            # column.set_sort_order(Gtk.Gtk.SortType.ASCENDING)
        else:
            column.set_sort_column_id(-1)
        self.append_column(column)
        if click_handler:
            column.set_clickable(True)
            label = Gtk.Label(label=hdr)
            label.show()
            column.set_widget(label)
            widget = column.get_button()
            while not isinstance(widget, Gtk.Button):
                widget = widget.get_parent()
            widget.connect('button-release-event', click_handler)
            if tooltip:
                widget.set_tooltip_text(tooltip)

        return column

    def create_selection_colunm(self, attr, click_handler=None,
                                popup_handler=None, tooltip=None, icon=None):
        """Create an selection column, there get data via property function
        and a key attr
        """
        # Setup a selection column using a object attribute
        cell1 = Gtk.CellRendererToggle()  # Selection
        cell1.set_property('activatable', True)
        column1 = Gtk.TreeViewColumn("", cell1)
        column1.set_cell_data_func(cell1, self.get_data_bool, attr)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_sort_column_id(-1)
        self.append_column(column1)
        cell1.connect("toggled", self.on_toggled)
        column1.set_clickable(True)
        if click_handler:
            column1.connect('clicked', click_handler)
        label = Gtk.Label(label="+")
        label.show()
        column1.set_widget(label)
        if popup_handler:
            widget = column1.get_widget()
            while not isinstance(widget, Gtk.Button):
                widget = widget.get_parent()
            widget.connect('button-release-event', popup_handler)
            if icon:
                image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
                widget.set_image(image)
            if tooltip:
                widget.set_tooltip_text(tooltip)

    def create_selection_column_num(self, num, data_func=None, tooltip=None):
        """
        Create an selection column, there get data an TreeStore Column
        @param num: TreeStore column to get data from
        @param data_func:
        @param tooltip:
        """
        # Setup a selection column using a column num

        column = Gtk.TreeViewColumn(None, None)
        # Selection checkbox
        selection = Gtk.CellRendererToggle()  # Selection
        selection.set_property('activatable', True)
        column.pack_start(selection, False)
        if data_func:
            column.set_cell_data_func(selection, data_func)
        else:
            column.add_attribute(selection, "active", num)
        column.set_resizable(True)
        column.set_sort_column_id(-1)
        self.append_column(column)
        selection.connect("toggled", self.on_toggled)
        if tooltip:
            label = Gtk.Label(label="")
            label.show()
            column.set_widget(label)
            widget = column.get_widget()
            while not isinstance(widget, Gtk.Button):
                widget = widget.get_parent()
            widget.set_tooltip_text(tooltip)

        return column

    def create_selection_text_column(self, hdr, select_func, text_attr,
                                     size=200):
        """
        Create an selection column, there get data an TreeStore Column
        """
        # Setup a selection column using a column num

        column = Gtk.TreeViewColumn(hdr, None)
        # Selection checkbox
        selection = Gtk.CellRendererToggle()  # Selection
        selection.set_property('activatable', True)
        selection.connect("toggled", self.on_toggled)
        column.pack_start(selection, False)
        column.set_cell_data_func(selection, select_func)
        text = Gtk.CellRendererText()
        column.pack_start(text, False)
        column.set_cell_data_func(text, self.get_data_text, text_attr)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(size)
        column.set_sort_column_id(-1)
        self.append_column(column)
        return column

    def get_data_text(self, column, cell, model, iterator, prop):
        """property function to get string data from a object in
        the TreeStore based on an attributes key
        """
        obj = model.get_value(iterator, 0)
        if obj:
            cell.set_property('text', getattr(obj, prop))
            cell.set_property('foreground-rgba', obj.color)

    def get_data_bool(self, column, cell, model, iterator, prop):
        """Property function to get boolean data from a object in
        the TreeStore based on an attributes key
        """
        obj = model.get_value(iterator, 0)
        cell.set_property("visible", True)
        if obj:
            cell.set_property("active", getattr(obj, prop))

    def on_toggled(self, widget, path):
        """
        selection togged handler
        overload in child class
        """
        pass

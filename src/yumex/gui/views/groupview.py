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

from gi.repository import Gtk, GObject, GdkPixbuf
from yumex.common import _

logger = logging.getLogger('yumex.gui.views')


class Group:
    """ Object to represent a dnf group/category """
    def __init__(self, grpid, grp_name, grp_desc, inst, is_category=False):
        self.id = grpid
        self.name = grp_name
        self.description = grp_desc
        self.installed = inst
        self.category = is_category
        self.selected = False


class GroupView(Gtk.TreeView):
    __gsignals__ = {
        'group-changed':
        (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING, ))
    }

    def __init__(self, qview, base):
        Gtk.TreeView.__init__(self)
        self.base = base
        self.model = self.setup_view()
        self.queue = qview.queue
        self.queueView = qview
        self.currentCategory = None
        self._groups = None
        self.selected_group = None
        self.connect('cursor-changed', self.on_cursor_changed)

    def setup_view(self):
        """ Setup Group View  """
        model = Gtk.TreeStore(GObject.TYPE_PYOBJECT)

        self.set_model(model)
        column = Gtk.TreeViewColumn(None, None)
        # Selection checkbox
        selection = Gtk.CellRendererToggle()  # Selection
        selection.set_property('activatable', True)
        column.pack_start(selection, False)
        column.set_cell_data_func(selection, self.set_checkbox)
        selection.connect("toggled", self.on_toggled)
        self.append_column(column)
        column = Gtk.TreeViewColumn(None, None)
        # Queue Status (install/remove group)
        state = Gtk.CellRendererPixbuf()  # Queue Status
        state.set_property('stock-size', 1)
        column.pack_start(state, False)
        column.set_cell_data_func(state, self.queue_pixbuf)

        # category/group icons
        icon = Gtk.CellRendererPixbuf()
        icon.set_property('stock-size', 1)
        column.pack_start(icon, False)
        column.set_cell_data_func(icon, self.grp_pixbuf)

        category = Gtk.CellRendererText()
        column.pack_start(category, False)
        column.set_cell_data_func(category, self.get_data_text, 'name')

        self.append_column(column)
        self.set_headers_visible(False)
        return model

    def get_data_text(self, column, cell, model, iterator, prop):
        """property function to get string data from a object in the
        TreeStore based on  an attributes key
        """
        obj = model.get_value(iterator, 0)
        if obj:
            cell.set_property('text', getattr(obj, prop))

    def set_checkbox(self, column, cell, model, iterator, data=None):
        obj = model.get_value(iterator, 0)
        if obj:
            if obj.category:
                cell.set_property('visible', False)
            else:
                cell.set_property('visible', True)
                cell.set_property('active', obj.selected)

    def on_toggled(self, widget, path):
        """ Group selection handler """
        iterator = self.model.get_iter(path)
        obj = self.model.get_value(iterator, 0)
        action = self.queue.has_group(obj)
        if action:  # Group is in the queue, remove it from the queue
            self.queue.remove_group(obj, action)
        else:
            if obj.installed:  # Group is installed add it to queue for removal
                self.queue.add_group(obj, 'r')  # Add for remove
            else:  # Group is not installed, add it to queue for installation
                self.queue.add_group(obj, 'i')  # Add for install
        self.queueView.refresh()

    def on_cursor_changed(self, widget):
        """
        a new group is selected in group view
        """
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model is not None and iterator is not None:
                obj = self.model.get_value(iterator, 0)
                if not obj.category and obj.id != self.selected_group:
                    self.selected_group = obj.id
                    # send the group-changed signal
                    self.emit('group-changed', obj.id)

    def populate(self, data):
        self.freeze_child_notify()
        self.set_model(None)
        self.model.clear()
        self._groups = data
        self.set_model(self.model)
        for cat, catgrps in data:
            # cat: [category_id, category_name, category_desc]
            (catid, name, desc) = cat
            obj = Group(catid, name, desc, False, True)
            node = self.model.append(None, [obj])
            for grp in catgrps:
                # [group_id, group_name, group_desc, group_is_installed]
                (grpid, grp_name, grp_desc, inst) = grp
                obj = Group(grpid, grp_name, grp_desc, inst, False)
                self.model.append(node, [obj])
        self.thaw_child_notify()
        self.selected_group = None

    def queue_pixbuf(self, column, cell, model, iterator, data=None):
        """
        Cell Data function for
        """
        obj = model.get_value(iterator, 0)
        if not obj.category:
            action = self.queue.has_group(obj.id)
            icon = 'non-starred-symbolic'
            if obj.installed:
                icon = 'starred'
            if action:
                if action == 'i':
                    icon = 'network-server'
                else:
                    icon = 'edit-delete'
            cell.set_property('icon-name', icon)
            cell.set_property('visible', True)
        else:
            cell.set_property('visible', False)

    def grp_pixbuf(self, column, cell, model, iterator, data=None):
        """
        Cell Data function for recent Column, shows pixmap
        if recent Value is True.
        """
        obj = model.get_value(iterator, 0)
        pix = None
        fn = "/usr/share/pixmaps/comps/%s.png" % obj.id
        if os.access(fn, os.R_OK):
            pix = self._get_pix(fn)
        else:  # Try to get the parent icon
            parent = model.iter_parent(iterator)
            if parent:
                cat_id = model[parent][0].id  # get the parent cat_id
                fn = "/usr/share/pixmaps/comps/%s.png" % cat_id
                if os.access(fn, os.R_OK):
                    pix = self._get_pix(fn)
        if pix:
            cell.set_property('visible', True)
            cell.set_property('pixbuf', pix)
        else:
            cell.set_property('visible', False)

    def _get_pix(self, fn):
        """
        Get a pix buffer from a file, resize it to 24 px, if needed
        @param fn:
        """
        imgsize = 24
        pix = GdkPixbuf.Pixbuf.new_from_file(fn)
        if pix.get_height() != imgsize or pix.get_width() != imgsize:
            pix = pix.scale_simple(imgsize, imgsize, GdkPixbuf.INTERP_BILINEAR)
        return pix

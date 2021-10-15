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
from yumex.gui.views.packagequeue import PackageQueue


class QueueView(Gtk.TreeView):
    __gsignals__ = {'queue-refresh': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_INT,))}

    def __init__(self, queue_menu):
        Gtk.TreeView.__init__(self)
        self.store = self._setup_model()
        self.queue = PackageQueue()
        self.queue_menu = queue_menu
        self.connect('button-press-event',
                     self.on_QueueView_button_press_event)
        remove_menu = self.queue_menu.get_children()[
            0]  # get the first child (remove menu)
        remove_menu.connect('activate', self.deleteSelected)

    def _setup_model(self):
        """
        Setup the model and view
        """
        model = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.set_model(model)
        cell1 = Gtk.CellRendererText()
        column1 = Gtk.TreeViewColumn(_("Packages"), cell1, markup=0)
        column1.set_resizable(True)
        self.append_column(column1)

        cell2 = Gtk.CellRendererText()
        column2 = Gtk.TreeViewColumn(_("Summary"), cell2, text=1)
        column2.set_resizable(True)
        self.append_column(column2)
        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        return model

    def deleteSelected(self, widget=None):
        rmvlist = []
        model, paths = self.get_selection().get_selected_rows()
        for path in paths:
            row = model[path]
            if row.parent is not None:
                rmvlist.append(row[0])
        for pkg in self.filter_pkgs_from_list(rmvlist):
            self.queue.remove(pkg)
            if pkg.queued == "do" and pkg.installed:
                pkg.downgrade_po.queued = None
                pkg.downgrade_po.set_select(not pkg.selected)
                pkg.action = "r"  # reset action type of installed package
            pkg.queued = None
            pkg.set_select(not pkg.selected)
        self.queue.remove_groups(rmvlist)
        self.refresh()

    def on_QueueView_button_press_event(self, treeview, event):
        """
        Mouse button clicked in package view handler
        :param treeview:
        :param event:
        """
        if event.button == 3:  # Right Click
            popup = self.queue_menu
            popup.popup(None, None, None, None, event.button, event.time)
            return True

    def filter_pkgs_from_list(self, rlist):
        """
        return packages in queue where str(pkg) is in a list
        @param rlist:
        """
        rclist = []
        for action in const.QUEUE_PACKAGE_TYPES:
            pkg_list = self.queue.packages[action]
            if pkg_list:
                rclist.extend([x for x in pkg_list if str(x) in rlist])
        return rclist

    def refresh(self):
        """ Populate view with data from queue """
        self.store.clear()
        pkg_list = self.queue.packages['u'] + self.queue.packages['o']
        label = "<b>%s</b>" % ngettext(
            "Package to update", "Packages to update", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['i']
        label = "<b>%s</b>" % ngettext(
            "Package to install", "Packages to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['r']
        label = "<b>%s</b>" % ngettext(
            "Package to remove", "Packages to remove", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['ri']
        label = "<b>%s</b>" % ngettext(
            "Package to reinstall", "Packages to reinstall", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['li']
        label = "<b>%s</b>" % ngettext(
            "RPM file to install", "RPM files to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        grps = self.queue.groups['i']
        label = "<b>%s</b>" % ngettext(
            "Group to install", "Groups to install", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        grps = self.queue.groups['r']
        label = "<b>%s</b>" % ngettext(
            "Group to remove", "Groups to remove", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        self.populate_list_downgrade()
        self.expand_all()
        self.emit('queue-refresh', self.queue.total())

    def populate_list(self, label, pkg_list):
        parent = self.store.append(None, [label, ""])
        for pkg in pkg_list:
            self.store.append(parent, [str(pkg), pkg.summary])

    def populate_group_list(self, label, grps):
        parent = self.store.append(None, [label, ""])
        for grp in grps.values():
            self.store.append(parent, [grp.name, grp.description])

    def populate_list_downgrade(self):
        pkg_list = self.queue.packages['do']
        label = "<b>%s</b>" % ngettext(
            "Package to downgrade", "Packages to downgrade", len(pkg_list))
        if len(pkg_list) > 0:
            parent = self.store.append(None, [label, ""])
            for pkg in pkg_list:
                item = self.store.append(parent,
                                         [str(pkg.downgrade_po), pkg.summary])
                self.store.append(
                    item, [_("<b>Downgrade to</b> %s ") %
                           str(pkg), ""])

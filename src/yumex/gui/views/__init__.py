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
from yumex.gui.views.selectionview import SelectionView




class PackageQueue:
    """
    A Queue class to store selected packages/groups and the pending actions
    """

    def __init__(self):
        self.packages = {}
        self._setup_packages()
        self.groups = {'i': {}, 'r': {}}
        self._name_arch_index = {}

    def _setup_packages(self):
        for key in const.QUEUE_PACKAGE_TYPES:
            self.packages[key] = []

    def clear(self):
        del self.packages
        self.packages = {}
        self._setup_packages()
        self.groups = {'i': {}, 'r': {}}
        self._name_arch_index = {}

    def get(self, action=None):
        if action is None:
            return self.packages
        else:
            return self.packages[action]

    def total(self):
        num = 0
        for key in const.QUEUE_PACKAGE_TYPES:
            num += len(self.packages[key])
        num += len(self.groups['i'].keys())
        num += len(self.groups['r'].keys())
        return num

    def add(self, pkg, action=None):
        """Add a package to queue"""
        if not action:
            action = pkg.action
        na = "%s.%s" % (pkg.name, pkg.arch)
        if pkg not in self.packages[action] and \
                na not in self._name_arch_index:
            self.packages[action].append(pkg)
            na = "%s.%s" % (pkg.name, pkg.arch)
            self._name_arch_index[na] = 1

    def remove(self, pkg, action=None):
        """Remove package from queue"""
        if not action:
            action = pkg.action
        na = "%s.%s" % (pkg.name, pkg.arch)
        if pkg in self.packages[action]:
            self.packages[action].remove(pkg)
            del self._name_arch_index[na]

    def has_pkg_with_name_arch(self, pkg):
        na = "%s.%s" % (pkg.name, pkg.arch)
        return na in self._name_arch_index

    def add_group(self, grp, action):
        """

        @param grp: Group object
        @param action:
        """
        logger.debug('add_group : %s - %s', grp.id, action)
        grps = self.groups[action]
        if grp.id not in grps:
            grps[grp.id] = grp
            grp.selected = True

    def remove_group(self, grp, action):
        """

        @param grp: Group object
        @param action:
        """
        logger.debug('removeGroup : %s - %s', grp.id, action)
        grps = self.groups[action]
        if grp.id in grps:
            del grps[grp.id]
            grp.selected = False

    def remove_all_groups(self):
        """
        remove all groups from queue
        """
        for action in ('i', 'r'):
            for grp in self.groups[action]:
                self.remove_group(grp, action)

    def remove_groups(self, group_names):
        """
        remove groups from queue based on list of grp_ids
        """
        for action in ('i', 'r'):
            new_dict = {}
            grps = self.groups[action]
            for grp in grps.values():
                if grp.name not in group_names:
                    new_dict[grp.id] = grp  # copy to new dict
                else:  # unselect the group object
                    grp.selected = False
            self.groups[action] = new_dict

    def has_group(self, grp_id):
        """ check if group is in package queue """
        for action in ['i', 'r']:
            grps = self.groups[action]
            if grp_id in grps:
                return action
        return None

    def get_groups(self):
        """ get (grp_id, action) generator"""
        for action in ('i', 'r'):
            for grp in self.groups[action].values():
                yield grp.id, action


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


class HistoryPackageView(Gtk.TreeView):
    """ History Package View Class"""

    def __init__(self, base):
        Gtk.TreeView.__init__(self)
        self.model = self.setup_view()
        self.base = base

    def setup_view(self):
        """ Create Notebook list for single page  """
        model = Gtk.TreeStore(str)
        self.set_model(model)
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("History Packages"), cell, markup=0)
        column.set_resizable(True)
        # column1.set_fixed_width(200)
        self.append_column(column)
        # model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        return model

    def reset(self):
        self.model.clear()

    def populate(self, data):
        self.model.clear()
        # Order by package name.arch
        names = {}
        names_pair = {}
        for elem in data:
            pkg_id, state, is_inst = elem
            (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
            na = "%s.%s" % (n, a)
            if state in const.HISTORY_UPDATE_STATES:  # part of a pair
                if na in names_pair:
                    # this is the updating pkg
                    if state in const.HISTORY_NEW_STATES:
                        names_pair[na].insert(0, elem)  # add first in list
                    else:
                        names_pair[na].append(elem)
                else:
                    names_pair[na] = [elem]
            else:
                names[na] = [elem]

        # order by primary state
        states = {}
        # pkgs without relatives
        for na in sorted(list(names)):
            pkg_list = names[na]
            pkg_id, state, is_inst = pkg_list[
                0]  # Get first element (the primary (new) one )
            if state in states:
                states[state].append(pkg_list)
            else:
                states[state] = [pkg_list]
        # pkgs with releatives
        for na in sorted(list(names_pair)):
            pkg_list = names_pair[na]
            pkg_id, state, is_inst = pkg_list[
                0]  # Get first element (the primary (new) one )
            if state in states:
                states[state].append(pkg_list)
            else:
                states[state] = [pkg_list]
        # apply packages to model in right order
        for state in const.HISTORY_SORT_ORDER:
            if state in states:
                num = len(states[state])
                cat = self.model.append(
                    None, ["<b>%s (%i)</b>" %
                           (const.HISTORY_STATE_LABLES[state], num)])
                for pkg_list in states[state]:
                    pkg_id, st, is_inst = pkg_list[0]
                    if is_inst:
                        name = '<span foreground="%s">%s</span>' % (
                            CONFIG.conf.color_install,
                            misc.pkg_id_to_full_name(pkg_id))
                    else:
                        name = misc.pkg_id_to_full_name(pkg_id)
                    pkg_cat = self.model.append(cat, [name])
                    if len(pkg_list) == 2:
                        pkg_id, st, is_inst = pkg_list[1]
                        name = misc.pkg_id_to_full_name(pkg_id)
                        self.model.append(pkg_cat, [name])
        self.expand_all()




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
    __gsignals__ = {'group-changed': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_STRING,))}

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
        selection = Gtk.CellRendererToggle()    # Selection
        selection.set_property('activatable', True)
        column.pack_start(selection, False)
        column.set_cell_data_func(selection, self.set_checkbox)
        selection.connect("toggled", self.on_toggled)
        self.append_column(column)
        column = Gtk.TreeViewColumn(None, None)
        # Queue Status (install/remove group)
        state = Gtk.CellRendererPixbuf()    # Queue Status
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
            pix = pix.scale_simple(imgsize, imgsize,
                                   GdkPixbuf.INTERP_BILINEAR)
        return pix

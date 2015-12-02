# -*- coding: utf-8 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 -2014 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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


from __future__ import absolute_import

import os
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango

from yumex import const
from yumex.misc import _, P_, CONFIG, doGtkEvents, TimeFunction, \
     check_dark_theme

logger = logging.getLogger('yumex.gui.views')


class SelectionView(Gtk.TreeView):
    '''
    A Base view with an selection column
    '''

    def __init__(self):
        '''
        init the view
        @param widget: the gtk TreeView widget
        '''
        Gtk.TreeView.__init__(self)
        self.store = None

    def create_text_column_num(self, hdr, colno, resize=True, size=None,
                               markup=False):
        '''
        Create a TreeViewColumn with data from a TreeStore column
        @param hdr: column header text
        @param colno: TreeStore column to get the data from
        @param resize: is resizable
        '''
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
            #column.connect('clicked', click_handler)
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
        '''Create an selection column, there get data via property function
        and a key attr

        @param attr: key attr for property funtion
        '''
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
        '''
        Create an selection column, there get data an TreeStore Column
        @param num: TreeStore column to get data from
        '''
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
        '''
        Create an selection column, there get data an TreeStore Column
        @param num: TreeStore column to get data from
        '''
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
        '''property function to get string data from a object in
        the TreeStore based on an attributes key
        '''
        obj = model.get_value(iterator, 0)
        if obj:
            cell.set_property('text', getattr(obj, prop))
            cell.set_property('foreground-rgba', obj.color)

    def get_data_bool(self, column, cell, model, iterator, prop):
        '''Property function to get boolean data from a object in
        the TreeStore based on an attributes key
        '''
        obj = model.get_value(iterator, 0)
        cell.set_property("visible", True)
        if obj:
            cell.set_property("active", getattr(obj, prop))

    def on_toggled(self, widget, path):
        '''
        selection togged handler
        overload in child class
        '''
        pass


class PackageView(SelectionView):
    __gsignals__ = {'pkg-changed': (GObject.SignalFlags.RUN_FIRST,
                                    None,
                                    (GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, qview, arch_menu, group_mode=False):
        self.logger = logging.getLogger('yumex.PackageView')
        SelectionView.__init__(self)
        self.set_name('YumexPackageView')
        self.group_mode = group_mode
        self._click_header_state = ""
        self.queue = qview.queue
        self.queueView = qview
        self.arch_menu = arch_menu
        self.store = self._setup_model()
        self.connect('cursor-changed', self.on_cursor_changed)
        self.connect('button-press-event', self.on_mouse_button)
        self.state = 'normal'
        self._last_selected = []
        self.popup = None
        if self.group_mode:
            self._click_header_active = True
        else:
            self._click_header_active = False

    def _setup_model(self):
        '''
        Setup the model and view
        '''
        store = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.set_model(store)
        if self.group_mode:
            self.create_selection_colunm('selected',
                click_handler=self.on_section_header_clicked_group,
                popup_handler=self.on_section_header_button,
                tooltip=_("Click to install all/remove all"))
        else:
            self.create_selection_colunm('selected',
                click_handler=self.on_section_header_clicked,
                popup_handler=self.on_section_header_button,
                tooltip=_("Click to select/deselect all"))
        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()  # new
        cell2.set_property('icon-name', 'list-add-symbolic')
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)
        column2.set_clickable(True)

        self.create_text_column(_("Package"), 'name', size=200)

        self.create_text_column(_("Ver."), 'fullver', size=120)
        self.create_text_column(
            _("Arch."), 'arch', size=60,
            click_handler=self.arch_menu.on_arch_clicked,
            tooltip=_('click to filter archs'))
        self.create_text_column(_("Summary"), 'summary', size=400)
        self.create_text_column(_("Repo."), 'repository', size=90)
        self.create_text_column(_("Size"), 'sizeM', size=90)
        self.set_search_column(1)
        self.set_enable_search(True)
        # store.set_sort_column_id(1, Gtk.Gtk.SortType.ASCENDING)
        self.set_reorderable(False)
        self.set_fixed_height_mode(True)
        return store

    def on_section_header_button(self, button, event):
        if event.button == 3:  # Right click
            print("Right Click on selection column header")

    def on_mouse_button(self, button, event):
        """Handle mouse click in view."""
        if event.button == 3:  # Right Click
            x = int(event.x)
            y = int(event.y)
            pthinfo = self.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                self.grab_focus()
                self.set_cursor(path, col, 0)
                iterator = self.store.get_iter(path)
                pkg = self.store.get_value(iterator, 0)
                print("rc pkg:", str(pkg))
                # Only open popup menu for installed packages
                if not pkg.installed or pkg.queued:
                    return
                self.popup = self._get_package_popup(pkg, path)
                self.popup.popup(None, None, None, None,
                                 event.button, event.time)
                return True
        else:
            return False

    def _get_package_popup(self, pkg, path):
        """ Create a right click menu, for a given package."""
        # get available downgrades
        popup = Gtk.Menu()
        mi = Gtk.MenuItem(_("Reinstall Package"))
        mi.connect('activate', self.on_package_reinstall, pkg)
        popup.add(mi)
        # Show downgrade menu only if there is any avaliable downgrades
        do_pkgs = pkg.downgrades
        if do_pkgs:
            print(do_pkgs)
            popup_sub = Gtk.Menu()
            for do_pkg in do_pkgs:
                mi = Gtk.MenuItem(str(do_pkg))
                mi.set_use_underline(False)
                mi.connect('button-press-event',
                           self.on_package_downgrade, pkg, do_pkg)
                popup_sub.add(mi)
            popup_sub.show_all()
            mi = Gtk.MenuItem(_("Downgrade Package"))
            mi.set_submenu(popup_sub)
            popup.add(mi)
        popup.show_all()
        return popup

    def on_package_reinstall(self, widget, pkg):
        """Handler for package right click menu"""
        logger.debug('reinstall: %s ' % str(pkg))
        pkg.queued = 'ri'
        pkg.selected = True
        self.queue.add(pkg, 'ri')
        self.queueView.refresh()
        self.queue_draw()

    def on_package_downgrade(self, widget, event, pkg, do_pkg):
        """Downgrade package right click menu handler"""
        if event.button == 1:  # Left Click
            logger.debug('downgrade to : %s ' % str(do_pkg))
            #pkg.action = 'do'
            pkg.queued = 'do'
            pkg.selected = True
            pkg.downgrade_po = do_pkg
            do_pkg.queued = 'do'
            do_pkg.selected = True
            do_pkg.downgrade_po = pkg
            self.queue.add(do_pkg, 'do')
            self.queueView.refresh()
            self.queue_draw()

    def on_section_header_clicked(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal':  # deselect all
            self._last_selected = self.get_selected()
            self.select_all()
            self.state = 'selected'
        elif self.state == 'selected':  # select all
            self.state = 'deselected'
            self.deselect_all()
        elif self.state == 'deselected':  # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def on_section_header_clicked_group(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal':  # deselect all
            self._last_selected = self.get_selected()
            self.install_all()
            self.state = 'install-all'
        elif self.state == 'install-all':  # select all
            self.state = 'remove-all'
            self.deselect_all()
            self.remove_all()
        elif self.state == 'remove-all':  # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def on_cursor_changed(self, widget):
        '''
        a new group is selected in group view
        '''
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model is not None and iterator is not None:
                pkg = model.get_value(iterator, 0)
                self.emit('pkg-changed', pkg)  # send the group-changed signal

    def set_header_click(self, state):
        self._click_header_active = state
        self._click_header_state = ""

    def select_all(self):
        '''
        Select all packages in the view
        '''
        for el in self.store:
            obj = el[0]
            if not obj.queued == obj.action:
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queueView.refresh()
        self.queue_draw()

    def deselect_all(self):
        '''
        Deselect all packages in the view
        '''
        for el in self.store:
            obj = el[0]
            if obj.queued == obj.action:
                obj.queued = None
                self.queue.remove(obj)
                obj.set_select(not obj.selected)
        self.queueView.refresh()
        self.queue_draw()

    def select_by_keys(self, keys):
        '''

        @param keys:
        '''
        iterator = self.store.get_iter_first()
        while iterator is not None:
            obj = self.store.get_value(iterator, 0)
            if obj in keys and not obj.selected:
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(True)
            elif obj.selected:
                obj.queued = None
                self.queue.remove(obj)
                obj.set_select(False)
            iterator = self.store.iter_next(iterator)
        self.queueView.refresh()
        self.queue_draw()

    def get_selected(self):
        '''

        '''
        selected = []
        for el in self.store:
            obj = el[0]
            if obj.selected:
                selected.append(obj)
        return selected

    def get_notselected(self):
        '''

        '''
        notselected = []
        for el in self.store:
            obj = el[0]
            if not obj.queued == obj.action:
                notselected.append(obj)
        return notselected

    def new_pixbuf(self, column, cell, model, iterator, data):
        """
        Cell Data function for recent Column, shows pixmap
        if recent Value is True.
        """
        pkg = model.get_value(iterator, 0)
        if pkg:
            action = pkg.queued
            if action:
                if action in ('u', 'i', 'o'):
                    icon = 'emblem-downloads'
                elif action == 'ri':
                    icon = 'gtk-refresh'
                elif action == 'do':
                    icon = 'gtk-go-down'
                else:
                    icon = 'edit-delete'
                cell.set_property('visible', True)
                cell.set_property('icon-name', icon)
            else:
                cell.set_property('visible', pkg.recent)
                cell.set_property('icon-name', 'document-new')
        else:
            cell.set_property('visible', False)

    @TimeFunction
    def populate(self, pkgs):
        self.freeze_child_notify()
        self.set_model(None)
        self.store.clear()
        self.set_model(self.store)
        if pkgs:
            i = 0
            for po in sorted(pkgs, key=lambda po: po.name):
                i += 1
                if i % 500:  # Handle Gtk event, so gui dont freeze
                    doGtkEvents()
                self.store.append([po, str(po)])
        self.thaw_child_notify()
        # reset the selection column header selection state
        self.state = 'normal'
        self._last_selected = []

    def on_toggled(self, widget, path):
        """ Package selection handler """
        iterator = self.store.get_iter(path)
        obj = self.store.get_value(iterator, 0)
        self.togglePackage(obj)
        self.queueView.refresh()

    def togglePackage(self, obj):
        '''
        Toggle the package queue status
        @param obj:
        '''
        if obj.action == 'do' or obj.queued == 'do':
            self._toggle_downgrade(obj)
        else:
            if obj.queued == obj.action:
                obj.queued = None
                self.queue.remove(obj)
                obj.selected = not obj.selected
            elif not self.queue.has_pkg_with_name_arch(obj):
                obj.queued = obj.action
                self.queue.add(obj)
                obj.selected = not obj.selected

    def _toggle_downgrade(self, obj):
        if obj.queued == 'do':  # all-ready queued
            related_po = obj.downgrade_po
            if obj.installed:  # is obj the installed pkg ?
                self.queue.remove(related_po, 'do')
            else:
                self.queue.remove(obj, 'do')
            obj.queued = None
            obj.selected = False
            related_po.queued = None
            related_po.selected = False
            # the releated package
        else:
            pkgs = obj.downgrades  # get the installed po
            if pkgs:
                # downgrade the po
                pkg = pkgs[0]
                # Installed pkg is all-ready downgraded by another package
                if pkg.action == 'do' or \
                    self.queue.has_pkg_with_name_arch(pkg):
                        return
                pkg.queued = 'do'
                pkg.selected = True
                pkg.downgrade_po = obj
                obj.queued = 'do'
                obj.selected = True
                obj.downgrade_po = pkg
                self.queue.add(obj, 'do')
        self.queueView.refresh()
        self.queue_draw()

    def install_all(self):
        '''
        Select all packages in the view
        '''
        for el in self.store:
            obj = el[0]
            if not obj.queued == obj.action and obj.action == 'i':
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queueView.refresh()
        self.queue_draw()

    def remove_all(self):
        '''
        Select all packages in the view
        '''
        for el in self.store:
            obj = el[0]
            if not obj.queued == obj.action and obj.action == 'r':
                obj.queued = obj.action
                self.queue.add(obj)
                obj.set_select(not obj.selected)
        self.queueView.refresh()
        self.queue_draw()


class PackageQueue:
    '''
    A Queue class to store selected packages/groups and the pending actions
    '''

    def __init__(self):
        '''
        Init the queue
        '''
        self.packages = {}
        self._setup_packages()
        self.groups = {}
        self.groups['i'] = {}
        self.groups['r'] = {}
        self._name_arch_index = {}

    def _setup_packages(self):
        for key in const.QUEUE_PACKAGE_TYPES:
            self.packages[key] = []

    def clear(self):
        '''

        '''
        del self.packages
        self.packages = {}
        self._setup_packages()
        self.groups = {}
        self.groups['i'] = {}
        self.groups['r'] = {}
        self._name_arch_index = {}

    def get(self, action=None):
        '''

        @param action:
        '''
        if action is None:
            return self.packages
        else:
            return self.packages[action]

    def total(self):
        '''

        '''
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
        if not pkg in self.packages[action] and \
            not na in self._name_arch_index:
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
        '''

        @param grp: Group object
        @param action:
        '''
        logger.debug('add_group : %s - %s' % (grp.id, action))
        grps = self.groups[action]
        if not grp.id in grps:
            grps[grp.id] = grp
            grp.selected = True

    def remove_group(self, grp, action):
        '''

        @param grp: Group object
        @param action:
        '''
        logger.debug('removeGroup : %s - %s' % (grp.id, action))
        grps = self.groups[action]
        if grp.id in grps:
            del grps[grp.id]
            grp.selected = False

    def remove_all_groups(self):
        '''
        remove all groups from queue
        '''
        for action in ('i', 'r'):
            for grp in self.groups[action]:
                self.remove_group(grp, action)

    def remove_groups(self, group_names):
        '''
        remove groups from queue based on list of grp_ids
        '''
        for action in ('i', 'r'):
            new_dict = {}
            grps = self.groups[action]
            for grp in grps.values():
                if not grp.name in group_names:
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
                                    (GObject.TYPE_INT,))
                    }

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
        '''
        Setup the model and view
        '''
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
        '''

        '''
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
        '''
        Mouse button clicked in package view handler
        :param treeview:
        :param event:
        '''
        if event.button == 3:  # Right Click
            popup = self.queue_menu
            popup.popup(None, None, None, None, event.button, event.time)
            return True

    def filter_pkgs_from_list(self, rlist):
        '''
        return packages in queue where str(pkg) is in a list
        @param rlist:
        '''
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
        label = "<b>%s</b>" % P_(
            "Package to update", "Packages to update", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['i']
        label = "<b>%s</b>" % P_(
            "Package to install", "Packages to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['r']
        label = "<b>%s</b>" % P_(
            "Package to remove", "Packages to remove", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['ri']
        label = "<b>%s</b>" % P_(
            "Package to reinstall", "Packages to reinstall", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['li']
        label = "<b>%s</b>" % P_(
            "RPM file to install", "RPM files to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        grps = self.queue.groups['i']
        label = "<b>%s</b>" % P_(
            "Group to install", "Groups to install", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        grps = self.queue.groups['r']
        label = "<b>%s</b>" % P_(
            "Group to remove", "Groups files to remove", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        self.populate_list_downgrade()
        self.expand_all()
        self.emit('queue-refresh', self.queue.total())

    def populate_list(self, label, pkg_list):
        '''

        @param header:
        @param pkg_list:
        '''
        parent = self.store.append(None, [label, ""])
        for pkg in pkg_list:
            self.store.append(parent, [str(pkg), pkg.summary])

    def populate_group_list(self, label, grps):
        '''
        @param label:
        @param pkg_list:
        '''
        parent = self.store.append(None, [label, ""])
        for grp in grps.values():
            self.store.append(parent, [grp.name, grp.description])

    def populate_list_downgrade(self):
        '''

        '''
        pkg_list = self.queue.packages['do']
        label = "<b>%s</b>" % P_(
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
        '''

        @param widget:
        '''
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
            if not y in main:
                ycat = self.model.append(None, [y, -1])
                main[y] = (ycat, {})
            ycat, mdict = main[y]
            # month
            if not m in mdict:
                mcat = self.model.append(ycat, [m, -1])
                mdict[m] = (mcat, {})
            mcat, ddict = mdict[m]
            # day
            if not d in ddict:
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
        '''
        a new History element is selected in history view
        '''
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
        '''

        @param widget:
        '''
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
                cat = self.model.append(None, ["<b>%s (%i)</b>" %
                          (const.HISTORY_STATE_LABLES[state], num)])
                for pkg_list in states[state]:
                    pkg_id, st, is_inst = pkg_list[0]
                    if is_inst:
                        name = '<span foreground="%s">%s</span>' % (
                            CONFIG.conf.color_install, self._fullname(pkg_id))
                    else:
                        name = self._fullname(pkg_id)
                    pkg_cat = self.model.append(cat, [name])
                    if len(pkg_list) == 2:
                        pkg_id, st, is_inst = pkg_list[1]
                        name = self._fullname(pkg_id)
                        self.model.append(pkg_cat, [name])
        self.expand_all()

    def _fullname(self, pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s" % (n, e, v, r, a)
        else:
            return "%s-%s-%s.%s" % (n, v, r, a)


class RepoView(SelectionView):
    """
    This class controls the repo TreeView
    """
    def __init__(self):
        '''

        @param widget:
        '''
        SelectionView.__init__(self)
        self.headers = [_('Repository'), _('Filename')]
        self.store = self.setup_view()
        self.state = 'normal'
        self._last_selected = []

    def on_toggled(self, widget, path):
        """ Repo select/unselect handler """
        iterator = self.store.get_iter(path)
        state = self.store.get_value(iterator, 0)
        self.store.set_value(iterator, 0, not state)

    def on_section_header_clicked(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal':  # deselect all
            self._last_selected = self.get_selected()
            self.select_all(state=False)
            self.state = 'deselected'
        elif self.state == 'deselected':  # select all
            self.state = 'selected'
            self.select_all(state=True)
        elif self.state == 'selected':  # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def setup_view(self):
        """ Create models and columns for the Repo TextView  """
        store = Gtk.ListStore('gboolean', str, str, 'gboolean')
        self.set_model(store)
        # Setup Selection Column
        col = self.create_selection_column_num(
            0, tooltip=_("Click here to switch between\n"
                         " none/all/default selected"))
        col.set_clickable(True)
        col.connect('clicked', self.on_section_header_clicked)

        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()    # gpgcheck
        cell2.set_property('icon-name', 'dialog-password-symbolic')
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)

        # Setup reponame & repofile column's
        self.create_text_column_num(_('Repository'), 1)
        self.create_text_column_num(_('Name'), 2)
        self.set_search_column(1)
        self.set_reorderable(False)
        return store

    def populate(self, data):
        """ Populate a repo liststore with data """
        self.store.clear()
        for state, ident, name, gpg in data:
            self.store.append([state, ident, name, gpg])

    def new_pixbuf(self, column, cell, model, iterator, data):
        '''

        @param column:
        @param cell:
        @param model:
        @param iterator:
        '''
        gpg = model.get_value(iterator, 3)
        if gpg:
            cell.set_property('visible', True)
        else:
            cell.set_property('visible', False)

    def get_selected(self):
        '''

        '''
        selected = []
        for elem in self.store:
            state = elem[0]
            name = elem[1]
            if state:
                selected.append(name)
        return selected

    def get_notselected(self):
        '''

        '''
        notselected = []
        for elem in self.store:
            state = elem[0]
            name = elem[1]
            if not state:
                notselected.append(name)
        return notselected

    def select_by_keys(self, keys):
        '''

        @param keys:
        '''
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
    '''
    '''
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
        #column.add_attribute(category, 'markup', 1)
        column.set_cell_data_func(category, self.get_data_text, 'name')

        self.append_column(column)
        self.set_headers_visible(False)
        return model

    def get_data_text(self, column, cell, model, iterator, prop):
        '''property function to get string data from a object in the
        TreeStore based on  an attributes key
        '''
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
        '''
        a new group is selected in group view
        '''
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model is not None and iterator is not None:
                obj = self.model.get_value(iterator, 0)
                if not obj.category and obj.id != self.selected_group:
                    self.selected_group = obj.id
                    # send the group-changed signal
                    self.emit('group-changed', obj.id)

    def populate(self, data):
        '''

        @param data:
        '''
        self.freeze_child_notify()
        self.set_model(None)
        self.model.clear()
        self._groups = data
        self.set_model(self.model)
        for cat, catgrps in data:
            #print( cat, catgrps)
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
        '''
        Get a pix buffer from a file, resize it to 24 px, if needed
        @param fn:
        '''
        imgsize = 24
        pix = GdkPixbuf.Pixbuf.new_from_file(fn)
        if pix.get_height() != imgsize or pix.get_width() != imgsize:
            pix = pix.scale_simple(imgsize, imgsize,
                                   GdkPixbuf.INTERP_BILINEAR)
        return pix

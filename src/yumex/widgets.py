# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.



from gi.repository import Gtk
from gi.repository import Gdk, GdkPixbuf
from gi.repository import GObject, GLib, Gio
from datetime import date
from subprocess import call
import logging

from .misc import _, P_, CONFIG, format_number, doGtkEvents, format_block, TimeFunction, color_to_hex, get_color  # @UnusedImport
from .const import *  # @UnusedWildImport
import shutil


logger = logging.getLogger('yumex.widget')

class InfoProgressBar:

    def __init__(self, ui):
        self.ui = ui
        self.infobar = ui.get_object("infobar") # infobar revealer
        frame = ui.get_object("info_frame")
        new_bg = Gdk.RGBA()
        new_bg.parse("rgb(255,255,255)")
        frame.override_background_color (Gtk.StateFlags.NORMAL, new_bg)
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")

    def _show_infobar(self, show=True):
        self.infobar.set_reveal_child(show)

    def show_progress(self, state):
        if state:
            self.show_label()
        else:
            self.hide()

    def hide(self):
        self.label.hide()
        self.sublabel.hide()
        self.progress.hide()
        self._show_infobar(False)
        self.progress.set_text("")
        #self.progress.set_show_text (False)

    def hide_sublabel(self):
        self.sublabel.hide()

    def show_label(self):
        self.label.show()
        self.label.set_text("")

    def show_sublabel(self):
        self.sublabel.show()
        self.sublabel.set_text("")

    def show_all(self):
        self.show_label()
        self.show_sublabel()
        self.progress.show()

    def info(self, msg):
        self._show_infobar(True)
        self.show_label()
        self.label.set_text(msg)

    def info_sub(self, msg):
        self._show_infobar(True)
        self.show_sublabel()
        self.sublabel.set_text(msg)

    def set_progress(self, frac, label=None):
        if label:
            self.progress.set_text(label)
        if frac >= 0.0 and frac <= 1.0:
            self.infobar.show()
            self.progress.show()
            self.progress.set_fraction(frac)
            # make sure that the main label is shown, else the progres looks bad
            # this is normally happen when changlog or filelist info is needed for at package
            # and it will trigger the yum daemon to download the need metadata.
            if not self.label.get_property('visible'):
                self.info(_("Getting Package metadata"))




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

    def create_text_column_num(self, hdr, colno, resize=True, size=None, markup=False):
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

    def create_text_column(self, hdr, prop, size, sortcol=None, click_handler=None, tooltip=None):
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
            label = Gtk.Label(hdr)
            label.show()
            column.set_widget(label)
            widget = column.get_button()
            while not isinstance(widget, Gtk.Button) :
                widget = widget.get_parent()
            widget.connect('button-release-event', click_handler)
            if tooltip:
                widget.set_tooltip_text(tooltip)

        return column

    def create_selection_colunm(self, attr, click_handler=None, popup_handler=None, tooltip=None):
        '''
        Create an selection column, there get data via property function and a key attr
        @param attr: key attr for property funtion
        '''
        # Setup a selection column using a object attribute
        cell1 = Gtk.CellRendererToggle()  # Selection
        cell1.set_property('activatable', True)
        column1 = Gtk.TreeViewColumn("", cell1)
        column1.set_cell_data_func(cell1, self.get_data_bool, attr)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_fixed_width(25)
        column1.set_sort_column_id(-1)
        self.append_column(column1)
        cell1.connect("toggled", self.on_toggled)
        column1.set_clickable(True)
        if click_handler:
            column1.connect('clicked', click_handler)
        label = Gtk.Label("")
        label.show()
        column1.set_widget(label)
        if popup_handler:
            widget = column1.get_widget()
            while not isinstance(widget, Gtk.Button):
                widget = widget.get_parent()
            widget.connect('button-release-event', popup_handler)
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
            label = Gtk.Label("")
            label.show()
            column.set_widget(label)
            widget = column.get_widget()
            while not isinstance(widget, Gtk.Button):
                widget = widget.get_parent()
            widget.set_tooltip_text(tooltip)

        return column

    def create_selection_text_column(self, hdr, select_func, text_attr, size=200):
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
        '''
        a property function to get string data from a object in the TreeStore based on
        an attributes key
        @param column:
        @param cell:
        @param model:
        @param iterator:
        @param prop: attribute key
        '''
        obj = model.get_value(iterator, 0)
        if obj:
            cell.set_property('text', getattr(obj, prop))
            cell.set_property('foreground-rgba', obj.color)

    def get_data_bool(self, column, cell, model, iterator, prop):
        '''
        a property function to get boolean data from a object in the TreeStore based on
        an attributes key

        @param column:
        @param cell:
        @param model:
        @param iterator:
        @param prop: attribute key
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

class ArchMenu(GObject.GObject):
    '''
    Class to handle a menu to select what arch to show in package view
    '''
    __gsignals__ = {'arch-changed': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_STRING,))}

    def __init__(self, arch_menu_widget, archs):
        GObject.GObject.__init__(self)
        self.all_archs = archs
        self.current_archs = archs
        self.arch_menu_widget= arch_menu_widget
        self.arch_menu = self._setup_archmenu()


    def _setup_archmenu(self):
        arch_menu = self.arch_menu_widget
        for arch in self.all_archs:
            cb = Gtk.CheckMenuItem()
            cb.set_label(arch)
            cb.set_active(True)
            cb.show()
            cb.connect('toggled', self.on_archmenu_clicked)
            arch_menu.add(cb)
        return arch_menu

    def on_arch_clicked(self, button, event=None):
        #print('clicked : event : %s' % event.type)
        if event:
            self.arch_menu.popup(None, None, None, None, event.button, event.time)
            return True


    def on_archmenu_clicked(self, widget):
        state = widget.get_active()
        label = widget.get_label()
        if state:
            self.current_archs.append(label)
        else:
            self.current_archs.remove(label)
        archs = ",".join(self.current_archs)
        self.emit("arch-changed", archs)


class PackageView(SelectionView):
    __gsignals__ = { 'pkg-changed': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, qview, arch_menu, group_mode=False):
        self.logger = logging.getLogger('yumex.PackageView')
        SelectionView.__init__(self)
        self.group_mode = group_mode
        self._click_header_state = ""
        self.queue = qview.queue
        self.queueView = qview
        self.arch_menu = arch_menu
        self.store = self._setup_model()
        self.connect('cursor-changed', self.on_cursor_changed)
        self.state = 'normal'
        self._last_selected = []
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
                                          tooltip=_("Click to select/deselect all (updates only)"))
        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()  # new
        cell2.set_property('stock-id', Gtk.STOCK_ADD)
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)
        column2.set_clickable(True)

        self.create_text_column(_("Package"), 'name' , size=200)
        self.create_text_column(_("Ver."), 'fullver', size=120)
        self.create_text_column(_("Arch."), 'arch' , size=60, click_handler=self.arch_menu.on_arch_clicked, tooltip=_('click to filter archs'))
        self.create_text_column(_("Summary"), 'summary', size=400)
        self.create_text_column(_("Repo."), 'repository' , size=90)
        self.create_text_column(_("Size."), 'sizeM' , size=90)
        self.set_search_column(1)
        self.set_enable_search(True)
        # store.set_sort_column_id(1, Gtk.Gtk.SortType.ASCENDING)
        self.set_reorderable(False)
        return store


    def on_section_header_button(self, button, event):
        if event.button == 3:  # Right click
            print("Right Click on selection column header")


    def on_section_header_clicked(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal': # deselect all
            self._last_selected = self.get_selected()
            self.select_all()
            self.state = 'selected'
        elif self.state == 'selected': # select all
            self.state = 'deselected'
            self.deselect_all()
        elif self.state == 'deselected': # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []

    def on_section_header_clicked_group(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal': # deselect all
            self._last_selected = self.get_selected()
            self.install_all()
            self.state = 'install-all'
        elif self.state == 'install-all': # select all
            self.state = 'remove-all'
            self.deselect_all()
            self.remove_all()
        elif self.state == 'remove-all': # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []


    def on_cursor_changed(self, widget):
        '''
        a new group is selected in group view
        '''
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model != None and iterator != None:
                pkg = model.get_value(iterator, 0)
                self.emit('pkg-changed', pkg) # send the group-changed signal

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
        while iterator != None:
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
            if obj.is_installed():  # is obj the installed pkg ?
                self.queue.remove(obj)
                obj.action = "r"
            else:
                self.queue.remove(related_po)
                related_po.action = "r"
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
                if pkg.action == 'do' or self.queue.has_pkg_with_name_arch(pkg):  # Installed pkg is all-ready downgraded by another package
                    return
                pkg.action = 'do'
                pkg.queued = 'do'
                pkg.selected = True
                pkg.downgrade_po = obj
                obj.queued = 'do'
                obj.selected = True
                obj.downgrade_po = pkg
                self.queue.add(pkg)
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
        for key in QUEUE_PACKAGE_TYPES:
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
        if action == None:
            return self.packages
        else:
            return self.packages[action]

    def total(self):
        '''

        '''
        num = 0
        for key in QUEUE_PACKAGE_TYPES:
            num += len(self.packages[key])
        num += len(self.groups['i'].keys())
        num += len(self.groups['r'].keys())
        return num

    def add(self, pkg):
        '''

        @param pkg:
        '''
        na = "%s.%s" % (pkg.name, pkg.arch)
        if not pkg in self.packages[pkg.action] and not na in self._name_arch_index :
            self.packages[pkg.action].append(pkg)
            na = "%s.%s" % (pkg.name, pkg.arch)
            self._name_arch_index[na] = 1

    def remove(self, pkg):
        '''

        @param pkg:
        '''
        na = "%s.%s" % (pkg.name, pkg.arch)
        if pkg in self.packages[pkg.action]:
            self.packages[pkg.action].remove(pkg)
            del self._name_arch_index[na]

    def has_pkg_with_name_arch(self, pkg):
        na = "%s.%s" % (pkg.name, pkg.arch)
        return na in self._name_arch_index

    def add_group(self, grp, action):
        '''

        @param grp: Group object
        @param action:
        '''
        logger.debug('add_group : %s - %s' %(grp.id, action))
        grps = self.groups[action]
        if not grp.id in grps:
            grps[grp.id] = grp
            grp.selected = True

    def remove_group(self, grp, action):
        '''

        @param grp: Group object
        @param action:
        '''
        logger.debug('removeGroup : %s - %s' %(grp.id, action))
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
                    new_dict[grp.id] = grp # copy to new dict
                else: # unselect the group object
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

    def __init__(self, queue_menu):
        Gtk.TreeView.__init__(self)
        self.store = self._setup_model()
        self.queue = PackageQueue()
        self.queue_menu = queue_menu
        self.connect('button-press-event',self.on_QueueView_button_press_event)
        remove_menu = self.queue_menu.get_children()[0] # get the first child (remove menu)
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
            if row.parent != None:
                rmvlist.append(row[0])
        for pkg in self.filter_pkgs_from_list(rmvlist):
            self.queue.remove(pkg)
            if pkg.queued == "do" and pkg.is_installed():
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
        for action in QUEUE_PACKAGE_TYPES:
            pkg_list = self.queue.packages[action]
            if pkg_list:
                rclist.extend([x for x in pkg_list if str(x) in rlist])
        return rclist

    def refresh (self):
        """ Populate view with data from queue """
        self.store.clear()
        pkg_list = self.queue.packages['u'] + self.queue.packages['o']
        label = "<b>%s</b>" % P_("Package to update", "Packages to update", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['i']
        label = "<b>%s</b>" % P_("Package to install", "Packages to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['r']
        label = "<b>%s</b>" % P_("Package to remove", "Packages to remove", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['ri']
        label = "<b>%s</b>" % P_("Package to reinstall", "Packages to reinstall", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        pkg_list = self.queue.packages['li']
        label = "<b>%s</b>" % P_("RPM file to install", "RPM files to install", len(pkg_list))
        if len(pkg_list) > 0:
            self.populate_list(label, pkg_list)
        grps = self.queue.groups['i']
        label = "<b>%s</b>" % P_("Group to install", "Groups to install", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        grps = self.queue.groups['r']
        label = "<b>%s</b>" % P_("Group to remove", "Groups files to remove", len(pkg_list))
        if len(grps) > 0:
            self.populate_group_list(label, grps)
        self.populate_list_downgrade()
        self.expand_all()

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
            self.store.append(parent, [grp.name, grp.description ])

    def populate_list_downgrade(self):
        '''

        '''
        pkg_list = self.queue.packages['do']
        label = "<b>%s</b>" % P_("Package to downgrade", "Packages to downgrade", len(pkg_list))
        if len(pkg_list) > 0:
            parent = self.store.append(None, [label, ""])
            for pkg in pkg_list:
                item = self.store.append(parent, [str(pkg), pkg.summary])
                self.store.append(item, [_("<b>Downgrade to</b> %s ") % str(pkg.downgrade_po), ""])


class HistoryView(Gtk.TreeView):
    """ History View Class"""
    def __init__(self, base):
        '''

        @param widget:
        '''
        Gtk.TreeView.__init__(self)
        self.modify_font(SMALL_FONT)
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
        self.is_populated = True

    def on_cursor_changed(self, widget):
        '''
        a new History element is selected in history view
        '''
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model != None and iterator != None:
                tid = model.get_value(iterator, 1)
                if tid != -1:
                    pkgs = self.base.get_root_backend().GetHistoryPackages(tid)
                    self.pkg_view.populate(pkgs)

class HistoryPackageView(Gtk.TreeView):
    """ History Package View Class"""
    def __init__(self, base):
        '''

        @param widget:
        '''
        Gtk.TreeView.__init__(self)
        self.modify_font(SMALL_FONT)
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
            if state in HISTORY_UPDATE_STATES:  # part of a pair
                if na in names_pair:
                    if state in HISTORY_NEW_STATES:  # this is the updating pkg
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
            pkg_id, state, is_inst = pkg_list[0]  # Get first element (the primary (new) one )
            if state in states:
                states[state].append(pkg_list)
            else:
                states[state] = [pkg_list]
        # pkgs with releatives
        for na in sorted(list(names_pair)):
            pkg_list = names_pair[na]
            pkg_id, state, is_inst = pkg_list[0]  # Get first element (the primary (new) one )
            if state in states:
                states[state].append(pkg_list)
            else:
                states[state] = [pkg_list]
        # apply packages to model in right order
        for state in HISTORY_SORT_ORDER:
            if state in states:
                cat = self.model.append(None, ["<b>%s</b>" % HISTORY_STATE_LABLES[state]])
                for pkg_list in states[state]:
                    pkg_id, st, is_inst = pkg_list[0]
                    if is_inst:
                        name = '<span foreground="%s">%s</span>' % (CONFIG.conf.color_install, self._fullname(pkg_id))
                    else:
                        name = self._fullname(pkg_id)
                    pkg_cat = self.model.append(cat, [name])
                    if len(pkg_list) == 2:
                        pkg_id, st, is_inst = pkg_list[1]
                        name = self._fullname(pkg_id)
                        self.model.append(pkg_cat, [name])

    def _fullname(self, pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s" % (n, e, v, r, a)
        else:
            return "%s-%s-%s.%s" % (n, v, r, a)



class TextViewBase(Gtk.TextView):
    '''  Encapsulate a Gtk.TextView with support for adding and using Pango styles'''
    def __init__(self, window=None, url_handler=None):
        '''
        Setup the textview

        :param textview: the Gtk.TextView widget to use
        '''
        Gtk.TextView.__init__(self)
        self.set_right_margin(10)
        self.set_left_margin(10)
        self.set_margin_top(5)
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.buffer = self.get_buffer()
        self.endMark = self.buffer.create_mark("End", self.buffer.get_end_iter(), False)
        self.startMark = self.buffer.create_mark("Start", self.buffer.get_start_iter(), False)
        self._styles = {}
        self.default_style = None  # the default style (text tag)
        self.window = window
        if window:
            self.connect("motion_notify_event", self.on_mouse_motion)
        self.url_handler = url_handler

        # List of active URLs in the tab
        self.url_tags = []
        self.underlined_url = False
        self.url_list = {}

    def on_url_event(self, tag, widget, event, iterator):
        """ Catch when the user clicks the URL """
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            url = self.url_list[tag.get_property("name")]
            if self.url_handler:
                self.url_handler(url)

    def on_mouse_motion(self, widget, event, data=None):
        '''
        Mouse movement handler for TextView

        :param widget:
        :param event:
        :param data:
        '''
        window = widget.get_window(Gtk.TextWindowType.WIDGET)
        # Get x,y pos for widget
        w, x, y, mask = window.get_pointer()
        # convert coords to TextBuffer coords
        x, y = widget.window_to_buffer_coords(Gtk.TextWindowType.TEXT, x, y)
        # Get the tags on current pointer location
        tags = widget.get_iter_at_location(x, y).get_tags()
        # Remove underline and hand mouse pointer
        if self.underlined_url:
            self.underlined_url.set_property("underline", Pango.Underline.NONE)
            widget.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)
            self.underlined_url = None
        for tag in tags:
            if tag in self.url_tags:
                # underline the tags and change mouse pointer to hand
                tag.set_property("underline", Pango.Underline.SINGLE)
                widget.get_window(Gtk.TextWindowType.TEXT).set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
                self.underlined_url = tag
        return False


    def add_url(self, text, url, newline=False):
        """ Append URL to textbuffer and connect an event """
        # Try to see if we already got the current url as a tag
        tag = self.get_style(text)
        if not tag:
            tag = self.buffer.create_tag(text, foreground="blue", font_desc=SMALL_FONT)
            tag.connect("event", self.on_url_event)
            self.url_tags.append(tag)
            self.url_list[text] = url
            self._styles[text] = tag
        self.write(text, style=text, newline=newline)


    def add_style(self, tag, style):
        '''
        Add a new Pango style

        :param tag: text tag to indentify the style
        :param style: the Gtk.TextTag containing the style
        '''
        self._styles[tag] = style
        self.buffer.get_tag_table().add(self._styles[tag])

    def get_style(self, tag=None):
        '''
        Get a Gtk.TextTag style

        :param tag: the tag of the style to get
        '''
        if not tag:
            tag = self.default_style
        if tag in self._styles:
            return self._styles[tag]
        else:
            return None

    def change_style(self, tag, color=None, font=None):
        '''
        Change the font and color of a Gtk.TextTag style

        :param tag: text tag to indentify the style
        :param color: the font foreground color name ex. 'red'
        :param font: the font name ex. 'courier'
        '''
        style = self.get_style(tag)
        if style:
            if color:
                style.set_property("foreground", color)
            if font:
                style.set_property("font", font)

    def write(self, txt, style=None, newline=True):
        '''
        write a line of text to the textview and scoll to end

        :param txt: Text to write to textview
        :param style: text tag to indentify the style to use
        :param newline: if True, then add newline to the text it not there already
        '''
        if not txt:
            return
        if newline and txt[ -1] != '\n':
            txt += '\n'
        start, end = self.buffer.get_bounds()
        style = self.get_style(style)
        if style:
            self.buffer.insert_with_tags(end, txt, style)
        else:
            self.buffer.insert(end, txt)
        self.scroll_to_iter(self.buffer.get_end_iter(), 0.0, True, 0.0, 0.0)
        doGtkEvents()

    def clear(self):
        '''
        clear the textview
        '''
        self.buffer.set_text('')


    def goTop(self):
        '''
        Set the cursor to the start of the text view
        '''
        self.scroll_to_iter(self.buffer.get_start_iter(), 0.0, False, 0.0, 0.0)


class PackageInfoView(TextViewBase):
    '''
    TextView handler for showing package information
    '''

    def __init__(self, window=None, url_handler=None,  font_size=9):
        '''
        Setup the textview

        :param textview: the Gtk.TextView widget to use
        :param font_size: default text size
        '''
        TextViewBase.__init__(self, window, url_handler)

        # description style
        tag = "description"
        style = Gtk.TextTag()
        style.set_property("foreground", "midnight blue")
        style.set_property("family", "Monospace")
        style.set_property("size_points", font_size)
        self.add_style(tag, style)
        self.default_style = tag

        # filelist style
        tag = "filelist"
        style = Gtk.TextTag()
        style.set_property("foreground", "DarkOrchid4")
        style.set_property("family", "Monospace")
        style.set_property("size_points", font_size)
        self.add_style(tag, style)

        # changelog style
        tag = "changelog"
        style = Gtk.TextTag()
        style.set_property("foreground", "midnight blue")
        style.set_property("family", "Monospace")
        style.set_property("size_points", font_size)
        self.add_style(tag, style)

        # changelog style
        tag = "changelog-header"
        style = Gtk.TextTag()
        style.set_property("foreground", "dark red")
        style.set_property("family", "Monospace")
        style.set_property("size_points", font_size)
        self.add_style(tag, style)


class PackageInfoWidget(Gtk.Box):
    __gsignals__ = { 'info-changed': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_STRING,))
                    }

    def __init__(self, window, url_handler):
        Gtk.Box.__init__(self)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        # PKGINFO_FILTERS = ['desc', 'updinfo', 'changelog', 'files', 'deps']
        rb = self._get_radio_button('dialog-information-symbolic', "desc")
        vbox.add(rb)
        vbox.add(self._get_radio_button('software-update-available-symbolic', "updinfo", rb))
        vbox.add(self._get_radio_button('bookmark-new-symbolic', "changelog", rb))
        vbox.add(self._get_radio_button('drive-multidisk-symbolic', "files", rb))
        vbox.add(self._get_radio_button('insert-object-symbolic', "deps", rb))
        vbox.set_margin_right(5)
        self.pack_start(vbox, False, False, 0)
        sw = Gtk.ScrolledWindow()
        self.view = PackageInfoView( window, url_handler)
        sw.add(self.view)
        self.pack_start(sw, True, True, 0)


    def _get_radio_button(self,icon_name,name, group=None):
        if group:
            wid = Gtk.RadioButton.new_from_widget(group)
        else:
            wid = Gtk.RadioButton()
        icon = Gio.ThemedIcon(name=icon_name)
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
        wid.set_image(image)
        wid.connect('toggled', self._on_filter_changed, name)
        wid.set_property("draw-indicator", False) # we only want an image, not the black dot indicator
        return wid

    def _on_filter_changed(self, button, data):
        '''
        Radio Button changed handler
        Change the info in the view to match the selection
Gtk.Image()
        :param button:
        :param data:
        '''
        if button.get_active():
            logger.debug("pkginfo: %s selected" % data)
            self.emit("info-changed",data)

class PackageInfo(PackageInfoWidget):
    '''
    class for handling the Package Information view
    '''

    def __init__(self, window, base):
        PackageInfoWidget.__init__(self, window, url_handler=self._url_handler)
        self.window = window
        self.base = base
        self.current_package = None
        self.active_filter = PKGINFO_FILTERS[0]
        self.connect('info-changed',self.on_filter_changed)
        self.update()

    def on_filter_changed(self, widget, data):
        self.active_filter = data
        self.update()

    def set_package(self, pkg):
        '''
        Set current active package to show information about in the
        Package Info view.

        :param pkg: package to set as active package
        '''
        self.current_package = pkg
        self.update()

    def update(self):
        '''
        update the information in the Package info view
        '''
        self.view.clear()
        self.view.write("\n")
        if self.current_package:
            if self.active_filter == 'desc':
                self._show_description()
            elif self.active_filter == 'updinfo':
                self._show_updateinfo()

            elif self.active_filter == 'changelog':
                self._show_changelog()

            elif self.active_filter == 'files':
                self._show_filelist()

            elif self.active_filter == 'deps':
                self._show_requirements()
            else:
                print("Package info not found : ", self.active_filter)
        self.view.goTop()

    def _is_url(self, url):
        urls = re.findall('^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url)
        if urls:
            return True
        else:
            return False

    def _url_handler(self, url):
        print('Url activated : ' + url)
        if self._is_url(url):  # just to be sure and prevent shell injection
            rc = call("xdg-open %s" % url, shell=True)
            if rc != 0:  # failover to gtk.show_uri, if xdg-open fails or is not installed
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            self.frontend.warning("%s is not an url" % url)

    def _show_description(self):
        tags = self.current_package.pkgtags
        if tags:
            self.view.write(_("Tags : %s\n ") % ", ".join(tags),"changelog-header")
        url = self.current_package.URL
        self.view.write(_("Project URL : "), "changelog-header", newline=False)
        self.view.add_url(url, url, newline=True)
        self.view.write('\n')

        desc = self.current_package.description
        self.view.write(desc)
        self.base.set_working(False)

    def _show_updateinfo(self):
        # FIXME: updateinfo is not supported in dnf yet
        self.view.write("Updateinfo not supported in dnf yet")
        return
        self.base.set_working(True)
        updinfo = self.current_package.updateinfo
        for info in updinfo:
            self._write_update_info(info)
        if len(updinfo) == 0:
            self.view.write("No Update information is available")
        self.base.set_working(False)

    def _write_update_info(self, upd_info):
        head = ""
        head += ("%14s " % _("Release")) + ": %(release)s\n"
        head += ("%14s " % _("Type")) + ": %(type)s\n"
        head += ("%14s " % _("Status")) + ": %(status)s\n"
        head += ("%14s " % _("Issued")) + ": %(issued)s\n"
        head = head % upd_info

        if upd_info['updated'] and upd_info['updated'] != upd_info['issued']:
            head += "    Updated : %s" % upd_info['updated']

        self.view.write(head)
        head = ""

        # Add our bugzilla references
        if upd_info['references']:
            bzs = [ r for r in upd_info['references'] if r and r['type'] == 'bugzilla']
            if len(bzs):
                header = "Bugzilla"
                for bz in bzs:
                    if 'title' in bz and bz['title']:
                        bug_msg = ' - %s' % bz['title']
                    else:
                        bug_msg = ''
                    self.view.write("%14s : " % header, newline=False)
                    self.view.add_url(bz['id'], BUGZILLA_URL + bz['id'])
                    self.view.write(bug_msg)
                    header = " "

        # Add our CVE references
        if upd_info['references']:
            cves = [ r for r in upd_info['references'] if r and r['type'] == 'cve']
            if len(cves):
                cvelist = ""
                header = "CVE"
                for cve in cves:
                    cvelist += "%14s : %s\n" % (header, cve['id'])
                    header = " "
                head += cvelist[:-1].rstrip() + '\n\n'

        if upd_info['description'] is not None:
            desc = upd_info['description']
            head += "\n%14s : %s\n" % (_("Description"), format_block(desc, 17))

        head += "\n"
        self.view.write(head)

    def _show_changelog(self):
        # FIXME: Changekog is not supported in dnf yet
        self.view.write("Changelog not supported in dnf yet")
        return
        self.base.set_working(True)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.view.write("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver), "changelog-header")
                for line in msg.split('\n'):
                    self.view.write("%s" % line, "changelog")
                self.view.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        self.base.set_working(False)


    def _show_filelist(self):
        # FIXME: filelist is not supported in dnf yet
        self.view.write("filelist not supported in dnfdaemon yet")
        return
        self.base.set_working(True)
        filelist = self.current_package.filelist
        for fname in sorted(filelist):
            self.view.write(fname)
        self.base.set_working(False)

    def _show_requirements(self):
        self.view.write("Requirements for " + str(self.current_package))



class Preferences:

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("preferences")
        self.dialog.set_transient_for(base)
        self._settings = ['autostart', 'clean_unused', 'newest_only','autocheck_updates','hide_on_close']
        self.repo_view = RepoView()
        widget = self.base.ui.get_object('repo_sw')
        widget.add(self.repo_view)
        self.repos = []

    def run(self):
        self.get_settings()
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        need_reset = False
        if rc == 1:
            need_reset = self.set_settings()
        return need_reset

    def get_settings(self):
        # set settings states
        for option in self._settings:
            logger.debug("%s : %s " % (option,getattr(CONFIG.conf,option) ))
            widget = self.base.ui.get_object('pref_'+option)
            widget.set_active(getattr(CONFIG.conf,option))
        # autocheck update on/off handler
        widget = self.base.ui.get_object('pref_autocheck_updates')
        widget.connect('notify::active', self.on_autocheck_updates)
        # set current colors
        for name in ['color_install','color_update' ,'color_normal','color_obsolete','color_downgrade']:
            rgba = get_color(getattr(CONFIG.conf,name))
            widget = self.base.ui.get_object(name)
            widget.set_rgba(rgba)
        # Set update checker values
        for name in ['update_startup_delay', 'update_interval','refresh_interval']:
            widget = self.base.ui.get_object('pref_'+name)
            widget.set_value(getattr(CONFIG.conf,name))
        self.on_autocheck_updates()
        # get the repositories
        self.repos = self.base.backend.get_repositories()
        self.repo_view.populate(self.repos)

    def on_autocheck_updates(self, *args):
        widget = self.base.ui.get_object('pref_autocheck_updates')
        state = widget.get_active()
        if state:
            self.base.ui.get_object('pref_update_startup_delay').set_sensitive(True)
            self.base.ui.get_object('pref_update_interval').set_sensitive(True)
            self.base.ui.get_object('label_update_delay').set_sensitive(True)
            self.base.ui.get_object('label_update_interval').set_sensitive(True)
        else:
            self.base.ui.get_object('pref_update_startup_delay').set_sensitive(False)
            self.base.ui.get_object('pref_update_interval').set_sensitive(False)
            self.base.ui.get_object('label_update_delay').set_sensitive(False)
            self.base.ui.get_object('label_update_interval').set_sensitive(False)

    def set_settings(self):
        changed = False
        need_reset = False
        # handle options
        for option in self._settings:
            widget = self.base.ui.get_object('pref_'+option)
            state = widget.get_active()
            if state != getattr(CONFIG.conf, option): # changed ??
                setattr(CONFIG.conf, option, state)
                changed = True
                self.handle_setting(option, state)
        # handle colors
        for name in ['color_install','color_update' ,'color_normal','color_obsolete','color_downgrade']:
            widget = self.base.ui.get_object(name)
            rgba = widget.get_rgba()
            color =  color_to_hex(rgba)
            if color != getattr(CONFIG.conf, name): # changed ??
                setattr(CONFIG.conf, name, color)
                changed = True
        # handle update checker values
        for name in ['update_startup_delay', 'update_interval','refresh_interval']:
            widget = self.base.ui.get_object('pref_'+name)
            value = widget.get_value_as_int()
            if value != getattr(CONFIG.conf, name): # changed ??
                setattr(CONFIG.conf, name, value)
                changed = True
        # handle repos
        repo_before = CONFIG.session.enabled_repos
        repo_now = self.repo_view.get_selected()
        if repo_now != repo_before:                     # repo selection changed
            CONFIG.session.enabled_repos = repo_now     # set the new selection
            need_reset = True                           # we need to reset the gui
        if changed:
            CONFIG.write()
        return need_reset

    def handle_setting(self, option, state):
        if option == 'autostart':
            if state: # create an autostart .desktop for current user
                shutil.copy(MISC_DIR+"/yumex-dnf-autostart.desktop", os.environ['HOME'] +"/.config/autostart/yumex-dnf.desktop")
            else: # remove the autostart file
                os.unlink(os.environ['HOME'] +"/.config/autostart/yumex-dnf.desktop")


class TransactionResult:

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("transaction-results")
        self.dialog.set_transient_for(base)
        self.view = self.base.ui.get_object("result_view")
        self.store = self.setup_view(self.view)

    def run(self):
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        return rc == 1

    def clear(self):
        self.store.clear()

    def _fullname(self, pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s" % (n, e, v, r, a)
        else:
            return "%s-%s-%s.%s" % (n, v, r, a)


    def setup_view(self, view):
        '''
        Setup the TreeView
        @param view: the TreeView widget
        '''
        model = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_STRING,
                              GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        view.set_model(model)
        self.create_text_column(_("Name"), view, 0, size=250)
        self.create_text_column(_("Arch"), view, 1)
        self.create_text_column(_("Ver"), view, 2)
        self.create_text_column(_("Repository"), view, 3, size=100)
        self.create_text_column(_("Size"), view, 4)
        return model

    def create_text_column(self, hdr, view, colno, size=None):
        '''
        Create at TreeViewColumn
        @param hdr: column header text
        @param view: the TreeView widget
        @param colno: the TreeStore column containing data for the column
        @param min_width: the min column view (optional)
        '''
        cell = Gtk.CellRendererText()  # Size Column
        column = Gtk.TreeViewColumn(hdr, cell, markup=colno)
        column.set_resizable(True)
        if size:
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_fixed_width(size)
        view.append_column(column)


    def populate(self, pkglist, dnl_size):
        '''
        Populate the TreeView with data
        @param pkglist: list containing view data
        '''
        model = self.store
        self.store.clear()
        total_size = 0
        for sub, lvl1 in pkglist:
            label = "<b>%s</b>" % TRANSACTION_RESULT_TYPES[sub]
            level1 = model.append(None, [label, "", "", "", ""])
            for id, size, replaces in lvl1:
                (n, e, v, r, a, repo_id) = str(id).split(',')
                level2 = model.append(level1, [n, a, "%s.%s" % (v, r), repo_id, format_number(size)])
                if sub in ['install', 'update', 'install-deps', 'update-deps', 'obsoletes']:  # packages there need to be downloaded
                    total_size += size
                for r in replaces:
                    fn = self._fullname(r)
                    model.append(level2, [ fn, "", "", "", ""])
        self.base.ui.get_object("result_size").set_text(format_number(total_size))
        self.view.expand_all()


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
        if self.state == 'normal': # deselect all
            self._last_selected = self.get_selected()
            self.select_all()
            self.state = 'deselected'
        elif self.state == 'deselected': # select all
            self.state = 'selected'
            self.select_all()
        elif self.state == 'selected': # select previous selected
            self.state = 'normal'
            self.select_by_keys(self._last_selected)
            self._last_selected = []



    def setup_view(self):
        """ Create models and columns for the Repo TextView  """
        store = Gtk.ListStore('gboolean', str, str, 'gboolean')
        self.set_model(store)
        # Setup Selection Column
        col = self.create_selection_column_num(0, tooltip = _("Click here to switch between\n none/all/default selected"))
        col.set_clickable(True)
        col.connect('clicked', self.on_section_header_clicked)

        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()    # gpgcheck
        cell2.set_property('stock-id', Gtk.STOCK_DIALOG_AUTHENTICATION)
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

    def new_pixbuf(self, column, cell, model, iterator,data):
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
        while iterator != None:
            repoid = self.store.get_value(iterator, 1)
            if repoid in keys:
                self.store.set_value(iterator, 0, True)
            else:
                self.store.set_value(iterator, 0, False)
            iterator = self.store.iter_next(iterator)


class Group:
    """ Object to represent a dnf group/category """

    def __init__(self,grpid, grp_name, grp_desc, inst, is_category = False ):
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
        '''
        a property function to get string data from a object in the TreeStore based on
        an attributes key
        @param column:
        @param cell:
        @param model:
        @param iterator:
        @param prop: attribute key
        '''
        obj = model.get_value(iterator, 0)
        if obj:
            cell.set_property('text', getattr(obj, prop))

    def set_checkbox(self, column, cell, model, iterator, data=None):
        '''

        @param column:
        @param cell:
        @param model:
        @param iterator:
        '''
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
        if action: # Group is in the queue, remove it from the queue
            self.queue.remove_group(obj, action)
        else:
            if obj.installed: # Group is installed add it to queue for removal
                self.queue.add_group(obj, 'r') # Add for remove
            else: # Group is not installed, add it to queue for installation
                self.queue.add_group(obj, 'i') # Add for install
        self.queueView.refresh()

    def on_cursor_changed(self, widget):
        '''
        a new group is selected in group view
        '''
        if widget.get_selection():
            (model, iterator) = widget.get_selection().get_selected()
            if model != None and iterator != None:
                obj = self.model.get_value(iterator, 0)
                if not obj.category and obj.id != self.selected_group:
                    self.selected_group = obj.id
                    self.emit('group-changed', obj.id) # send the group-changed signal

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
            cell.set_property('visible',True)
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
        else: # Try to get the parent icon
            parent = model.iter_parent(iterator)
            if parent:
                cat_id =model[parent][0].id # get the parent cat_id
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

class AboutDialog(Gtk.AboutDialog):

    def __init__(self):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'Yum Extender (dnf)'
        self.props.version = VERSION
        self.props.authors = ['Tim Lauridsen <timlau@fedoraproject.org>']
        self.props.license_type = Gtk.License.GPL_2_0
        self.props.copyright = '(C) 2014 Tim Lauridsen'
        self.props.website = 'https://github.com/timlau/yumex-dnf'
        self.props.logo_icon_name = 'yumex-dnf'


def ask_for_gpg_import(window, values):
    (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
    pkg_name = pkg_id.split(',')[0]
    msg = (_( ' Do you want to import this GPG Key\n'
              ' Needed to verify the %s package\n\n'
              ' key        : 0x%s:\n'
              ' Userid     : "%s"\n'
              ' From       : %s') %
                (pkg_name, hexkeyid, userid,
                keyurl.replace("file://","")))

    dialog = Gtk.MessageDialog(window, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, msg)
    rc = dialog.run()
    dialog.destroy()
    return rc == Gtk.ResponseType.YES


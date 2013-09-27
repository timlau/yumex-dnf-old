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
from gi.repository import GObject, GLib
from datetime import date
from subprocess import call
import cairo
import random
import logging

from .misc import _, P_, CONFIG, format_number, doGtkEvents, format_block, TimeFunction  # @UnusedImport
from .const import *  # @UnusedWildImport
import shutil


logger = logging.getLogger('yumex.widget')        

#
# based on SearchEntry by Sebastian Heinlein <glatzor@ubuntu.com>
# http://bazaar.launchpad.net/~ubuntuone-control-tower/software-center/trunk/view/head:/softwarecenter/ui/gtk3/widgets/searchentry.py
#
class SearchEntry(Gtk.Entry):

    __gsignals__ = {'search-changed': (GObject.SignalFlags.RUN_FIRST,
                                      None,
                                      (GObject.TYPE_STRING,))}

    def __init__(self, width=50, timeout=600):
        """
        Creates an enhanced IconEntry that triggers a timeout when typing
        """
        Gtk.Entry.__init__(self)
        self.set_width_chars(width)
        self._timeout = timeout  # timeout for sending changed signal


        self._handler_changed = self.connect_after("changed",
                                                   self._on_changed)

        self.connect("icon-press", self._on_icon_pressed)

        self.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY,
            'edit-find-symbolic')
        self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)

        self._timeout_id = 0

    def _on_icon_pressed(self, widget, icon, mouse_button):
        """
        Emit the search-changed signal without any time out when the clear
        button was clicked
        """
        if icon == Gtk.EntryIconPosition.SECONDARY:
            # clear with no signal and emit manually to avoid the
            # search-timeout
            self.clear_with_no_signal()
            self.grab_focus()
            self.emit("search-changed", "")

        elif icon == Gtk.EntryIconPosition.PRIMARY:
            self.select_region(0, -1)
            self.grab_focus()

    def clear(self):
        self.set_text("")
        self._check_clear_icon()

    def set_text(self, text, cursor_to_end=True):
        Gtk.Entry.set_text(self, text)
        if cursor_to_end:
            self.emit("move-cursor", Gtk.MovementStep.BUFFER_ENDS, 1, False)

    def set_text_with_no_signal(self, text):
        """Clear and do not send a term-changed signal"""
        self.handler_block(self._handler_changed)
        self.set_text(text)
        self.emit("move-cursor", Gtk.MovementStep.BUFFER_ENDS, 1, False)
        self.handler_unblock(self._handler_changed)

    def clear_with_no_signal(self):
        """Clear and do not send a term-changed signal"""
        self.handler_block(self._handler_changed)
        self.clear()
        self.handler_unblock(self._handler_changed)

    def _emit_search_changed(self):
        text = self.get_text()
        # add to the undo stack once a term changes
        self.emit("search-changed", text)

    def _on_changed(self, widget):
        """
        Call the actual search method after a small timeout to allow the user
        to enter a longer search term
        """
        self._check_clear_icon()
        if self._timeout_id > 0:
            GLib.source_remove(self._timeout_id)
        self._timeout_id = GLib.timeout_add(self._timeout,
                                               self._emit_search_changed)

    def _check_clear_icon(self):
        """
        Show the clear icon whenever the field is not empty
        """
        if self.get_text() != "":
            self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY,
                Gtk.STOCK_CLEAR)
            # reverse the icon if we are in an rtl environment
            if self.get_direction() == Gtk.TextDirection.RTL:
                pb = self.get_icon_pixbuf(
                    Gtk.EntryIconPosition.SECONDARY).flip(True)
                self.set_icon_from_pixbuf(Gtk.EntryIconPosition.SECONDARY, pb)
        else:
            self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)

class InfoProgressBar:

    def __init__(self, ui):
        self.ui = ui
        self.infobar = ui.get_object("infobar")
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")
        self.actions = ui.get_object("infobar_actions")

    def show_progress(self, state):
        if state:
            self.show_label()
        else:
            self.hide()

    def hide(self):
        self.label.hide()
        self.sublabel.hide()
        self.progress.hide()
        self.actions.hide()
        self.infobar.hide()
        self.progress.set_text("")
        self.progress.set_show_text (False)

    def show_label(self):
        self.label.show()
        self.label.set_text("")

    def show_sublabel(self):
        self.sublabel.show()
        self.sublabel.set_text("")

    def show_buttons(self):
        self.actions.show()

    def message(self, msg):
        self.infobar.show()
        self.show_label()
        self.label.set_markup("<b>%s</b>" % msg)

    def message_sub(self, msg):
        self.infobar.show()
        self.show_sublabel()
        self.sublabel.set_text(msg)

    def info(self, msg):
        self.message(msg)

    def info_sub(self, msg):
        self.message_sub(msg)

    def set_progress(self, frac, label=None):
        if label:
            self.progress.set_text(label)
            self.progress.set_show_text (True)
        if frac >= 0.0 and frac <= 1.0:
            self.infobar.show()
            self.progress.show()
            self.progress.set_fraction(frac)




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

    def create_text_column(self, hdr, prop, size, sortcol=None):
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
        column1.set_fixed_width(20)
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



    def create_selection_column_num(self, num, data_func=None):
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


class PackageView(SelectionView):

    def __init__(self, qview, base):
        self.logger = logging.getLogger('yumex.PackageView')
        SelectionView.__init__(self)
        self.store = self._setup_model()
        self._click_header_active = False
        self._click_header_state = ""
        self.queue = qview.queue
        self.queueView = qview
        self.base = base


    def _setup_model(self):
        '''
        Setup the model and view
        '''
        store = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.set_model(store)
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
        self.create_text_column(_("Arch."), 'arch' , size=60)
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


    def on_section_header_clicked(self, *args):
        if self._click_header_active:
            if self._click_header_state == "":
                self.selectAll()
                self._click_header_state = "selected"
            elif self._click_header_state == "selected":
                self.deselectAll()
                self._click_header_state = ""

    def set_header_click(self, state):
        self._click_header_active = state
        self._click_header_state = ""

    def selectAll(self):
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

    def deselectAll(self):
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
        self.groups['i'] = []
        self.groups['r'] = []
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
        self.groups['i'] = []
        self.groups['r'] = []
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

    def addGroup(self, grp, action):
        '''

        @param grp:
        @param action:
        '''
        pkg_list = self.groups[action]
        if not grp in pkg_list:
            pkg_list.append(grp)
        self.groups[action] = pkg_list

    def removeGroup(self, grp, action):
        '''

        @param grp:
        @param action:
        '''
        pkg_list = self.groups[action]
        if grp in pkg_list:
            pkg_list.remove(grp)
        self.groups[action] = pkg_list

    def remove_all_groups(self):
        '''
        remove all groups from queue
        '''
        for action in ('i', 'r'):
            for grp in self.groups[action]:
                self.removeGroup(grp, action)


    def hasGroup(self, grp):
        '''

        @param grp:
        '''
        for action in ['i', 'r']:
            if grp in self.groups[action]:
                return action
        return None


class QueueView(Gtk.TreeView):

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.store = self._setup_model()
        self.queue = PackageQueue()


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

    def deleteSelected(self):
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
        self.refresh()


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

    def __init__(self, font_size=9, window=None, url_handler=None):
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


class PackageInfo(PackageInfoView):
    '''
    class for handling the Package Information view
    '''

    def __init__(self, window, base):
        PackageInfoView.__init__(self, window=window, url_handler=self._url_handler)
        # self.set_margin_top(10)
        self.window = window
        self.base = base
        self.current_package = None
        self.active_filter = PKGINFO_FILTERS[0]
        self.setup_filters()
        self.update()


    def setup_filters(self):
        '''
        Setup the package info radio buttons toggle handlers
        '''
        for flt in PKGINFO_FILTERS:
            widget = self.base.ui.get_object("info_%s" % flt)
            widget.connect('toggled', self.on_filter_changed, flt)

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
        self.clear()
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
        self.goTop()

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
            self.write(_("Tags : %s\n ") % ", ".join(tags),"changelog-header")
        desc = self.current_package.description
        self.write(desc)

    def _show_updateinfo(self):
        self.base.set_working(True)
        updinfo = self.current_package.updateinfo
        for info in updinfo:
            self._write_update_info(info)
        if len(updinfo) == 0:
            self.write("No Update information is available")
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

        self.write(head)
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
                    self.write("%14s : " % header, newline=False)
                    self.add_url(bz['id'], BUGZILLA_URL + bz['id'])
                    self.write(bug_msg)
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
        self.write(head)

    def _show_changelog(self):
        self.base.set_working(True)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.write("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver), "changelog-header")
                for line in msg.split('\n'):
                    self.write("%s" % line, "changelog")
                self.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        self.base.set_working(False)


    def _show_filelist(self):
        self.base.set_working(True)
        filelist = self.current_package.filelist
        for fname in sorted(filelist):
            self.write(fname)
        self.base.set_working(False)

    def _show_requirements(self):
        self.write("Requirements for " + str(self.current_package))

    def on_filter_changed(self, button, data):
        '''
        Radio Button changed handler
        Change the info in the view to match the selection

        :param button:
        :param data:
        '''
        if button.get_active():
            # self.base.infobar.info("pkginfo: %s selected" % data)
            self.active_filter = data
            self.update()


class Preferences:

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("preferences")
        self.dialog.set_transient_for(base)
        self._settings = ['autostart','skip_broken', 'clean_unused', 'newest_only']
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
        # set current colors 
        for name in ['color_install','color_update' ,'color_normal','color_obsolete','color_downgrade']:
            rgba = Gdk.RGBA()
            rgba.parse(getattr(CONFIG.conf,name))
            widget = self.base.ui.get_object(name)
            widget.set_rgba(rgba)
        # get the repositories 
        self.repos = self.base.backend.get_repositories()
        self.repo_view.populate(self.repos)

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
            color =  rgba.to_string()
            if color != getattr(CONFIG.conf, name): # changed ??
                setattr(CONFIG.conf, name, color)
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
                shutil.copy(MISC_DIR+"/yumex-nextgen-autostart.desktop", os.environ['HOME'] +"/.config/autostart/yumex-nextgen.desktop")
            else: # remove the autostart file
                os.unlink(os.environ['HOME'] +"/.config/autostart/yumex-nextgen.desktop")
        

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
        self.create_text_column(_("Repository"), view, 3)
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
                    model.append(level2, [ r, "", "", "", ""])
        self.base.ui.get_object("result_size").set_text(format_number(total_size))
        self.view.expand_all()


class StatusIcon:
    rel_font_size = 0.7
    is_working = 0
    need_input = False
    update_count = -2

    popup_menu = None
    quit_menu = None
    search_updates_menu = None


    def __init__(self):
        self.image_checking = ICON_TRAY_WORKING
        self.image_no_update = ICON_TRAY_NO_UPDATES
        self.image_updates = ICON_TRAY_UPDATES
        self.image_error = ICON_TRAY_ERROR
        self.image_info = ICON_TRAY_INFO

        self.statusicon = Gtk.StatusIcon()
        self.init_popup_menu()
        self.update_tray_icon()

    def init_popup_menu(self):
        menu = Gtk.Menu()
        self.popup_menu = menu

        quit = Gtk.MenuItem(_("Quit"))
        self.quit_menu = quit

        search_updates = Gtk.MenuItem(_("Search for Updates"))
        self.search_updates_menu = search_updates

        menu.append(search_updates)
        menu.append(quit)
        menu.show_all()
        self.statusicon.connect("popup-menu", self.on_popup)


    def set_popup_menu_sensitivity(self, sensitive):
        self.quit_menu.set_sensitive(sensitive)
        self.search_updates_menu.set_sensitive(sensitive)

    def on_popup(self, icon, button, time):
        # self.popup_menu.popup(None, None, Gtk.StatusIcon.position_menu, button,time, self.statusicon)
        def pos(menu, icon):
            return (Gtk.StatusIcon.position_menu(menu, icon))

        self.popup_menu.popup(None, None, pos, self.statusicon, button, time)
        # self.popup_menu.popup(None, None, None, Gtk.StatusIcon.position_menu, button, time)

    def get_status_icon(self):
        return self.statusicon

    def update_tray_icon(self):
        if self.need_input:
            self.statusicon.set_tooltip_text("Yum Extender: Need user input")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_info)
            self.set_popup_menu_sensitivity(False)
        elif self.is_working > 0:
            self.statusicon.set_tooltip_text("Yum Extender: Working")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_checking)
            self.set_popup_menu_sensitivity(False)
        else:
            self.set_popup_menu_sensitivity(True)
            update_count = self.update_count
            if update_count == -2:
                self.statusicon.set_tooltip_text(_("Yum Extender"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
            elif update_count == -1:
                self.statusicon.set_tooltip_text(_("Yum Extender: Error"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_error)
            elif update_count == 0:
                self.statusicon.set_tooltip_text(_("Yum Extender: No Updates"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
            else:
                self.statusicon.set_tooltip_text(_("Yum Extender: %s Updates available")
                        % update_count)
                pixbuf = self.get_pixbuf_with_text(self.image_updates,
                        str(update_count), self.rel_font_size)
        self.statusicon.set_from_pixbuf(pixbuf)
        Gtk.main_iteration()

    # png_file must be a squared image
    def get_pixbuf_with_text(self, png_file, text, relative_font_size):
        img = cairo.ImageSurface.create_from_png(png_file)
        size = img.get_height()
        surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context (surface)
        ctx.set_source_surface(img, 0, 0)
        ctx.paint()

        font_size = size * relative_font_size
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        # resize font size until text fits ...
        while font_size > 1.0:
            ctx.set_font_size(int(font_size))
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                    cairo.FONT_WEIGHT_BOLD)
            [bearing_x, bearing_y, font_x, font_y, ax, ay] = ctx.text_extents(text)
            if font_x < size: break
            font_size = font_size * 0.9
        ctx.move_to(int(size - font_x) / 2 - bearing_x , int(size - font_y) / 2 - bearing_y)
        ctx.show_text(text)
        ctx.stroke()

        # this is ugly but the easiest way to get a pixbuf from a cairo image
        # surface...
        r = int(random.random() * 999999)
        file_name = "/tmp/notifier_tmp_" + str(r) + ".png"
        surface.write_to_png(file_name)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_name)
        os.remove(file_name)
        return pixbuf


    def set_update_count(self, update_count):
        '''
        set the available update count
        @param update_count: =0: no updates, -1: error occured
        '''
        self.update_count = update_count
        self.update_tray_icon()

    def set_is_working(self, is_working=True):
        '''
        set working: show a busy tray icon if is_working is True
        '''
        if is_working:
            self.is_working = self.is_working + 1
        else:
            self.is_working = self.is_working - 1
        self.update_tray_icon()

    def need_user_input(self, need_input=True):
        """ call this when a user interacton/input is needed """

        self.need_input = need_input
        self.update_tray_icon()

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

    def on_toggled(self, widget, path):
        """ Repo select/unselect handler """
        iterator = self.store.get_iter(path)
        state = self.store.get_value(iterator, 0)
        self.store.set_value(iterator, 0, not state)

    def on_section_header_clicked(self, widget):
        """  Selection column header clicked"""
        if self.state == 'normal': # deselect all
            self._last_selected = self.get_selected()
            self.deselect_all()
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
        col = self.create_selection_column_num(0)
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

    def deselect_all(self):
        '''

        '''
        iterator = self.store.get_iter_first()
        while iterator != None:
            self.store.set_value(iterator, 0, False)
            iterator = self.store.iter_next(iterator)

    def select_all(self):
        '''

        '''
        iterator = self.store.get_iter_first()
        while iterator != None:
            self.store.set_value(iterator, 0, True)
            iterator = self.store.iter_next(iterator)


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

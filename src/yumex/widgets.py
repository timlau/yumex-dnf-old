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
from gi.repository import Gdk
from gi.repository import GObject, GLib
from datetime import date
from subprocess import call

from .const import _
from .const import *
from .misc import doGtkEvents, format_block, TimeFunction


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
        self._timeout = timeout # timeout for sending changed signal


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

    def hide(self):
        self.label.hide()
        self.sublabel.hide()
        self.progress.hide()
        self.actions.hide()
        self.infobar.hide()

    def show_label(self):
        self.label.show()
        self.label.set_text("")

    def show_sublabel(self):
        self.sublabel.show()
        self.sublabel.set_text("")

    def show_progress(self):
        self.progress.show()
        self.progress.set_fraction(0.0)

    def show_buttons(self):
        self.actions.show()

    def message(self, msg):
        self.infobar.show()
        self.show_label()
        self.label.set_text(msg)



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
        cell = Gtk.CellRendererText()    # Size Column
        column = Gtk.TreeViewColumn(hdr, cell)
        column.set_resizable(True)
        column.set_cell_data_func(cell, self.get_data_text, prop)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(size)
        if sortcol:
            column.set_sort_column_id(sortcol)
            #column.set_sort_indicator(True)
            #column.set_sort_order(Gtk.Gtk.SortType.ASCENDING)
        else:
            column.set_sort_column_id(-1)
        self.append_column(column)
        return column

    def create_selection_colunm(self, attr, click_handler=None):
        '''
        Create an selection column, there get data via property function and a key attr
        @param attr: key attr for property funtion
        '''
        # Setup a selection column using a object attribute
        cell1 = Gtk.CellRendererToggle()    # Selection
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


    def create_selection_column_num(self, num, data_func=None):
        '''
        Create an selection column, there get data an TreeStore Column
        @param num: TreeStore column to get data from
        '''
        # Setup a selection column using a column num

        column = Gtk.TreeViewColumn(None, None)
        # Selection checkbox
        selection = Gtk.CellRendererToggle()    # Selection
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
        selection = Gtk.CellRendererToggle()    # Selection
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
            cell.set_property('foreground', obj.color)

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

    def __init__(self,qview, base):
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
        self.create_selection_colunm('selected', click_handler=self.on_section_header_clicked)

        # Setup resent column
        cell2 = Gtk.CellRendererPixbuf()    # new
        cell2.set_property('stock-id', Gtk.STOCK_ADD)
        column2 = Gtk.TreeViewColumn("", cell2)
        column2.set_cell_data_func(cell2, self.new_pixbuf)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column2.set_fixed_width(20)
        column2.set_sort_column_id(-1)
        self.append_column(column2)
        column2.set_clickable(True)

        self.create_text_column(_("Package"), 'name' , size=200)
        self.create_text_column(_("Ver."), 'version', size=120)
        self.create_text_column(_("Arch."), 'arch' , size=60)
        self.create_text_column(_("Summary"), 'summary', size=400)
        self.create_text_column(_("Repo."), 'repository' , size=90)
        self.create_text_column(_("Size."), 'sizeM' , size=90)
        self.set_search_column(1)
        self.set_enable_search(True)
        #store.set_sort_column_id(1, Gtk.Gtk.SortType.ASCENDING)
        self.set_reorderable(False)
        return store

    def on_section_header_clicked(self,*args):
        if self._click_header_active:
            if self._click_header_state == "":
                self.selectAll()
                self._click_header_state = "selected"
            elif self._click_header_state == "selected":
                self.deselectAll()
                self._click_header_state = ""

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
        i=0
        for po in sorted(pkgs,key=lambda po: po.name ):
            i += 1
            if i % 500: # Handle Gtk event, so gui dont freeze
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
        if obj.queued == 'do': # all-ready queued
            related_po = obj.downgrade_po
            if obj.is_installed(): # is obj the installed pkg ?
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
            pkgs = obj.downgrades # get the installed po
            print("downgrades",pkgs)
            if pkgs:
                # downgrade the po
                pkg = pkgs[0]
                if pkg.action == 'do' or self.queue.has_pkg_with_name_arch(pkg): # Installed pkg is all-ready downgraded by another package
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
                pkg.action = "r" # reset action type of installed package
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


class History(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_direction(Gtk.Orientation.HORIZONTAL)
        self._setup_views()

    def _setup_views(self):
        self.selection = Gtk.TreeView()
        self.add(self.selection)
        self.selection_model = self._setup_selection()
        self.content = Gtk.TreeView()
        self.pack_start(self.content,True,True,0)
        self.content_model = self._setup_content()

    def _setup_selection(self):
        model = Gtk.TreeStore(str, int)
        self.selection.set_model(model)
        cell1 = Gtk.CellRendererText()
        column1 = Gtk.TreeViewColumn(_("History (Date/Time)"), cell1, markup=0)
        column1.set_resizable(False)
        column1.set_fixed_width(200)
        self.selection.append_column(column1)
        model.set_sort_column_id(0, Gtk.SortType.DESCENDING)
        return model

    def _setup_content(self):
        model = Gtk.TreeStore(str)
        self.content.set_model(model)
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("History Packages"), cell, markup=0)
        column.set_resizable(True)
        #column.set_fixed_width(600)
        self.content.append_column(column)
        #model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        return model

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
        self.default_style = None # the default style (text tag)
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
            #print("button press : ", url)
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
        w,x,y,mask = window.get_pointer()
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
        self.scroll_to_iter(self.buffer.get_end_iter(), 0.0, True, 0.0,0.0)
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
        #self.set_margin_top(10)
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
            widget = self.base.builder.get_object("info_%s" % flt)
            widget.connect('toggled',self.on_filter_changed, flt)

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

    def _is_url(self,url):
        urls = re.findall('^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url)
        if urls:
            return True
        else:
            return False

    def _url_handler(self, url):
        print('Url activated : ' + url)
        if self._is_url(url): # just to be sure and prevent shell injection
            rc = call("xdg-open %s"%url, shell=True)
            if rc != 0: # failover to gtk.show_uri, if xdg-open fails or is not installed
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            self.frontend.warning("%s is not an url" % url)

    def _show_description(self):
        desc = self.current_package.description
        self.write(desc)

    def _show_updateinfo(self):
        self.base.set_spinner(True)
        updinfo = self.current_package.updateinfo
        for info in updinfo:
            self._write_update_info(info)
        if len(updinfo) == 0:
            self.write("No Update information is available")
        self.base.set_spinner(False)

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
                buglist = ""
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
            head += "\n%14s : %s\n" % (_("Description"), format_block(desc,17))

        head += "\n"
        self.write(head)

    def _show_changelog(self):
        self.base.set_spinner(True)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.write("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver), "changelog-header")
                for line in msg.split('\n'):
                    self.write("%s" % line, "changelog")
                self.write('\n')
                if i == 5: # only show the last 5 entries
                    break
        self.base.set_spinner(False)


    def _show_filelist(self):
        self.base.set_spinner(True)
        filelist = self.current_package.filelist
        for fname in sorted(filelist):
            self.write(fname)
        self.base.set_spinner(False)

    def _show_requirements(self):
        self.write("Requirements for "+str(self.current_package))

    def on_filter_changed(self, button, data):
        '''
        Radio Button changed handler
        Change the info in the view to match the selection

        :param button:
        :param data:
        '''
        if button.get_active():
            #self.base.infobar.info("pkginfo: %s selected" % data)
            self.active_filter = data
            self.update()
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
from gi.repository import Gio
from .widgets import SearchEntry, PackageView, QueueView, History, PackageInfo
from .misc import show_information
from .const import *
from .yum_backend import YumReadOnlyBackend

class YumexWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.Window.__init__(self, title="Yum Extender", application=app)
        self.set_default_size(1024, 600)
        self.app = app
        # init vars
        self.last_search = None
        self.current_filter = None

        # setup the GtkBuilder from file
        self.builder = Gtk.Builder()
        # get the file (if it is there)
        try:
            self.builder.add_from_file(DATA_DIR +"/yumex.ui")
        except:
            print ("file not found")
            sys.exit()

        # setup the package manager backend
        #self.backend = TestBackend()
        self.backend = YumReadOnlyBackend(self)
        self.backend.setup()


        # setup the main gui
        grid = Gtk.Grid()
        self.add(grid)
        grid.show()
        grid.attach(self.builder.get_object("main"), 0, 0, 1, 1)

        # build the package filter widget
        button = self.builder.get_object("tool_packages")
        button.set_menu(self.builder.get_object("pkg_filter_menu"))

        # Connect menu radio buttons to handler
        for widget_name in ['updates','installed','available']:
            rb = self.builder.get_object("pkg_"+widget_name)
            rb.connect('toggled', self.on_pkg_filter, widget_name)

        # Setup search entry
        search_widget = self.builder.get_object("seach_entry")
        search_entry = SearchEntry()
        search_entry.connect("search-changed", self.on_search_changed)
        search_widget.add(search_entry)
        search_widget.show_all()

        # setup the package/queue/history views
        self.build_content()

        # setup info view
        info = self.builder.get_object("info_sw")
        self.info = PackageInfo(self,self)
        info.add(self.info)
        self.info.show_all()

        # setup actions
        self._create_action("pref", self.on_pref)
        self._create_action("packages", self.on_packages)
        self._create_action("history", self.on_history)
        self._create_action("queue", self.on_queue)
        self._create_action("apply_changes", self.on_apply_changes)
#         self._create_action("info_desc", self.on_info)
#         self._create_action("info_changelog", self.on_info)
#         self._create_action("info_files", self.on_info)
#         self._create_action("info_deps", self.on_info)

        # show window
        self.show_now()
        
        # setup default selections
        self.builder.get_object("pkg_updates").set_active(True)
        self.builder.get_object("info_desc").set_active(True)


    def build_content(self):
        '''
        Create a tab-less notebook to handle the package, history and queue views
        '''
        self.content = self.builder.get_object("content")
        self.queue_view = QueueView()
        self.package_view = PackageView(self.queue_view)
        select = self.package_view.get_selection()
        select.connect("changed", self.on_pkg_view_selection_changed)
        self.history_view = History()
        sw = self.builder.get_object("package_sw")
        sw.add(self.package_view)
        sw = self.builder.get_object("queue_sw")
        sw.add(self.queue_view)
        sw = self.builder.get_object("history_sw")
        sw.add(self.history_view)
        self.content.set_show_tabs(False)
        self.content.show_all()

    def set_content_page(self, page):
        '''
        Set the visible content notebook page
        :param page: active page (0 = packages, 1 = queue, 2 = history)
        '''
        self.content.set_current_page(page)

    def _create_action(self, name, callback, para = None):
        '''
        Created a Gio.SimpleAction on a given name and connect it to a given callback
        handler
        '''
        action = Gio.SimpleAction.new(name, para)
        action.connect("activate", callback)
        self.add_action(action)
        
    def exception_handler(self,e):
        msg = str(e)
        err, msg = self._parse_error(msg)
        print(err,msg)
        if err == "YumLockedError":
            msg="Yum  is locked by another process \n\nYum Extender will exit"
        show_information(self, msg)
        sys.exit(1)
 
    def _parse_error(self, value):
        '''
        parse values from a DBus releated exception
        '''
        res = DBUS_ERR_RE.match(str(value))
        if res:
            err = res.groups()[0]
            err = err.split('.')[-1]
            msg = res.groups()[1]
            return err, msg
        return "",""
       
    def on_pkg_view_selection_changed(self, selection):
        '''
        package selected in the view 
        :param widget: the view widget
        '''
        model, iterator = selection.get_selected()
        if model != None and iterator != None:
            pkg = model.get_value(iterator, 0)
            print("package selected", pkg)
            if pkg:
                self.info.set_package(pkg)

    def on_packages(self, action, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        self._show_info(True)

        widget = self.builder.get_object("hidden")
        widget.set_active(True)
        self._set_pkg_relief()
        self.set_content_page(0)

    def _set_pkg_relief(self, relief = Gtk.ReliefStyle.HALF):
        '''
        Set the button relief on the package button, so it is visible
        that it is selected or not
        '''
        widget = self.builder.get_object("tool_packages")
        button = widget.get_children()[0].get_children()[0]
        button.set_relief(relief)

    def _show_info(self, state):
        '''
        Show/Hide the package info box
        '''
        box = self.builder.get_object("info_box")
        box.set_visible(state)
        if state:
            desc = self.builder.get_object("info_desc")
            desc.set_active(True)

#
# Callback handlers
#

    def on_pkg_filter(self, widget, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        if widget.get_active():
            self.on_packages(None,None)
            print(data)
            if data in ["installed","available","updates"]:
                self.current_filter = (widget, data)
                pkgs = self.backend.get_packages(data)
                self.package_view.populate(pkgs)


    def on_search_changed(self, widget, data):
        '''
        Search callback handler
        '''
        print("Search for : [%s]" % data)
        if len(data) >= 3 and data != self.last_search: # only search for word larger than 3 chars
            self.last_search = data
            if self.current_filter:
                widget, flt = self.current_filter
                widget.set_active(False)
            pkgs = self.backend.get_packages_by_name(data+"*",True)
            self.package_view.populate(pkgs)
        elif data == "": # revert to the current selected filter
            if self.current_filter:
                widget, flt = self.current_filter
                self.on_pkg_filter(widget,flt)


    def on_history(self, action, parameter):
        '''
        History button callback handler
        '''
        widget = self.builder.get_object("tool_history")
        if widget.get_active():
            self._show_info(False)
            self.set_content_page(2)
            self._set_pkg_relief(Gtk.ReliefStyle.NONE)

    def on_queue(self, action, parameter):
        '''
        Queue button callback handler
        '''
        widget = self.builder.get_object("tool_queue")
        if widget.get_active():
            self._show_info(False)
            self.set_content_page(1)
            self._set_pkg_relief(Gtk.ReliefStyle.NONE)

    def on_info(self, action, parameter):
        '''
        Package info radiobuttons callback handler
        '''
        widget = self.builder.get_object(action.get_name())
        if widget.get_active():
            print("You clicked \"info\".",action.get_name())
            self.info.clear()
            self.info.write(action.get_name())


    def on_apply_changes(self, action, parameter):
        '''
        Apply Changes button callback handler
        '''
        print("You clicked \"Apply Changes\".",action.get_name())

    def on_pref(self, action, parameter):
        '''
        Preferences button callback handler
        '''
        print("You clicked \"Pref\".")

class YumexApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        self.win = YumexWindow(self)
        # show the window - with show() not show_all() because that would show also
        # the leave_fullscreen button
        self.win.show()
        self.win.connect('delete_event', self.on_quit)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Setup actions
        self._create_action("quit", self.on_quit)

    def _create_action(self, name, callback, para = None):
        action = Gio.SimpleAction.new(name, para)
        action.connect("activate", callback)
        self.add_action(action)

    def on_quit(self, action=None, parameter=None):
        self.quit()
        
    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)
        print("Exit Application")
        if self.win.backend:
            self.win.backend.quit()
    



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
from gi.repository import Gio
from .widgets import SearchEntry, PackageView, QueueView, PackageInfo, InfoProgressBar, HistoryView, TransactionResult
from .misc import show_information, doGtkEvents, _, P_, CONFIG, ExceptionHandler  # lint:ok
from .const import * # @UnusedWildImport
from .yum_backend import YumReadOnlyBackend, YumRootBackend

class YumexWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.Window.__init__(self, title="Yum Extender", application=app)
        self.set_default_size(1024, 700)
        self.app = app
        # init vars
        self.last_search = None
        self.current_filter = None
        self._root_backend = None
        self._root_locked = False
        self.search_type = ""

        # setup the GtkBuilder from file
        self.ui = Gtk.Builder()
        # get the file (if it is there)
        try:
            self.ui.add_from_file(DATA_DIR +"/yumex.ui")
        except:
            show_information(self, "GtkBuilder ui file not found : "+DATA_DIR +"/yumex.ui")
            sys.exit()

        # setup the package manager backend
        #self.backend = TestBackend()
        self.backend = YumReadOnlyBackend(self)
        self.backend.setup()

        # setup the main gui
        grid = Gtk.Grid()
        self.add(grid)
        grid.show()
        grid.attach(self.ui.get_object("main"), 0, 0, 1, 1)

        # build the package filter widget
        button = self.ui.get_object("tool_packages")
        button.set_menu(self.ui.get_object("pkg_filter_menu"))

        # Connect menu radio buttons to handler
        for widget_name in ['updates','installed','available']:
            rb = self.ui.get_object("pkg_"+widget_name)
            rb.connect('toggled', self.on_pkg_filter, widget_name)

        # build the search_conf widget
        button = self.ui.get_object("search_conf")
        button.set_menu(self.ui.get_object("search_menu"))
        # Connect menu radio buttons to handler
        for widget_name in ['keyword','prefix','summary',"desc"]:
            rb = self.ui.get_object("search_"+widget_name)
            rb.connect('toggled', self.on_search_config, widget_name)


        # Setup search entry
        search_widget = self.ui.get_object("seach_entry")
        self.search_entry = SearchEntry()
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_widget.add(self.search_entry)
        search_widget.show_all()

        # setup the package/queue/history views
        self.build_content()

        # setup info view
        info = self.ui.get_object("info_sw")
        self.info = PackageInfo(self,self)
        info.add(self.info)
        self.info.show_all()

        # spinner
        self.spinner = self.ui.get_object("progress_spinner")
        self.spinner.set_from_file(PIX_DIR+"/spinner.gif")
        self.spinner.hide()

        # infobar
        self.infobar = InfoProgressBar(self.ui)
        self.infobar.hide()

        # transaction result dialog
        self.transaction_result = TransactionResult(self)

        # setup actions
        self._create_action("pref", self.on_pref)
        self._create_action("packages", self.on_packages)
        self._create_action("history", self.on_history)
        self._create_action("queue", self.on_queue)
        self._create_action("apply_changes", self.on_apply_changes)
        self._create_action("search_config", self.on_search_config)

        # show window
        self.show_now()

        # setup default selections
        self.ui.get_object("pkg_updates").set_active(True)
        self.ui.get_object("info_desc").set_active(True)
        self.ui.get_object("search_keyword").set_active(True)


    @ExceptionHandler
    def get_root_backend(self):
        """
        Get the current root backend
        if it is not setup yet, the create it
        if it is not locked, then lock it
        """
        if self._root_backend == None:
            self._root_backend = YumRootBackend(self)
            self._root_backend.setup()
            self._root_locked = True
            print("Start the yum root daemon")
        elif self._root_locked == False:
            self._root_backend.Lock()
            self._root_locked = True
            print("Lock the yum root daemon")
        return self._root_backend

    @ExceptionHandler
    def release_root_backend(self, quit=False):
        """
        Release the current root backend, if it is setup and locked
        """
        if self._root_backend == None:
            return
        if self._root_locked == True:
            print("Unlock the yum root daemon")
            self._root_backend.Unlock()
            self._root_locked = False
        if quit:
            print("Exit the yum root daemon")
            self._root_backend.Exit()

    def build_content(self):
        '''
        Create a tab-less notebook to handle the package, history and queue views
        '''
        self.content = self.ui.get_object("content")
        self.queue_view = QueueView()
        self.package_view = PackageView(self.queue_view, self)
        select = self.package_view.get_selection()
        select.connect("changed", self.on_pkg_view_selection_changed)
        sw = self.ui.get_object("package_sw")
        sw.add(self.package_view)
        sw = self.ui.get_object("queue_sw")
        sw.add(self.queue_view)
        # History
        sw = self.ui.get_object("history_sw")
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.history_view = HistoryView(self)
        hb.pack_start(self.history_view, False,False,0)
        hb.pack_start(self.history_view.pkg_view, True,True,0)
        sw.add(hb)
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
        print("EXCEPTION : ", msg)
        err, msg = self._parse_error(msg)
        print(err,msg)
        if err == "YumLockedError":
            msg="Yum  is locked by another process \n\nYum Extender will exit"
        show_information(self, msg)
        sys.exit(1)

    def set_spinner(self, state, insensitive=False):
        if state:
            self.spinner.show()
            self.busy_cursor(insensitive)
        else:
            self.spinner.hide()
            self.infobar.hide()
            self.normal_cursor()



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

    def busy_cursor(self, insensitive=False):
        ''' Set busy cursor in mainwin and make it insensitive if selected '''
        win = self.get_window()
        if win != None:
            win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
            if insensitive:
                for widget in ['top_box', 'content']:
                    self.ui.get_object(widget).set_sensitive(False)
        doGtkEvents()

    def normal_cursor(self):
        ''' Set Normal cursor in mainwin and make it sensitive '''
        win = self.get_window()
        if win != None:
            win.set_cursor(None)
            for widget in ['top_box', 'content']:
                self.ui.get_object(widget).set_sensitive(True)
        doGtkEvents()


    def on_pkg_view_selection_changed(self, selection):
        '''
        package selected in the view
        :param widget: the view widget
        '''
        model, iterator = selection.get_selected()
        if model != None and iterator != None:
            pkg = model.get_value(iterator, 0)
            if pkg:
                self.info.set_package(pkg)

    def on_packages(self, action, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        self._show_info(True)

        widget = self.ui.get_object("hidden")
        widget.set_active(True)
        self._set_pkg_relief()
        self.set_content_page(0)

    def _set_pkg_relief(self, relief = Gtk.ReliefStyle.HALF):
        '''
        Set the button relief on the package button, so it is visible
        that it is selected or not
        '''
        widget = self.ui.get_object("tool_packages")
        button = widget.get_children()[0].get_children()[0]
        button.set_relief(relief)

    def _show_info(self, state):
        '''
        Show/Hide the package info box
        '''
        box = self.ui.get_object("info_box")
        box.set_visible(state)
        if state:
            desc = self.ui.get_object("info_desc")
            desc.set_active(True)

#
# Callback handlers
#
    def on_search_config(self, widget, data):
        '''
        callback for search config
        :param widget:
        :param data:
        '''
        self.search_type = data
        self.last_search = None
        self.search_entry.clear_with_no_signal()

    def on_pkg_filter(self, widget, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        if widget.get_active():
            self.on_packages(None,None)
            if data in ["installed","available","updates"]:
                self.infobar.message(PACKAGE_LOAD_MSG[data])
                self.current_filter = (widget, data)
                self.set_spinner(True,True)
                pkgs = self.backend.get_packages(data)
                self.info.set_package(None)
                self.infobar.message(_("Adding packages to view"))
                self.package_view.populate(pkgs)
                self.set_spinner(False)
                self.infobar.hide()
                if data == 'updates':
                    self.package_view.set_header_click(True)
                else:
                    self.package_view.set_header_click(False)

    def on_search_changed(self, widget, data):
        '''
        Search callback handler
        '''
        if self.search_type == "keyword":
            flt = "*%s*"
            self._search_name(data, flt)
        elif self.search_type == "prefix":
            flt = "%s*"
            self._search_name(data, flt)
        elif self.search_type == "summary":
            fields = ['name','summary']
            self._search_keys(fields, data)
        elif self.search_type == "desc":
            fields = ['name','summary', 'description']
            self._search_keys(fields, data)


    def _search_name(self, data,  search_flt):
        if len(data) >= 3 and data != self.last_search: # only search for word larger than 3 chars
            self.last_search = data
            if self.current_filter:
                widget, flt = self.current_filter
                widget.set_active(False)
            self.set_spinner(True)
            pkgs = self.backend.get_packages_by_name(search_flt % data, True)
            self.on_packages(None,None) # switch to package view
            self.info.set_package(None)
            self.package_view.populate(pkgs)
            self.set_spinner(False)
        elif data == "": # revert to the current selected filter
            if self.current_filter:
                widget, flt = self.current_filter
                self.on_pkg_filter(widget,flt)

    def _search_keys(self, fields, data):
        if data != self.last_search:
            self.last_search = data
            if self.current_filter:
                widget, flt = self.current_filter
                widget.set_active(False)
            self.set_spinner(True)
            pkgs = self.backend.search(fields,data.split(' '), True, False)
            self.on_packages(None,None) # switch to package view
            self.info.set_package(None)
            self.package_view.populate(pkgs)
            self.set_spinner(False)
        elif data == "": # revert to the current selected filter
            if self.current_filter:
                widget, flt = self.current_filter
                self.on_pkg_filter(widget,flt)




    def on_history(self, action, parameter):
        '''
        History button callback handler
        '''
        widget = self.ui.get_object("tool_history")
        if widget.get_active():
            if not self.history_view.is_populated:
                result = self.get_root_backend().GetHistoryByDays(0,int(CONFIG.history_days))
                self.history_view.populate(result)
            self._show_info(False)
            self.set_content_page(2)
            self._set_pkg_relief(Gtk.ReliefStyle.NONE)
        else:
            self.release_root_backend()

    def on_queue(self, action, parameter):
        '''
        Queue button callback handler
        '''
        widget = self.ui.get_object("tool_queue")
        if widget.get_active():
            self._show_info(False)
            self.set_content_page(1)
            self._set_pkg_relief(Gtk.ReliefStyle.NONE)

    def on_info(self, action, parameter):
        '''
        Package info radiobuttons callback handler
        '''
        widget = self.ui.get_object(action.get_name())
        if widget.get_active():
            self.info.clear()
            self.info.write(action.get_name())


    def on_apply_changes(self, action, parameter):
        '''
        Apply Changes button callback handler
        '''
        self.process_actions()

    def on_pref(self, action, parameter):
        '''
        Preferences button callback handler
        '''
        show_information(self, "not implemented yet")

    def process_actions(self):
        '''
        Process the current action in the queue
        - setup the yum transaction
        - resolve dependencies
        - ask user for confirmation on result of depsolve
        - run the transaction
        '''
        self.set_spinner(True)
        self.get_root_backend().ClearTransaction()
        for action in QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    self.get_root_backend().AddTransaction(pkg.downgrade_po.pkg_id, QUEUE_PACKAGE_TYPES[action])
                else:
                    self.get_root_backend().AddTransaction(pkg.pkg_id, QUEUE_PACKAGE_TYPES[action])

        self.get_root_backend().GetTransaction()
        self.infobar.info(_('Resolving Dependencies'))
        rc, result = self.get_root_backend().BuildTransaction()
        self.infobar.info(_('Dependencies Resolved'))
        self.set_spinner(False)
        if rc == 2:
            self.transaction_result.populate(result, "")
            ok = self.transaction_result.run()
            if ok: # Ok pressed
                self.infobar.info(_('Running Transaction'))
                self.set_spinner(True)
                self.get_root_backend().RunTransaction()
                self.set_spinner(False)
                self.reset()
        elif rc == 0:
            show_information(self,_("No actions to process"))
        else:
            show_information(self, _("Errors in dependency resolution"), result)
        self.infobar.hide()
        self.release_root_backend()

    def reset(self):
        self.set_spinner(True)
        self.infobar.hide()
        self.release_root_backend()
        # clear the package queue
        self.queue_view.queue.clear()
        self.queue_view.refresh()
        self.backend.reload()
        # clear search entry
        self.search_entry.clear_with_no_signal()
        self.last_search = None
        self.set_spinner(False)
        widget = self.ui.get_object("pkg_updates")
        widget.set_active(True)
        self.on_pkg_filter(widget,"updates")




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
        if self.win.backend:
            self.win.backend.quit()
        self.win.release_root_backend(quit=True)




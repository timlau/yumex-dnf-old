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
from .widgets import SearchEntry, PackageView, QueueView, PackageInfo, InfoProgressBar, HistoryView, TransactionResult, \
                     StatusIcon, Preferences
from .misc import show_information, doGtkEvents, _, P_, CONFIG, ExceptionHandler  # lint:ok
from .const import *  # @UnusedWildImport
from .yum_backend import YumReadOnlyBackend, YumRootBackend
import argparse
import logging

class YumexWindow(Gtk.ApplicationWindow):
    '''
    Main application window class
    '''
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, title="Yum Extender", application=app)
        self.key_bindings = Gtk.AccelGroup()
        self.add_accel_group(self.key_bindings)
        self.logger = logging.getLogger('yumex.Window')
        self.set_default_size(1024, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.app = app
        icon = Gtk.IconTheme.get_default().load_icon('yumex-nextgen', 128, 0)
        self.set_icon(icon)
        self.connect('delete_event', self.on_delete_event)

        # init vars
        self.last_search = None
        self.current_filter = None
        self._root_backend = None
        self._root_locked = False
        self.search_type = ""
        self.active_archs = ['i686','noarch','x86_64']

        # setup the GtkBuilder from file
        self.ui = Gtk.Builder()
        # get the file (if it is there)
        try:
            self.ui.add_from_file(DATA_DIR + "/yumex.ui")
        except:
            show_information(self, "GtkBuilder ui file not found : " + DATA_DIR + "/yumex.ui")
            sys.exit()

        # setup the package manager backend
        # self.backend = TestBackend()
        self.backend = YumReadOnlyBackend(self)
        self.backend.setup()
        CONFIG.session.enabled_repos = self.backend.get_repo_ids("enabled") # get the default enabled repos

        # setup the main gui
        main = self.ui.get_object("main")
        self.add(main)
        main.show()
        
        # build the package filter widget
        button = self.ui.get_object("tool_packages")
        button.set_menu(self.ui.get_object("pkg_filter_menu"))

        # Connect menu radio buttons to handler
        for name in ['updates', 'installed', 'available']:
            rb = self.ui.get_object("pkg_" + name)
            rb.connect('toggled', self.on_pkg_filter, name)

        # build the option widget
        button = self.ui.get_object("tool_pref")
        button.set_menu(self.ui.get_object("options_menu"))
        # Connect menu radio buttons to handler
        for name in ['newest_only', 'skip_broken', 'clean_unused']:
            rb = self.ui.get_object("option_" + name)
            rb.set_active(getattr(CONFIG.session, name))
            rb.connect('toggled', self.on_options, name)

        # build the search_conf widget
        button = self.ui.get_object("search_conf")
        button.set_menu(self.ui.get_object("search_menu"))
        # Connect menu radio buttons to handler
        for name in ['keyword', 'prefix', 'summary', "desc"]:
            rb = self.ui.get_object("search_" + name)
            rb.connect('toggled', self.on_search_config, name)


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
        self.info = PackageInfo(self, self)
        info.add(self.info)
        self.info.show_all()

        # spinner
        self.spinner = self.ui.get_object("progress_spinner")
        self.spinner.set_from_file(PIX_DIR + "/spinner.gif")
        self.spinner.hide()

        # infobar
        self.infobar = InfoProgressBar(self.ui)
        self.infobar.hide()

        # transaction result dialog
        self.transaction_result = TransactionResult(self)
        
        # preferences dialog
        
        self.preferences = Preferences(self)

        # setup actions
        self._create_action("pref", self.on_pref)
        self._create_action("packages", self.on_packages)
        self._create_action("history", self.on_history)
        self._create_action("queue", self.on_queue)
        self._create_action("apply_changes", self.on_apply_changes)
        self._create_action("search_config", self.on_search_config)

        # Status Icon
        self.status_icon = StatusIcon()
        icon = self.status_icon.get_status_icon()
        icon.connect("activate", self.on_status_icon_clicked)
        self.status_icon.quit_menu.connect("activate", self.app.on_quit)
        self.status_icon.search_updates_menu.connect("activate", self.check_for_updates)
        # self.status_icon.search_updates_menu.connect("activate",   self.app.on_quit)
        
        # Key bindings
        widget = self.ui.get_object('tool_quit')
        self._add_key_binding(widget, '<ctrl>q')

        if not self.app.args.hidden:
            self.show_now()
            
        # get the arch filter
        self.arch_filter = self.backend.get_filter('arch')
        self.arch_filter.set_active(True)
        self.arch_filter.change(self.active_archs)

        # setup default selections
        self.ui.get_object("pkg_updates").set_active(True)
        self.ui.get_object("info_desc").set_active(True)
        self.ui.get_object("search_keyword").set_active(True)


    def on_delete_event(self, *args):
        '''
        windows delete event handler
        just hide, dont exit application
        '''
        self.hide()
        return True


    def on_status_icon_clicked(self, event):
        '''
        left click on status icon handler
        hide/show the window, based on current state
        '''
        if self.get_property('visible'):
            self.hide()
        else:
            self.show()

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
            self.logger.debug("Start the yum root daemon")
        elif self._root_locked == False:
            self._root_backend.Lock()
            if CONFIG.session.enabled_repos:
                self.logger.debug("root: Setting repos : %s" % CONFIG.session.enabled_repos)
                self._root_backend.SetEnabledRepos(CONFIG.session.enabled_repos)

            self._root_locked = True
            self.logger.debug("Lock the yum root daemon")
        return self._root_backend

    @ExceptionHandler
    def release_root_backend(self, quit=False):
        """
        Release the current root backend, if it is setup and locked
        """
        if self._root_backend == None:
            return
        if self._root_locked == True:
            self.logger.debug("Unlock the yum root daemon")
            self._root_backend.Unlock()
            self._root_locked = False
        if quit:
            self.logger.debug("Exit the yum root daemon")
            self._root_backend.Exit()

    def build_content(self):
        '''
        setup the main content notebook
        setup the package, history and queue views pages
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
        hb.pack_start(self.history_view, False, False, 0)
        hb.pack_start(self.history_view.pkg_view, True, True, 0)
        sw.add(hb)
        self.content.set_show_tabs(False)
        self.content.show_all()

    def set_content_page(self, page):
        '''
        Set the visible content notebook page
        :param page: active page (PAGE_PACKAGES, PAGE_QUEUE, PAGE_HISTORY)
        '''
        self.content.set_current_page(page)

    def _create_action(self, name, callback, para=None):
        '''
        create and action and connect it to a callback handler
        handles win.<name> actions defined in GtkBuilder ui file.
        '''
        action = Gio.SimpleAction.new(name, para)
        action.connect("activate", callback)
        self.add_action(action)

    def _add_key_binding(self, widget, accel, event='clicked'):
        '''
        Added key bindings to widget
        @param widget: widget
        @param accel: key binding to map (ex. <ctrl>1 )
        @param event: key event (default = clicked)
        '''
        keyval, mask = Gtk.accelerator_parse(accel)
        widget.add_accelerator(event, self.key_bindings, keyval, mask, 0)

    def exception_handler(self, e):
        '''
        Called if exception occours in methods with the @ExceptionHandler decorator
        '''
        msg = str(e)
        self.logger.error("EXCEPTION : %s " % msg)
        err, errmsg = self._parse_error(msg)
        self.logger.debug("err:  %s - msg: %s" % (err, errmsg))
        if err == "YumLockedError":
            errmsg = "Yum  is locked by another process \n\nYum Extender will exit"
        if errmsg == "":
            errmsg = msg
        show_information(self, errmsg)
        # try to exit the backends, ignore errors
        try:
            self.backend.Exit()
        except:
            pass
        try:
            self.release_root_backend(quit=True)
        except:
            pass
        sys.exit(1)

    def set_working(self, state, insensitive=False):
        '''
        Set the working state
        - show/hide the progress spinner
        - show busy/normal mousepointer
        - make gui insensitive/sensitive
        - set/unset the woring state in the status icon
        based on the state.
        '''
        if state:
            self.spinner.show()
            self.status_icon.set_is_working(True)
            self._set_busy_cursor(insensitive)
        else:
            self.spinner.hide()
            self.infobar.hide()
            self.status_icon.set_is_working(False)
            self._set_normal_cursor()



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
        return "", ""

    def check_for_updates(self, widget=None):
        '''
        check for updates handller for the status icon menu
        '''
        self.backend.reload()  # Reload backend
        widget = self.ui.get_object("pkg_updates")
        if widget.get_active():
            self.on_pkg_filter(widget, "updates")
        else:
            self.ui.get_object("pkg_updates").set_active(True)

    def _set_busy_cursor(self, insensitive=False):
        ''' Set busy cursor in mainwin and make it insensitive if selected '''
        win = self.get_window()
        if win != None:
            win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
            if insensitive:
                for widget in ['top_box', 'content']:
                    self.ui.get_object(widget).set_sensitive(False)
        doGtkEvents()

    def _set_normal_cursor(self):
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
        self.set_content_page(PAGE_PACKAGES)

    def _set_pkg_relief(self, relief=Gtk.ReliefStyle.HALF):
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
        if self.last_search:
            key = self.last_search
            self.last_search = None
            self.search_entry.clear_with_no_signal()
            self.search_entry.set_text(key)

    def on_pkg_filter(self, widget, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        if widget.get_active():
            self.on_packages(None, None)
            if data in ["installed", "available", "updates"]:
                self.infobar.message(PACKAGE_LOAD_MSG[data])
                self.current_filter = (widget, data)
                self.set_working(True, True)
                pkgs = self.backend.get_packages(data)
                if data == 'updates':
                    self.status_icon.set_update_count(len(pkgs))
                self.info.set_package(None)
                self.infobar.message(_("Adding packages to view"))
                self.package_view.populate(pkgs)
                self.set_working(False)
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
            fields = ['name', 'summary']
            self._search_keys(fields, data)
        elif self.search_type == "desc":
            fields = ['name', 'summary', 'description']
            self._search_keys(fields, data)


    def _search_name(self, data, search_flt):
        '''
        search package name for keyword with wildcards
        '''
        if len(data) >= 3 and data != self.last_search:  # only search for word larger than 3 chars
            self.last_search = data
            if self.current_filter:
                widget, flt = self.current_filter
                widget.set_active(False)
            self.set_working(True)
            newest_only = CONFIG.session.newest_only
            pkgs = self.backend.get_packages_by_name(search_flt % data, newest_only)
            self.on_packages(None, None)  # switch to package view
            self.info.set_package(None)
            self.package_view.populate(pkgs)
            self.set_working(False)
        elif data == "":  # revert to the current selected filter
            if self.current_filter:
                widget, flt = self.current_filter
                self.on_pkg_filter(widget, flt)

    def _search_keys(self, fields, data):
        '''
        search given package attributes for keywords
        '''
        if data != self.last_search:
            self.last_search = data
            if self.current_filter:
                widget, flt = self.current_filter
                widget.set_active(False)
            self.set_working(True)
            newest_only = CONFIG.session.newest_only
            pkgs = self.backend.search(fields, data.split(' '), True, newest_only, True)
            self.on_packages(None, None)  # switch to package view
            self.info.set_package(None)
            self.package_view.populate(pkgs)
            self.set_working(False)
        elif data == "":  # revert to the current selected filter
            if self.current_filter:
                widget, flt = self.current_filter
                self.on_pkg_filter(widget, flt)




    def on_history(self, action, parameter):
        '''
        History button callback handler
        '''
        widget = self.ui.get_object("tool_history")
        if widget.get_active():
            if not self.history_view.is_populated:
                result = self.get_root_backend().GetHistoryByDays(0, int(CONFIG.conf.history_days))
                self.history_view.populate(result)
            self._show_info(False)
            self.set_content_page(PAGE_HISTORY)
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
            self.set_content_page(PAGE_QUEUE)
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

    def on_options(self, widget, parameter):
        '''
        callback handler for options menu
        set the CONFIG parameter values based on the menu checkbox states
        '''
        state = widget.get_active()
        setattr(CONFIG.session, parameter,state )
        self.logger.debug("Option : %s = %s" % (parameter, getattr(CONFIG.session, parameter)))

    def on_pref(self, action, parameter):
        '''
        Preferences button callback handler
        '''
        
        need_reset = self.preferences.run()
        if need_reset:
            self.reset()

    @ExceptionHandler
    def process_actions(self):
        '''
        Process the current action in the queue
        - setup the yum transaction
        - resolve dependencies
        - ask user for confirmation on result of depsolve
        - run the transaction
        '''
        self.set_working(True, True)
        self.infobar.info(_('Preparing system for applying changes'))
        self.get_root_backend().ClearTransaction()
        for action in QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    self.logger.debug('adding : %s %s' % (action, pkg.downgrade_po.pkg_id))
                    txmbrs = self.get_root_backend().AddTransaction(pkg.downgrade_po.pkg_id, QUEUE_PACKAGE_TYPES[action])
                    self.logger.debug("%s: %s" % (action, txmbrs))
                else:
                    self.logger.debug('adding : %s %s' % (action, pkg.pkg_id))
                    txmbrs = self.get_root_backend().AddTransaction(pkg.pkg_id, QUEUE_PACKAGE_TYPES[action])
                    self.logger.debug("%s: %s" % (action, txmbrs))

        self.get_root_backend().GetTransaction()
        self.infobar.info(_('Searching for dependencies'))
        rc, result = self.get_root_backend().BuildTransaction()
        self.infobar.info(_('Dependencies resolved'))
        self.set_working(False)
        if rc == 2:
            self.transaction_result.populate(result, "")
            ok = self.transaction_result.run()
            if ok:  # Ok pressed
                self.infobar.info(_('Applying changes to the system'))
                self.set_working(True, True)
                self.get_root_backend().RunTransaction()
                self.set_working(False)
                self.reset()
        elif rc == 0:
            show_information(self, _("No actions to process"))
        else:
            show_information(self, _("Error(s) in search for dependencies"), result[0])
        self.infobar.hide()
        self.release_root_backend()

    @ExceptionHandler
    def reset(self):
        '''
        Reset the gui to inital state, used after at transaction is completted.
        '''
        self.set_working(True)
        self.infobar.hide()
        self.release_root_backend()
        # clear the package queue
        self.queue_view.queue.clear()
        self.queue_view.refresh()
        self.backend.reload()
        # clear search entry
        self.search_entry.clear_with_no_signal()
        self.last_search = None
        self.set_working(False)
        widget = self.ui.get_object("pkg_updates")
        widget.set_active(True)
        self.on_pkg_filter(widget, "updates")




class YumexApplication(Gtk.Application):
    '''
    Main application class
    '''
    def __init__(self):
        Gtk.Application.__init__(self,flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.args = None
        self.logger = logging.getLogger('yumex.Application')

    def do_activate(self):
        '''
        Gtk.Application activate handler
        '''
        self.win = YumexWindow(self)
        # show the window - with show() not show_all() because that would show also
        # the leave_fullscreen button
        self.win.connect('delete_event', self.on_quit)
        if self.args.hidden:
            self.win.hide()
        else:
            self.win.show()

    def do_startup(self):
        '''
        Gtk.Application startup handler
        '''
        Gtk.Application.do_startup(self)
        # Setup actions
        self._create_action("quit", self.on_quit)

    def _create_action(self, name, callback, para=None):
        '''
        create and action and connect it to a callback handler
        handles app.<name> actions defined in GtkBuilder ui file.
        '''
        action = Gio.SimpleAction.new(name, para)
        action.connect("activate", callback)
        self.add_action(action)

    def on_quit(self, action=None, parameter=None):
        '''
        quit handler
        '''
        self.quit() # quit the application

    def do_command_line(self, args):
        '''
        Gtk.Application command line handler
        called if Gio.ApplicationFlags.HANDLES_COMMAND_LINE is set.
        must call the self.do_activate() to get the application up and running.
        '''
        Gtk.Application.do_command_line(self, args)
        parser = argparse.ArgumentParser(prog='yumex')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument('--hidden', action='store_true')
        parser.add_argument("-I", "--install", type=str, metavar="PACKAGE", help="Install Package")
        self.args = parser.parse_args(args.get_arguments()[1:])
        if self.args.debug:
            self.doTextLoggerSetup(loglvl=logging.DEBUG)
            # setup log handler for yumdaemon API
            self.doTextLoggerSetup(logroot='yumdaemon', logfmt = "%(asctime)s: [%(name)s] - %(message)s",loglvl=logging.DEBUG)
        else:
            self.doTextLoggerSetup()
        self.logger.debug("cmdline : %s " % repr(self.args))
        self.do_activate()
        return 0

    def do_shutdown(self):
        '''
        Gtk.Application shutdown handler
        Do clean up before the application is closed.
        '''
        Gtk.Application.do_shutdown(self)
        if hasattr(self,"win"): # if windows object exist, unlock and exit backends
            if self.win.backend:
                self.win.backend.quit()
            self.win.release_root_backend(quit=True)

    def doTextLoggerSetup(self, logroot='yumex', logfmt='%(asctime)s: %(message)s', loglvl=logging.INFO):
        ''' Setup Python logging  '''
        logger = logging.getLogger(logroot)
        logger.setLevel(loglvl)
        formatter = logging.Formatter(logfmt, "%H:%M:%S")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.propagate = False
        logger.addHandler(handler)



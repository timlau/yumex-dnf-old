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
                     Preferences, GroupView, ArchMenu, ask_for_gpg_import
from .misc import show_information, doGtkEvents, _, P_, CONFIG, ExceptionHandler  # lint:ok
from .const import *  # @UnusedWildImport
from .yum_backend import YumReadOnlyBackend, YumRootBackend
from .status import StatusIcon
import argparse
import logging
from subprocess import call
import time

class BaseWindow(Gtk.ApplicationWindow):
    """ Common Yumex Base window """

    def __init__(self, app, status):
        Gtk.ApplicationWindow.__init__(self, title="Yum Extender - Powered by dnf", application=app)
        self.logger = logging.getLogger('yumex.Window')
        self.set_position(Gtk.WindowPosition.CENTER)
        self.app = app
        self.status = status
        icon = Gtk.IconTheme.get_default().load_icon('yumex-dnf', 128, 0)
        self.set_icon(icon)
        self.connect('delete_event', self.on_delete_event)

        self._root_backend = None
        self._root_locked = False
        self.is_working = False
        self.session_backend_refreshed = False
        self.system_backend_refreshed = False

        # setup GtkBuilder
        self.ui = Gtk.Builder()
        try:
            self.ui.add_from_file(DATA_DIR + "/yumex.ui")
        except:
            show_information(self, "GtkBuilder ui file not found : " + DATA_DIR + "/yumex.ui")
            sys.exit()

        # transaction result dialog
        self.transaction_result = TransactionResult(self)

    def set_working(self, state, insensitive=False):
        '''
        Set the working state

        subclass and extend in child class

        '''
        self.is_working = state


    @ExceptionHandler
    def get_root_backend(self):
        """
        Get the current root backend
        if it is not setup yet, the create it
        if it is not locked, then lock it
        """
        if self._root_backend == None:
            self._root_backend = YumRootBackend(self)
        if self._root_locked == False:
            locked, msg = self._root_backend.setup()
            if locked:
                self._root_locked = True
                self.logger.debug("Lock the yum root daemon")
                if not self.system_backend_refreshed:
                    self.logger.debug("Refresh system cache")
                    self.set_working(True, True)
                    self.infobar.info(_('Refreshing Repository Metadata'))
                    self._root_backend.ExpireCache()
                    self.set_working(False)
                    self.system_backend_refreshed = True
            else:
                self.logger.critical("can't get root backend lock")
                if msg == "not-authorized": # user canceled the polkit dialog
                    errmsg = _("Yum root backend was not authorized\n Yum Extender will exit")
                elif msg == "locked-by-other": # yum is locked by another process
                    errmsg = _("Yum  is locked by another process \n\nYum Extender will exit")
                show_information(self, errmsg)
                # close down and exit yum extender
                self.status.SetWorking(False) # reset working state
                self.status.SetYumexIsRunning(False)
                try:
                    self.backend.Exit()
                except:
                    pass
                sys.exit(1)
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

    def exception_handler(self, e):
        '''
        Called if exception occours in methods with the @ExceptionHandler decorator
        '''
        close = True
        msg = str(e)
        self.logger.error("EXCEPTION : %s " % msg)
        err, errmsg = self._parse_error(msg)
        self.logger.debug("err:  %s - msg: %s" % (err, errmsg))
        if err == "LockedError":
            errmsg = "DNF is locked by another process \n\nYum Extender will exit"
            close = False
        if errmsg == "":
            errmsg = msg
        show_information(self, errmsg)
        # try to exit the backends, ignore errors
        if close:
            try:
                self.release_root_backend(quit=True)
            except:
                pass
        self.status.SetWorking(False) # reset working state
        self.status.SetYumexIsRunning(False)
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
        return "", ""


class YumexInstallWindow(BaseWindow):
    '''
    Simple ui windows class for doing actions from the command line.
    '''
    def __init__(self, app, status):
        BaseWindow.__init__(self, app, status)
        self.set_default_size(600, 80)
        grid = Gtk.Grid()
        ib = self.ui.get_object("infobar")
        ib.reparent(grid)
        grid.attach(ib, 0, 0, 1, 1)
        self.add(grid)
        grid.show()
        self.infobar = InfoProgressBar(self.ui)
        self.infobar.show_all()
        info_spinner = self.ui.get_object("info_spinner")
        info_spinner.set_from_file(PIX_DIR + "/spinner-small.gif")
        self.system_backend_refreshed = True # dont refresh metadata


    def on_delete_event(self, *args):
        '''
        windows delete event handler
        '''
        if CONFIG.conf.hide_on_close or self.is_working:
            self.hide()
            return True
        else:
            self.app.on_quit()

    @ExceptionHandler
    def process_actions(self,action, package, always_yes):
        '''
        Process the pending actions from the command line

        :param action: action to perform (install/remove)
        :param package: package to work on
        :param always_yes: ask the user or default to yes/ok to all questions
        '''
        self.status.SetWorking(True)
        if action == 'install':
            self.infobar.info(_("Installing package : %s") % package)
            self.infobar.info_sub(package)
            txmbrs = self.get_root_backend().Install(package)
            self.logger.debug("txmbrs: %s" % str(txmbrs))
        elif action == "remove":
            self.infobar.info(_("Removing package : %s") % package)
            self.infobar.info_sub(package)
            txmbrs = self.get_root_backend().Remove(package)
            self.logger.debug("txmbrs: %s" % str(txmbrs))
        self.infobar.info(_('Searching for dependencies'))
        rc, result = self.get_root_backend().BuildTransaction()
        self.infobar.info(_('Dependencies resolved'))
        if rc:
            self.transaction_result.populate(result, "")
            if not always_yes:
                ok = self.transaction_result.run()
            else:
                ok = True
            if ok:  # Ok pressed
                self.infobar.info(_('Applying changes to the system'))
                self.get_root_backend().RunTransaction()
                self.release_root_backend()
                self.hide()
                if not always_yes:
                    show_information(self,_("Changes was successfully applied to the system"))
        #else:
            #if action == 'install':
                #show_information(self, _("the %s package can't be installed") % package)
            #elif action == 'remove':
                #show_information(self, _("the %s package can't be removed") % package)
        else:
            show_information(self, _("Error(s) in search for dependencies"), "\n".join(result))
        self.release_root_backend(quit=True)
        self.status.SetWorking(False)
        self.app.quit()

class YumexWindow(BaseWindow):
    '''
    Main application window class
    '''
    def __init__(self, app, status):
        BaseWindow.__init__(self, app, status)
        self.set_default_size(1024, 700)

        # init vars
        self.last_search = None
        self.current_filter = None
        self._root_backend = None
        self._root_locked = False
        self.search_type = ""
        self.last_search_pkgs = []
        self.current_filter_search = None
        self.active_archs = PLATFORM_ARCH
        self._grps = None   # Group and Category cache
        self.active_page = None # Active content page

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
        for name in ['newest_only', 'clean_unused']:
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
        self.setup_main_content()


        # spinner
        self.spinner = self.ui.get_object("progress_spinner")
        self.spinner.set_from_file(PIX_DIR + "/spinner.gif")
        self.info_spinner = self.ui.get_object("info_spinner")
        self.info_spinner.set_from_file(PIX_DIR + "/spinner-small.gif")
        self.spinner.hide()

        # infobar
        self.infobar = InfoProgressBar(self.ui)
        self.infobar.hide()

        # preferences dialog

        self.preferences = Preferences(self)

        # setup actions
        self._create_action("pref", self.on_pref)
        self._create_action("packages", self.on_packages)
        self._create_action("history", self.on_history)
        self._create_action("groups", self.on_groups)
        self._create_action("queue", self.on_queue)
        self._create_action("apply_changes", self.on_apply_changes)
        self._create_action("search_config", self.on_search_config)


        self.show_now()

        # Refresh the metadata cache for the readonly API
        if not self.session_backend_refreshed and not self.app.args.norefresh:
            self.logger.debug("Refresh session cache")
            self.set_working(True, True)
            self.infobar.info(_('Refreshing Repository Metadata'))
            self.backend.ExpireCache()
            self.set_working(False)
            self.session_backend_refreshed = True

        # get the arch filter
        self.arch_filter = self.backend.get_filter('arch')
        self.arch_filter.set_active(True)
        self.arch_filter.change(self.active_archs)

        # setup default selections
        self.ui.get_object("pkg_updates").set_active(True)
        self.ui.get_object("search_keyword").set_active(True)


    def on_delete_event(self, *args):
        '''
        windows delete event handler
        '''
        if CONFIG.conf.hide_on_close or self.is_working:
            self.hide()
            return True
        else:
            self.app.on_quit()


    def on_status_icon_clicked(self):
        '''
        left click on status icon handler
        hide/show the window, based on current state
        '''
        if self.get_property('visible'):
            self.hide()
        else:
            self.show()


    def setup_main_content(self):
        '''
        setup the main content notebook
        setup the package, history and queue views pages
        '''
        self.content = self.ui.get_object("content")
        # Package Page
        queue_menu = self.ui.get_object("queue_menu")
        self.queue_view = QueueView(queue_menu)
        arch_menu_widget = self.ui.get_object('arch_menu')
        self.arch_menu = ArchMenu(arch_menu_widget,self.active_archs)
        self.arch_menu.connect("arch-changed", self.on_arch_changed)
        self.package_view = PackageView(self.queue_view, self.arch_menu)
        self.package_view.connect("pkg_changed", self.on_pkg_view_selection_changed)
        sw = self.ui.get_object("package_sw")
        sw.add(self.package_view)
        # setup info view
        info = self.ui.get_object("info_box")
        self.info = PackageInfo(self, self)
        info.pack_start(self.info,True,True,0)
        self.info.show_all()
        # Queue Page
        sw = self.ui.get_object("queue_sw")
        sw.add(self.queue_view)
        # History Page
        sw = self.ui.get_object("history_sw")
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.history_view = HistoryView(self)
        hb.pack_start(self.history_view, False, False, 0)
        hb.pack_start(self.history_view.pkg_view, True, True, 0)
        sw.add(hb)
        #Groups
        sw = self.ui.get_object("groups_sw")
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.groups = GroupView(self.queue_view, self)
        self.groups.connect('group-changed', self.on_group_changed)
        #hb.pack_start(self.groups, True, True, 0)
        #sw.add(hb)
        sw.add(self.groups)
        sw = self.ui.get_object("group_pkg_sw")
        self.group_package_view = PackageView(self.queue_view, self.arch_menu, group_mode=True)
        #self.group_package_view.connect("arch-changed", self.on_arch_changed)
        self.group_package_view.connect("pkg_changed", self.on_group_pkg_view_selection_changed)
        sw.add(self.group_package_view)
        info = self.ui.get_object("group_pkg_info_sw")
        self.group_info = PackageInfo(self, self)
        info.add(self.group_info)
        self.info.show_all()
        self.content.set_show_tabs(False)
        self.content.show_all()


    def set_content_page(self, page):
        '''
        Set the visible content notebook page
        :param page: active page (PAGE_PACKAGES, PAGE_QUEUE, PAGE_HISTORY)
        '''
        self.active_page = page
        self.content.set_current_page(page)
        if page != PAGE_PACKAGES:
            self._set_pkg_relief(Gtk.ReliefStyle.NONE)
            self.search_entry.set_sensitive(False)
        else:
            self._set_pkg_relief()
            self.search_entry.set_sensitive(True)



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
        close = True
        msg = str(e)
        self.logger.error("EXCEPTION : %s " % msg)
        err, errmsg = self._parse_error(msg)
        self.logger.debug("err:  %s - msg: %s" % (err, errmsg))
        if err == "LockedError":
            errmsg = "dnf is locked by another process \n\nYum Extender will exit"
            close = False
        elif err == "AccessDeniedError":
            errmsg = "Root backend was not authorized and can't continue"
            close = True
        if errmsg == "":
            errmsg = msg
        show_information(self, errmsg)
        # try to exit the backends, ignore errors
        if close:
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
        self.is_working = state
        if state:
            self.spinner.show()
            self.status.SetWorking(True)
            self._set_busy_cursor(insensitive)
        else:
            self.spinner.hide()
            self.infobar.hide()
            self.status.SetWorking(False)
            self._set_normal_cursor()


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
                for widget in ["tool_quit","tool_pref","tool_history","tool_packages","tool_queue","tool_apply","search_conf","seach_entry",'content']:
                        self.ui.get_object(widget).set_sensitive(False)
        doGtkEvents()

    def _set_normal_cursor(self):
        ''' Set Normal cursor in mainwin and make it sensitive '''
        win = self.get_window()
        if win != None:
            win.set_cursor(None)
            for widget in ["tool_quit","tool_pref","tool_history","tool_packages","tool_queue","tool_apply","search_conf","seach_entry",'content']:
                self.ui.get_object(widget).set_sensitive(True)
        doGtkEvents()


    def on_pkg_view_selection_changed(self, widget, pkg):
        '''
        package selected in the view
        :param widget: the view widget
        '''
        self.info.set_package(pkg)

    def on_group_pkg_view_selection_changed(self, widget, pkg):
        '''
        package selected in the view
        :param widget: the view widget
        '''
        self.group_info.set_package(pkg)

    def on_packages(self, action, data):
        '''
        callback for switching package filter (updates, installed, available)
        :param widget:
        :param data:
        '''
        widget = self.ui.get_object("hidden")
        widget.set_active(True)
        self.set_content_page(PAGE_PACKAGES)

    def _set_pkg_relief(self, relief=Gtk.ReliefStyle.HALF):
        '''
        Set the button relief on the package button, so it is visible
        that it is selected or not
        '''
        widget = self.ui.get_object("tool_packages")
        button = widget.get_children()[0].get_children()[0]
        button.set_relief(relief)

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
        if self.search_type in ['keyword','prefix']:
            self.search_entry.set_auto_search(True)
        else:
            self.search_entry.set_auto_search(False)
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
                self.infobar.info(PACKAGE_LOAD_MSG[data])
                self.set_working(True, True)
                if self.last_search: # we are searching
                    self.current_filter_search = (widget, data)
                    pkgs = self.filter_search_pkgs(data)
                else: # normal package filter
                    self.current_filter = (widget, data)
                    pkgs = self.backend.get_packages(data)
                    if data == 'updates':
                        obs_pkgs = self.backend.get_packages('obsoletes')
                        pkgs.extend(obs_pkgs)
                        self.status.SetUpdateCount(len(pkgs))
                self.info.set_package(None)
                self.infobar.info(_("Adding packages to view"))
                self.package_view.populate(pkgs)
                self.set_working(False)
                self.infobar.hide()
                if data == 'updates':
                    self.package_view.set_header_click(True)
                else:
                    self.package_view.set_header_click(False)

    def on_arch_changed(self, widget, data):
        '''
        arch changes callback handler
        :param widget:
        :param data:
        '''
        self.active_archs = data.split(",")
        self.logger.debug("arch-changed : %s" % self.active_archs)
        if self.last_search:
            data = self.last_search
            self.last_search = None
            self.on_search_changed(self.search_entry, data)
        elif self.active_page == PAGE_PACKAGES and self.current_filter:
            widget, flt = self.current_filter
            self.on_pkg_filter(widget, flt)


    def on_search_changed(self, widget, data):
        '''
        Search callback handler
        '''
        if data == "":  # revert to the current selected filter
            self.last_search = None
            self.last_search_pkgs = []
            self.current_filter_search = None
            if self.current_filter:
                widget, flt = self.current_filter
                state = widget.get_active()
                if not state:
                    widget.set_active(True)
                else:
                    self.on_pkg_filter(widget, flt)
        else:
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

    def filter_search_pkgs(self, flt):
        '''
        return filtered search results (updates, install or all)
        :param flt:
        '''
        if flt == "updates": # get update only
            pkgs = [po for po in self.last_search_pkgs if po.action in ('u','o')]
        elif flt == "installed": # get installed only
            pkgs = [po for po in self.last_search_pkgs if po.is_installed()]
            return pkgs
        else: # get all
            return self.last_search_pkgs

    def _search_name(self, data, search_flt):
        '''
        search package name for keyword with wildcards
        '''
        if len(data) >= 3 and data != self.last_search:  # only search for word larger than 3 chars
            self.last_search = data
            self.set_working(True)
            newest_only = CONFIG.session.newest_only
            self.last_search_pkgs = self.backend.get_packages_by_name(search_flt % data, newest_only)
            self.logger.debug("Packages found : %d" % len(self.last_search_pkgs))
            self.info.set_package(None)
            self.set_working(False)
            if self.current_filter_search:
                widget, flt = self.current_filter_search
                self.on_pkg_filter(widget, flt)
            else:
                self._set_available_active()


    def _search_keys(self, fields, data):
        '''
        search given package attributes for keywords
        '''
        if data != self.last_search: # do the search
            self.last_search = data
            self.set_working(True, True)
            newest_only = CONFIG.session.newest_only
            self.last_search_pkgs = self.backend.search(fields, data.split(' '), True, newest_only, True)
            self.on_packages(None, None)  # switch to package view
            self.info.set_package(None)
            self.set_working(False)
            if self.current_filter_search:
                widget, flt = self.current_filter_search
                self.on_pkg_filter(widget, flt)
            else:
                self._set_available_active()


    def _set_available_active(self):
        '''
        Make the 'available' filter active, by selecting 'updates' and the back to 'available'
        '''
        widget = self.ui.get_object('pkg_updates')
        widget.set_active(True)
        widget = self.ui.get_object('pkg_available')
        widget.set_active(True)

    def on_groups(self, action, parameter):
        '''
        History button callback handler
        '''
        widget = self.ui.get_object("tool_groups")
        if widget.get_active():
            self.set_content_page(PAGE_GROUPS)
            if not self._grps:
                self.logger.debug("getting group and categories")
                self._grps = self.backend.get_groups()
                self.groups.populate(self._grps)

    def on_group_changed(self, widget, grp_id):
        '''
        Group changed callback handler
        called when a new group is selected and the group package view shall be updated
        with the packages in the group
        :param widget:
        :param grp_id: group id
        '''
        self.logger.debug('on_group_changed : %s ' % grp_id)
        self.set_working(True, True)
        pkgs = self.backend.get_group_packages(grp_id, 'all')
        self.group_package_view.populate(pkgs)
        self.set_working(False)

    def on_history(self, action, parameter):
        '''
        History button callback handler
        '''
        widget = self.ui.get_object("tool_history")
        if widget.get_active():
            if not self.history_view.is_populated:
                result = self.get_root_backend().GetHistoryByDays(0, CONFIG.conf.history_days)
                self.history_view.populate(result)
            self.set_content_page(PAGE_HISTORY)
        else:
            self.release_root_backend()

    def on_queue(self, action, parameter):
        '''
        Queue button callback handler
        '''
        widget = self.ui.get_object("tool_queue")
        if widget.get_active():
            self.set_content_page(PAGE_QUEUE)

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
        if self.queue_view.queue.total() == 0:
            show_information(self, _("No pending actions in queue"))
            return
        self.set_working(True, True)
        # switch to queue view
        self.set_content_page(PAGE_QUEUE)
        self.infobar.info(_('Preparing system for applying changes'))
        self.get_root_backend().ClearTransaction()
        errors = 0
        error_msgs = set()
        for action in QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    self.logger.debug('adding : %s %s' % (action, pkg.downgrade_po.pkg_id))
                    rc, trans = self.get_root_backend().AddTransaction(pkg.downgrade_po.pkg_id, QUEUE_PACKAGE_TYPES[action])
                    self.logger.debug("%s: %s" % (rc, trans))
                    if not rc:
                        errors += 1
                        error_msgs |= set(trans)
                else:
                    self.logger.debug('adding : %s %s' % (action, pkg.pkg_id))
                    rc, trans = self.get_root_backend().AddTransaction(pkg.pkg_id, QUEUE_PACKAGE_TYPES[action])
                    self.logger.debug("%s: %s" % (rc, trans))
                    if not rc:
                        errors += 1
                        error_msgs |= set(trans)

        if not errors:
            self.get_root_backend().GetTransaction()
            self.infobar.info(_('Searching for dependencies'))
            rc, result = self.get_root_backend().BuildTransaction()
            self.infobar.info(_('Dependencies resolved'))
            self.set_working(False)
            if rc:
                self.transaction_result.populate(result, "")
                ok = self.transaction_result.run()
                if ok:  # Ok pressed
                    self.infobar.info(_('Applying changes to the system'))
                    self.set_working(True, True)
                    rc = self.get_root_backend().RunTransaction()
                    while rc == 1: # This can happen more than once (more gpg keys to be imported)
                        values = self.get_root_backend()._gpg_confirm # get info about gpgkey to be comfirmed
                        (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
                        self.logger.debug("GPGKey : %s" % repr(values))
                        ok = ask_for_gpg_import(self, values)
                        if ok:
                            self.get_root_backend().ConfirmGPGImport(hexkeyid, True) # tell the backend that the gpg key is confirmed
                            rc = self.get_root_backend().RunTransaction()
                        else:
                            break
                    self.reset()
                    return
            else: # error in depsolve
                show_information(self, _("Error(s) in search for dependencies"), "\n".join(result))
        else: # error in population of the transaction
            show_information(self, _("Error(s) in search for dependencies"), "\n".join(error_msgs))
        self.reset_on_error()

    def reset_on_error(self):
        '''
        Reset gui on transaction issues
        '''
        self.set_working(True)
        self.infobar.hide()
        self.release_root_backend()
        self.set_content_page(PAGE_QUEUE)
        self.set_working(False)

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
        self.current_filter_search = None
        # reset groups
        self._grps = self.backend.get_groups()
        self.groups.populate(self._grps)
        self.group_package_view.populate([])
        self.set_working(False)
        self.set_content_page(PAGE_PACKAGES)
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
        self.status = None
        self.logger = logging.getLogger('yumex.Application')

    def do_activate(self):
        '''
        Gtk.Application activate handler
        '''
        self.logger.debug("do_activate")
        if self.args.install:
            self.install = YumexInstallWindow(self, self.status)
            self.install.show()
            self.install.process_actions("install",self.args.install, self.args.yes)
        elif self.args.remove:
            self.install = YumexInstallWindow(self, self.status)
            self.install.show()
            self.install.process_actions("remove",self.args.remove, self.args.yes)
        else:
            self.win = YumexWindow(self, self.status)
            self.win.connect('delete_event', self.on_quit)
            self.win.show()

    def do_startup(self):
        '''
        Gtk.Application startup handler
        '''
        self.logger.debug("do_startup")
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
        if action == None: # If we quit from the StatusIcon, then quit the status icon also
            self.keep_icon_running = False
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
        parser.add_argument('-y', '--yes', action='store_true', help="Answer yes/ok to all questions")
        parser.add_argument('--icononly', action='store_true', help="Start only the status icon")
        parser.add_argument('--norefresh', action='store_true', help="don't refresh dnf metadata cache'")
        parser.add_argument('--exit', action='store_true', help="tell session dbus services used by yumex to exit")
        parser.add_argument("-I", "--install", type=str, metavar="PACKAGE", help="Install Package")
        parser.add_argument("-R", "--remove", type=str, metavar="PACKAGE", help="Remove Package")
        self.args = parser.parse_args(args.get_arguments()[1:])
        if self.args.debug:
            self.doTextLoggerSetup(loglvl=logging.DEBUG)
            # setup log handler for yumdaemon API
            self.doTextLoggerSetup(logroot='yumdaemon', logfmt = "%(asctime)s: [%(name)s] - %(message)s",loglvl=logging.DEBUG)
        else:
            self.doTextLoggerSetup()
        self.logger.debug("cmdline : %s " % repr(self.args))
        if self.args.exit:
            call('/usr/bin/dbus-send --session --print-reply --dest="dk.yumex.StatusIcon" / dk.yumex.StatusIcon.Exit', shell=True)
            call('/usr/bin/dbus-send --session --print-reply --dest="org.baseurl.DnfSession" / org.baseurl.DnfSession.Exit',shell=True)
            call('sudo /usr/bin/dbus-send --system --print-reply --dest="org.baseurl.DnfSystem" / org.baseurl.DnfSystem.Exit',shell=True)
            sys.exit(0)
        # Start the StatusIcon dbus client
        self.status = StatusIcon(self)
        self.status.Start() # Show the icon
        if self.args.icononly: # Only start the icon and exit
            sys.exit(0)
        if self.status.SetYumexIsRunning(True): # Check if yumex is running already
            self.do_activate()
        else:
            show_information(None, "Yum Extender is already running")
            sys.exit(1)
        return 0

    def do_shutdown(self):
        '''
        Gtk.Application shutdown handler
        Do clean up before the application is closed.
        '''
        Gtk.Application.do_shutdown(self)
        if self.status:
            self.status.SetYumexIsRunning(False)
            if not CONFIG.conf.autostart and not CONFIG.conf.autocheck_updates:
                self.status.Exit()
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



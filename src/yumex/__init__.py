# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version..Win
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

from gi.repository import Gio, Gtk, Gdk

from yumex.misc import _, CONFIG

import argparse
import datetime
import logging
import os.path
import shutil
import subprocess
import sys

import yumex.const as const
import yumex.misc as misc
import yumex.dnf_backend
import yumex.gui.dialogs as dialogs
import yumex.gui.views as views
import yumex.gui.widgets as widgets


logger = logging.getLogger('yumex')


class BaseYumex:

    def __init__(self):
        self._root_backend = None
        self._root_locked = False
        self.is_working = False

    def set_working(self, state, insensitive=False):
        """Set the working state."""
        self.is_working = state

    def _check_cache_expired(self, cache_type):
        time_fmt = '%Y-%m-%d %H:%M'
        now = datetime.datetime.now()
        refresh_period = datetime.timedelta(hours=CONFIG.conf.refresh_interval)
        # check if cache management is disabled
        if refresh_period == 0:
            return False
        if cache_type == 'session':
            last_refresh = datetime.datetime.strptime(
                CONFIG.conf.session_refresh, time_fmt)
            period = now - last_refresh
            if period > refresh_period:
                return True
            else:
                return False
        elif cache_type == 'system':
            last_refresh = datetime.datetime.strptime(
                CONFIG.conf.system_refresh, time_fmt)
            period = now - last_refresh
            if period > refresh_period:
                return True
            else:
                return False

    def _set_cache_refreshed(self, cache_type):
        time_fmt = '%Y-%m-%d %H:%M'
        now = datetime.datetime.now()
        now_str = now.strftime(time_fmt)
        if cache_type == 'session':
            CONFIG.conf.session_refresh = now_str
            CONFIG.write()
        elif cache_type == 'system':
            CONFIG.conf.system_refresh = now_str
            CONFIG.write()

    @property
    def backend(self):
        return self.get_root_backend()

    @misc.ExceptionHandler
    def get_root_backend(self):
        """Get the current root backend.

        if it is not setup yet, the create it
        if it is not locked, then lock it
        """
        if self._root_backend is None:
            self._root_backend = yumex.dnf_backend.DnfRootBackend(self)
        if self._root_locked is False:
            logger.debug('Lock the DNF root daemon')
            locked, msg = self._root_backend.setup()
            if locked:
                self._root_locked = True
                if self._check_cache_expired('system'):
                    logger.debug('Refresh system cache')
                    self.set_working(True, True)
                    self.infobar.info(_('Refreshing Repository Metadata'))
                    rc = self._root_backend.ExpireCache()
                    self.set_working(False)
                    if rc:
                        self._set_cache_refreshed('system')
                    else:
                        dialogs.show_information(
                            self, _('Could not refresh the DNF cache (root)'))
            else:
                logger.critical("can't get root backend lock")
                if msg == 'not-authorized':  # user canceled the polkit dialog
                    errmsg = _(
                        'DNF root backend was not authorized.\n'
                        'Yum Extender will exit')
                # DNF is locked by another process
                elif msg == 'locked-by-other':
                    errmsg = _(
                        'DNF is locked by another process.\n\n'
                        'Yum Extender will exit')
                dialogs.show_information(self, errmsg)
                # close down and exit yum extender
                #self.status.SetWorking(False)  # reset working state
                #self.status.SetYumexIsRunning(self.pid, False)
                sys.exit(1)
        return self._root_backend

    @misc.ExceptionHandler
    def release_root_backend(self, quit=False):
        """Release the current root backend, if it is setup and locked."""
        if self._root_backend is None:
            return
        if self._root_locked is True:
            logger.debug('Unlock the DNF root daemon')
            self._root_backend.Unlock()
            self._root_locked = False
        if quit:
            logger.debug('Exit the DNF root daemon')
            self._root_backend.Exit()

    def exception_handler(self, e):
        """Called if exception occours in methods with the
        @ExceptionHandler decorator.
        """
        close = True
        msg = str(e)
        logger.error('BASE EXCEPTION : %s ' % msg)
        err, errmsg = self._parse_error(msg)
        logger.debug('BASE err:  [%s] - msg: %s' % (err, errmsg))
        if err == 'LockedError':
            errmsg = 'DNF is locked by another process.\n'
            '\nYum Extender will exit'
            close = False
        elif err == 'NoReply':
            errmsg = 'DNF D-Bus backend is not responding.\n'
            '\nYum Extender will exit'
            close = False
        if errmsg == '':
            errmsg = msg
        dialogs.show_information(self, errmsg)
        # try to exit the backends, ignore errors
        if close:
            try:
                self.release_root_backend(quit=True)
            except:
                pass
        #self.status.SetWorking(False)  # reset working state
        #self.status.SetYumexIsRunning(self.pid, False)
        sys.exit(1)

    def _parse_error(self, value):
        """Parse values from a DBus releated exception."""
        res = const.DBUS_ERR_RE.match(str(value))
        if res:
            err = res.groups()[0]
            err = err.split('.')[-1]
            msg = res.groups()[1]
            return err, msg
        return '', ''


class BaseWindow(Gtk.ApplicationWindow, BaseYumex):

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       title='Yum Extender - Powered by DNF',
                                       application=app)
        BaseYumex.__init__(self)
        self.app = app
        self.connect('delete_event', self.on_delete_event)
        icon = Gtk.IconTheme.get_default().load_icon('yumex-dnf', 128, 0)
        self.set_icon(icon)
        self.ui = Gtk.Builder()
        self.ui.set_translation_domain('yumex-dnf')
        try:
            self.ui.add_from_file(const.DATA_DIR + "/yumex.ui")
        except:
            raise
            dialogs.show_information(
                self, 'GtkBuilder ui file not found : ' +
                const.DATA_DIR + '/yumex.ui')
            sys.exit()
        # transaction result dialog
        self.transaction_result = dialogs.TransactionResult(self)

    def get_ui(self, widget_name):
        return self.ui.get_object(widget_name)

    def can_close(self):
        """ Check if yumex is idle and can be closed"""
        if self.is_working:
            return False
        else:
            return True

    def on_delete_event(self, *args):
        if CONFIG.conf.hide_on_close or self.is_working:
            self.iconify()
            return True
        else:
            self.app.quit()

    def load_custom_styling(self):
        """Load custom .css styling from current theme."""
        css_fn = None
        theme = Gtk.Settings.get_default().props.gtk_theme_name
        css_postfix = '%s/apps/yumex.css' % theme
        for css_prefix in [os.path.expanduser('~/.themes'),
                           '/usr/share/themes']:
            fn = os.path.join(css_prefix, css_postfix)
            logger.debug('looking for %s', fn)
            if os.path.exists(fn):
                css_fn = fn
                break
        if css_fn:
            screen = Gdk.Screen.get_default()
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(css_fn)
            context = Gtk.StyleContext()
            context.add_provider_for_screen(screen, css_provider,
                                    Gtk.STYLE_PROVIDER_PRIORITY_USER)
            logger.debug('loading custom styling : %s', css_fn)

    def on_window_state(self, widget, event):
        # save window current maximized state
        self.cur_maximized = event.new_window_state & \
                             Gdk.WindowState.MAXIMIZED != 0

    def on_window_changed(self, widget, data):
        self.cur_height = data.height
        self.cur_width = data.width

    def exception_handler(self, e):
        """Called if exception occours in methods with the
        @ExceptionHandler decorator.
        """
        close = True
        msg = str(e)
        logger.error('EXCEPTION : %s ' % msg)
        err, errmsg = self._parse_error(msg)
        logger.debug('err:  [%s] - msg: %s' % (err, errmsg))
        if err == 'LockedError':
            errmsg = 'dnf is locked by another process \n' \
                     '\nYum Extender will exit'
            close = False
        elif err == 'AccessDeniedError':
            errmsg = "Root backend was not authorized and can't continue"
            close = True
        elif err == 'FatalError':
            errmsg = 'Fatal error in yumex backend'
            close = False
        elif err == 'NoReply':
            errmsg = 'DNF Dbus backend is not responding \n'\
            '\nYum Extender will exit'
            close = False
        if errmsg == '':
            errmsg = msg
        dialogs.show_information(self, errmsg)
        # try to exit the backends, ignore errors
        if close:
            try:
                self.release_root_backend(quit=True)
            except:
                pass
        Gtk.main_quit()
        sys.exit(1)

    def set_working(self, state, insensitive=True):
        """Set the working state.

        - show/hide the progress spinner
        - show busy/normal mousepointer
        - make gui insensitive/sensitive
        - set/unset the woring state in the status icon
        based on the state.
        """
        self.is_working = state
        if state:
            self._set_busy_cursor(insensitive)
            if insensitive:
                self._disable_buttons(False)
        else:
            self.infobar.hide()
            self._set_normal_cursor()
            if insensitive:
                self._disable_buttons(True)

    def _disable_buttons(self, state):
        WIDGETS_INSENSITIVE = ['left_buttons', 'right_buttons',
                               'package_sidebar']
        for widget in WIDGETS_INSENSITIVE:
                        self.ui.get_object(widget).set_sensitive(state)

    def _set_busy_cursor(self, insensitive=False):
        """Set busy cursor in main window."""
        win = self.get_window()
        if win is not None:
            win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        misc.doGtkEvents()

    def _set_normal_cursor(self):
        """Set Normal cursor in main window."""
        win = self.get_window()
        if win is not None:
            win.set_cursor(None)
        misc.doGtkEvents()


class Window(BaseWindow):

    def __init__(self, app, gnome=True, install_mode=False):
        super(Window, self).__init__(app)
        self.gnome = gnome
        self.install_mode = install_mode
        # load custom styling from current theme
        self.load_custom_styling()

        # legacy cleanup from 4.1.x
        self.legacy_cleanup()

        # init vars
        self.cur_height = 0         # current window height
        self.cur_width = 0          # current windows width
        self.cur_maximized = False
        self.last_search = None
        self.current_filter = None
        self._root_backend = None
        self._root_locked = False
        self.search_type = 'prefix'
        self.last_search_pkgs = []
        if CONFIG.conf.archs:
            self.active_archs = CONFIG.conf.archs
        else:
            self.active_archs = list(const.PLATFORM_ARCH)
        self._grps = None   # Group and Category cache
        self.active_page = None  # Active content page
        self.search_fields = CONFIG.conf.search_fields

        if self.install_mode:
            self._setup_gui_installmode()
            self._run_actions_installmode(self.app.args, quit_app=True)
        else:
            self._setup_gui()
            self.show_all()
            # setup default selections
            self.pkg_filter.set_active('updates')

    def legacy_cleanup(self):
        """ Cleanup yumex-dnf 4.1.X leftovers"""
        # autostart file was renamed from yumex-dnf.desktop to
        # yumex-dnf-updater.desktop in 4.2.x
        # so we need to remove the old one.
        # and create a new one
        if os.path.exists(const.LEGACY_DESKTOP_FILE):
            logger.debug('removing legacy autostart: %s',
                         const.LEGACY_DESKTOP_FILE)
            os.unlink(const.LEGACY_DESKTOP_FILE)
        if CONFIG.conf.autostart:
            if not os.path.exists(const.USER_DESKTOP_FILE):
                logger.debug('create autostart: %s',
                             const.USER_DESKTOP_FILE)
                shutil.copy(const.SYS_DESKTOP_FILE, const.USER_DESKTOP_FILE)

###############################################################################
# Gui Setup
###############################################################################

    def rerun_installmode(self, args):
        '''call when yumex gui is already running and is idle
        and second instance is excuted in installmode
        '''
        self.get_ui('content_box').hide()
        WIDGETS_HIDE = ['left_buttons', 'right_buttons']
        for widget in WIDGETS_HIDE:
            self.ui.get_object(widget).hide()
        self.resize(50, 50)
        self._run_actions_installmode(args, quit_app=False)
        self.infobar.hide()
        self.get_ui('content_box').show()
        WIDGETS_HIDE = ['left_buttons', 'right_buttons']
        for widget in WIDGETS_HIDE:
            self.ui.get_object(widget).show()
        width = CONFIG.conf.win_width
        height = CONFIG.conf.win_height
        self.resize(width, height)
        self._reset()

    def _setup_gui_installmode(self):
        """setup minimal gui for doing actions from the cmd line."""
        self.set_default_size(50, 50)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)
        box.pack_start(self.get_ui('main_box'), False, True, 0)
        self.infobar = widgets.InfoProgressBar(self.ui)
        self.show_all()

    def _setup_gui(self):
        # Restore windows size
        width = CONFIG.conf.win_width
        height = CONFIG.conf.win_height
        self.set_default_size(width, height)
        if CONFIG.conf.win_maximized:
            self.maximize()
        self.connect('configure-event', self.on_window_changed)
        self.connect('window-state-event', self.on_window_state)
        self.connect('key_press_event', self.on_key_press)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)
        self._headerbar = self.get_ui('headerbar')
        if self.gnome:  # Gnome, headerbar in titlebar
            self.set_titlebar(self.get_ui('headerbar'))
            self._headerbar.set_show_close_button(True)
        else:
            box.pack_start(self.get_ui('headerbar'), False, True, 0)
            self._headerbar.set_show_close_button(False)
            self._headerbar.set_title("")
            self._headerbar.set_subtitle("")
        box.pack_start(self.get_ui('main_box'), False, True, 0)
        # Setup search
        self.search_bar = widgets.SearchBar(self)
        self.search_bar.connect('search', self.on_search)
        # Setup package filters
        self.pkg_filter = widgets.Filters(self)
        self.pkg_filter.connect('filter-changed', self.on_filter_changed)
        # Setup Content
        self.content = widgets.Content(self)
        self.content.connect('page-changed', self.on_page_changed)
        self._search_toggle = self.get_ui('sch_togglebutton')
        # Setup Options
        CONFIG.session.clean_instonly = CONFIG.conf.clean_instonly
        CONFIG.session.newest_only = CONFIG.conf.newest_only
        CONFIG.session.clean_unused = CONFIG.conf.clean_unused
        # setup the package/queue/history views
        self._setup_action_page()
        self._setup_package_page()
        self._setup_group_page()
        self._setup_history_page()

        # Setup info
        self.main_paned = self.get_ui('main_paned')
        self.main_paned.set_position(CONFIG.conf.info_paned)

        # Get the theme default TreeView text color
        color_normal = misc.get_style_color(self.package_view)
        CONFIG.conf.color_normal = misc.color_to_hex(color_normal)
        logger.debug('theme color : %s' % misc.color_to_hex(color_normal))

        # infobar
        self.infobar = widgets.InfoProgressBar(self.ui)
        self.infobar.hide()

        # preferences dialog
        self.preferences = dialogs.Preferences(self)

        # main menu setup
        self.main_menu = widgets.MainMenu(self)
        self.main_menu.connect('menu-changed', self.on_mainmenu)
        self.apply_button = self.get_ui('button_run')
        self.apply_button.connect('clicked', self.on_apply_changes)
        self.apply_button.set_sensitive(False)

        # get the arch filter
        self.arch_filter = self.backend.get_filter('arch')
        self.arch_filter.set_active(True)
        self.arch_filter.change(self.active_archs)

    def _setup_action_page(self):
        """Setup Pending Action page."""
        queue_menu = self.get_ui('queue_menu')
        self.queue_view = views.QueueView(queue_menu)
        self.queue_view.connect('queue-refresh', self.on_queue_refresh)
        # Queue Page
        sw = self.get_ui('queue_sw')
        sw.add(self.queue_view)

    def _setup_package_page(self):
        """Setup the package page."""
        arch_menu_widget = self.get_ui('arch_menu')
        self.arch_menu = widgets.ArchMenu(arch_menu_widget,
                                          const.PLATFORM_ARCH)
        self.arch_menu.connect('arch-changed', self.on_arch_changed)
        self.package_view = views.PackageView(self.queue_view, self.arch_menu)
        self.package_view.connect(
            'pkg_changed', self.on_pkg_view_selection_changed)
        sw = self.get_ui('package_sw')
        sw.add(self.package_view)
        # setup info view
        self.info = widgets.PackageInfo(self, self)

    def _setup_group_page(self):
        """Setup the group page."""
        # Groups
        sw = self.get_ui('groups_sw')
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.groups = views.GroupView(self.queue_view, self)
        self.groups.connect('group-changed', self.on_group_changed)
        #hb.pack_start(self.groups, True, True, 0)
        # sw.add(hb)
        sw.add(self.groups)
        sw = self.get_ui('group_pkg_sw')
        self.group_package_view = views.PackageView(
            self.queue_view, self.arch_menu, group_mode=True)
        #self.group_package_view.connect('arch-changed', self.on_arch_changed)
        self.group_package_view.connect(
            'pkg_changed', self.on_group_pkg_view_selection_changed)
        sw.add(self.group_package_view)

    def _setup_history_page(self):
        """Setup the history page."""
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.history_view = views.HistoryView(self)
        hb.pack_start(self.history_view, False, False, 0)
        hb.pack_start(self.history_view.pkg_view, True, True, 0)
        sw = self.get_ui('history_sw')
        sw.add(hb)
        # setup history buttons
        undo = self.get_ui('history_undo')
        undo.connect('clicked', self.on_history_undo)

###############################################################################
# Helpers
###############################################################################

    def _open_url(self, url):
        """Open URL in default browser."""
        if misc.is_url(url):  # just to be sure and prevent shell injection
            rc = subprocess.call('xdg-open %s' % url, shell=True)
            # failover to gtk.show_uri, if xdg-open fails or is not installed
            if rc != 0:
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            dialogs.show_information('%s is not an url' % url)

    def _search_name(self, data, search_flt):
        """Search package name for keyword with wildcards."""
        # only search for word larger than 3 chars
        self.last_search = data
        self.set_working(True)
        newest_only = CONFIG.session.newest_only
        self.last_search_pkgs = self.backend.get_packages_by_name(
            search_flt % data, newest_only)
        logger.debug('Packages found : %d' % len(self.last_search_pkgs))
        self.info.set_package(None)
        self.set_working(False)
        self.pkg_filter.set_active('all')

    def _search_keys(self, fields, data):
        """Search given package attributes for given keywords."""
        self.last_search = data
        self.set_working(True, True)
        newest_only = CONFIG.session.newest_only
        self.last_search_pkgs = self.backend.search(
            fields, data.split(' '), True, newest_only, True)
        self.info.set_package(None)
        self.set_working(False)
        self.pkg_filter.set_active('all')

    def _filter_search_pkgs(self, flt):
        """Get filtered search results."""
        if flt == 'updates':  # get update only
            pkgs = [
                po for po in self.last_search_pkgs if po.action in ('u', 'o')]
            return pkgs
        elif flt == 'installed':  # get installed only
            pkgs = [po for po in self.last_search_pkgs if po.installed]
            return pkgs
        elif flt == 'available':
            pkgs = [po for po in self.last_search_pkgs if po.action == 'i']
            return pkgs
        else:  # get all
            return self.last_search_pkgs

    def _reset_on_cancel(self):
        """Reset gui on user cancel"""
        self.set_working(True)
        self.infobar.hide()
        self.set_working(False)

    def _reset_on_error(self):
        """Reset gui on transaction errors."""
        self.set_working(True)
        self.infobar.hide()
        self.release_root_backend()
        self.backend.reload()
        self.set_working(False)

    @misc.ExceptionHandler
    def _reset(self):
        """Reset the gui on transaction completion."""
        self.set_working(True)
        self.infobar.info(_("Reloading package information..."))
        self.release_root_backend()
        self.backend.reload()
        # clear the package queue
        self.queue_view.queue.clear()
        self.queue_view.refresh()
        # clear search entry
        self.last_search = None
        self.search_bar.reset()
        # reset groups
        self._grps = self.backend.get_groups()
        self.groups.populate(self._grps)
        self.group_package_view.populate([])
        self.set_working(False)
        # show updates
        self.content.select_page('packages')
        self.pkg_filter.set_active('updates')

    def _load_groups(self):
        """Load groups into group cache and populate group view."""
        if not self._grps:
            logger.debug('getting group and categories')
            self._grps = self.backend.get_groups()
            self.groups.populate(self._grps)

    def _load_history(self):
        """Load history and populate view."""
        if not self.history_view.is_populated:
            result = self.backend.GetHistoryByDays(
                0, CONFIG.conf.history_days)
            self.history_view.populate(result)

    def _refresh(self):
        """Refresh package view, when arch filter is changed"""
        if self.last_search:
            self.last_search = None
            self.search_bar.signal()
        else:
            self.pkg_filter.set_active(self.pkg_filter.current)

    def _switch_to(self, page):
        if not self.active_page == page:
            self.content.select_page(page)

###############################################################################
# Transaction Processing
###############################################################################

    def _run_actions_installmode(self, args, quit_app):
        action = None
        if args.install:
            action = 'install'
            package = args.install
        elif args.remove:
            action = 'remove'
            package = args.remove
        elif args.updateall:
            action = 'update'
            package = '*'
        if action:
            self._process_actions_installmode(action, package,
                                              args.yes, quit_app)

    def _populate_transaction(self):
        self.backend.ClearTransaction()
        errors = 0
        error_msgs = set()
        for action in const.QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    logger.debug('adding: %s %s' %
                                 (const.QUEUE_PACKAGE_TYPES[action],
                                  pkg.pkg_id))
                    rc, trans = self.backend.AddTransaction(
                        pkg.pkg_id,
                        const.QUEUE_PACKAGE_TYPES[action])
                    if not rc:
                        logger.debug('result : %s: %s' % (rc, pkg))
                        errors += 1
                        error_msgs.add('%s : %s' %
                                       (const.QUEUE_PACKAGE_TYPES[action], pkg))
                else:
                    logger.debug('adding: %s %s' %
                                 (const.QUEUE_PACKAGE_TYPES[action],
                                  pkg.pkg_id))
                    rc, trans = self.backend.AddTransaction(
                        pkg.pkg_id, const.QUEUE_PACKAGE_TYPES[action])
                    if not rc:
                        logger.debug('result: %s: %s' % (rc, pkg))
                        errors += 1
                        error_msgs.add('%s : %s' %
                                       (const.QUEUE_PACKAGE_TYPES[action], pkg))
        for grp_id, action in self.queue_view.queue.get_groups():
            if action == 'i':
                rc, trans = self.backend.GroupInstall(grp_id)
            else:
                rc, trans = self.backend.GroupRemove(grp_id)
            if not rc:
                errors += 1
                error_msgs.add('group : %s : %s ' % (action, grp_id))
        logger.debug(' add transaction errors : %d', errors)
        if errors > 0:
            raise misc.TransactionBuildError(error_msgs)

    def _check_protected(self, trans):
        """Check for deletion protected packages in transaction"""
        protected = []
        for action, pkgs in trans:
            if action == 'remove':
                for id, size, replaces in pkgs:
                    (n, e, v, r, a, repo_id) = str(id).split(',')
                    if n in CONFIG.conf.protected:
                        protected.append(n)
        return protected

    def _build_from_queue(self):
        """Populate transaction from queue and resolve deps."""
        # switch to queue view
        if self.queue_view.queue.total() == 0:
            raise misc.QueueEmptyError
        self.content.select_page('actions')
        self._populate_transaction()
        self.infobar.info(_('Searching for dependencies'))
        rc, result = self.backend.BuildTransaction()
        self.infobar.info(_('Dependencies resolved'))
        if not rc:
            raise misc.TransactionSolveError(result)
        return result

    def _get_transaction(self):
        """Get current transaction."""
        rc, result = self.backend.GetTransaction()
        if not rc:
            raise misc.TransactionSolveError(result)
        return result

    def _run_transaction(self):
        """Run the current transaction."""
        self.infobar.info(_('Applying changes to the system'))
        self.set_working(True, True)
        rc, result = self.backend.RunTransaction()
        # This can happen more than once (more gpg keys to be
        # imported)
        while rc == 1:
            # get info about gpgkey to be comfirmed
            values = self.backend._gpg_confirm
            if values:  # There is a gpgkey to be verified
                (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
                logger.debug('GPGKey : %s' % repr(values))
                ok = dialogs.ask_for_gpg_import(self, values)
                if ok:
                    # tell the backend that the gpg key is confirmed
                    self.backend.ConfirmGPGImport(hexkeyid, True)
                    # rerun the transaction
                    # FIXME: It should not be needed to populate
                    # the transaction again
                    self._populate_transaction()
                    rc, result = self.backend.BuildTransaction()
                    rc, result = self.backend.RunTransaction()
                else:
                    break
            else:  # error in signature verification
                dialogs.show_information(
                    self, _('Error checking package signatures\n'),
                             '\n'.join(result))
                break

        if rc == 4:  # Download errors
            dialogs.show_information(
                self, _('Downloading error(s)\n'),
                         '\n'.join(result))
            self._reset_on_cancel()
            return
        elif rc != 0:  # other transaction errors
            dialogs.show_information(
                self, _('Error in transaction\n'),
                         '\n'.join(result))
        self._reset()
        return

    @misc.ExceptionHandler
    def _process_actions_installmode(self, action, package, always_yes,
                                     app_quit):
        """Process the pending actions from the command line.

        :param action: action to perform (install/remove)
        :param package: package to work on
        :param always_yes: ask the user or default to yes/ok to all questions
        """
        if action == 'install':
            self.infobar.info(_('Installing package: %s') % package)
            exit_msg = _('%s was installed successfully') % package
            self.infobar.info_sub(package)
            txmbrs = self.backend.Install(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
        elif action == 'remove':
            self.infobar.info(_('Removing package: %s') % package)
            exit_msg = _('%s was removed successfully') % package
            self.infobar.info_sub(package)
            txmbrs = self.backend.Remove(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
        elif action == 'update':
            self.infobar.info(_('Updating all available updates'))
            exit_msg = _('Available updates was applied successfully')
            txmbrs = self.backend.Update('*')
        self.infobar.info(_('Searching for dependencies'))
        rc, result = self.backend.BuildTransaction()
        self.infobar.info(_('Dependencies resolved'))
        if rc:
            self.transaction_result.populate(result, '')
            if not always_yes:
                ok = self.transaction_result.run()
            else:
                ok = True
            if ok:  # Ok pressed
                self.infobar.info(_('Applying changes to the system'))
                self.backend.RunTransaction()
                self.release_root_backend()
                self.hide()
                misc.notify('Yum Extender', exit_msg)
        else:
            dialogs.show_information(
                self, _('Error(s) in search for dependencies'),
                        '\n'.join(result))
        if app_quit:
            self.release_root_backend(quit=True)
            self.app.quit()

    @misc.ExceptionHandler
    def _process_actions(self, from_queue=True):
        """Process the current actions in the queue.

        - setup the Dnf transaction
        - resolve dependencies
        - ask user for confirmation on result of depsolve
        - run the transaction
        """
        self.set_working(True, True)
        self.infobar.info(_('Preparing system for applying changes'))
        try:
            if from_queue:
                result = self._build_from_queue()
            else:
                result = self._get_transaction()
            self.set_working(False)
            # check for protected packages
            check = self._check_protected(result)
            if check:
                dialogs.show_information(
                self, _("Can't remove protected package(s)"),
                        '\n'.join(check))
                self._reset_on_cancel()
                return
            # transaction confirmation dialog
            self.transaction_result.populate(result, '')
            ok = self.transaction_result.run()
            if ok:  # Ok pressed
                self._run_transaction()
            else:  # user cancelled transaction
                self._reset_on_cancel()
                return
        except misc.QueueEmptyError:  # Queue is empty
            self.set_working(False)
            dialogs.show_information(self, _('No pending actions in queue'))
            self._reset_on_cancel()
        except misc.TransactionBuildError as e:  # Error in building transaction
            dialogs.show_information(
                self, _('Error(s) in building transaction'),
                        '\n'.join(e.msgs))
            self._reset_on_cancel()
        except misc.TransactionSolveError as e:
            dialogs.show_information(
                    self, _('Error(s) in search for dependencies'),
                            '\n'.join(e.msgs))
            self._reset_on_error()

###############################################################################
# Callback handlers
###############################################################################
    def on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if event_and_modifiers != 0:
            # Open search bar on Ctrl + S
            if (event.keyval == Gdk.KEY_f and
                    event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                if self.active_page == 'packages':
                    self.search_bar.toggle()
            # Switch to packages page on Alt + 1
            if (event.keyval == Gdk.KEY_1 and
                    event_and_modifiers == Gdk.ModifierType.MOD1_MASK):
                self._switch_to('packages')
            # Switch to groups page on Alt + 2
            if (event.keyval == Gdk.KEY_2 and
                    event_and_modifiers == Gdk.ModifierType.MOD1_MASK):
                self._switch_to('groups')
            # Switch to groups page on Alt + 3
            if (event.keyval == Gdk.KEY_3 and
                    event_and_modifiers == Gdk.ModifierType.MOD1_MASK):
                self._switch_to('history')
            # Switch to groups page on Alt + 4
            if (event.keyval == Gdk.KEY_4 and
                    event_and_modifiers == Gdk.ModifierType.MOD1_MASK):
                self._switch_to('actions')

    def on_mainmenu(self, widget, action, data):
        """Handle mainmenu actions"""
        if action == 'pref':
            need_reset = self.preferences.run()
            if need_reset:
                self._reset()
        elif action == 'quit':
            if self.can_close():
                self.app.quit()
        elif action == 'about':
            dialog = dialogs.AboutDialog()
            dialog.run()
            dialog.destroy()
        elif action == 'docs':
            self._open_url('http://yumex-dnf.readthedocs.org/en/latest/')
        elif action in ['newest_only', 'clean_instonly', 'clean_unused']:
            setattr(CONFIG.session, action, data)
            logger.debug('session option : %s = %s' %
                     (action, getattr(CONFIG.session, action)))
            if action in ['newest_only']:  # search again
                self._refresh()
            if action in ['clean_instonly', 'clean_unused']:
                self._reset_on_error()

    def on_apply_changes(self, widget):
        """Apply Changes button callback."""
        self._process_actions()

    def on_page_changed(self, widget, page):
        """Handle content page is changed."""
        if page == 'packages':
            self._search_toggle.show()
            self.search_bar.show()
            self.info.show()
        else:
            self._search_toggle.hide()
            self.search_bar.hide()
            self.info.show(False)
        if page == 'groups':
            self._load_groups()
            self.info.show()
        elif page == 'history':
            self._load_history()
        self.active_page = page

    def on_search(self, widget, key, sch_type, fields):
        """Handle search."""
        self.search_bar.show_spinner(True)
        if key == '':  # revert to the current selected filter
            self.last_search = None
            self.last_search_pkgs = []
            self.pkg_filter.set_active(self.current_filter)
        else:
            if sch_type == 'keyword':
                flt = '*%s*'
                self._search_name(key, flt)
            elif sch_type == 'prefix':
                flt = '%s*'
                self._search_name(key, flt)
            elif sch_type == 'fields':
                self._search_keys(fields, key)
        self.search_bar.show_spinner(False)

    def on_filter_changed(self, widget, data):
        """Handle changes in package filter."""
        self.infobar.info(const.PACKAGE_LOAD_MSG[data])
        self.set_working(True, True)
        if self.last_search:  # we are searching
            pkgs = self._filter_search_pkgs(data)
        else:  # normal package filter
            self.current_filter = self.pkg_filter.current
            pkgs = self.backend.get_packages(data)
            if data == 'updates':
                if CONFIG.session.newest_only:
                    pkgs = self.backend.get_packages(data)
                else:
                    pkgs = self.backend.get_packages('updates_all')
                obs_pkgs = self.backend.get_packages('obsoletes')
                pkgs.extend(obs_pkgs)
            else:
                pkgs = self.backend.get_packages(data)
            #self.status.SetUpdateCount(len(pkgs))
        self.info.set_package(None)
        self.infobar.info(_('Adding packages to view'))
        self.package_view.populate(pkgs)
        self.set_working(False)
        self.infobar.hide()
        if data == 'updates':
            self.package_view.set_header_click(True)
        else:
            self.package_view.set_header_click(False)

    def on_queue_refresh(self, widget, total):
        '''Handle content of the queue is changed.'''
        if total > 0:
            self.apply_button.set_sensitive(True)
        else:
            self.apply_button.set_sensitive(False)

    def on_arch_changed(self, widget, data):
        """Arch changed in arch menu callback."""
        self.active_archs = data.split(',')
        logger.debug('arch-changed : %s' % self.active_archs)
        self.arch_filter.change(self.active_archs)
        self._refresh()

    def on_pkg_view_selection_changed(self, widget, pkg):
        """Handle package selection on package page."""
        self.info.set_package(pkg)

    def on_group_pkg_view_selection_changed(self, widget, pkg):
        """Handle package selection on group page."""
        self.info.set_package(pkg)

    def on_group_changed(self, widget, grp_id):
        """Handle group selection on group page."""
        logger.debug('on_group_changed : %s ' % grp_id)
        self.set_working(True, True)
        pkgs = self.backend.get_group_packages(grp_id, 'all')
        self.group_package_view.populate(pkgs)
        self.set_working(False)

    def on_history_undo(self, widget):
        """Handle the undo button on history page."""
        tid = self.history_view.get_selected()
        logger.debug('History Undo : %s', tid)
        rc, messages = self.backend.HistoryUndo(tid)
        if rc:
            self.process_actions(from_queue=False)
        else:
            msg = "Can't undo history transaction :\n%s" % \
                  ("\n".join(messages))
            logger.debug(msg)
            dialogs.show_information(
                self, _('Error in undo history transaction'),
                "\n".join(messages))


class YumexApplication(Gtk.Application):
    """Main application."""

    def __init__(self):
        Gtk.Application.__init__(self,
                    application_id="dk.yumex.yumex-ui",
                    flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

        self.connect("activate", self.on_activate)
        self.connect("command-line", self.on_command_line)
        self.connect("shutdown", self.on_shutdown)
        self.running = False
        self.args = None
        self.dont_close = False
        self.window = None
        self.install_mode = False

    def on_activate(self, app):
        if not self.running:
            self.window = Window(self, gnome=CONFIG.conf.headerbar,
                                 install_mode=self.install_mode)
            app.add_window(self.window)
            self.running = True
            self.window.show()
        else:
            self.window.present()
            if self.install_mode and self.window.can_close():
                self.window.rerun_installmode(self.current_args)

    def on_command_line(self, app, args):
        parser = argparse.ArgumentParser(prog='app')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument(
            '-y', '--yes', action='store_true',
             help='Answer yes/ok to all questions')
        parser.add_argument('--exit', action='store_true',
            help='tell dnfdaemon dbus services used by yumex to exit')
        parser.add_argument(
            '-I', '--install', type=str, metavar='PACKAGE',
            help='Install Package')
        parser.add_argument(
            '-R', '--remove', type=str, metavar='PACKAGE',
            help='Remove Package')
        parser.add_argument(
            '--updateall', action='store_true',
            help='apply all available updates')
        if not self.running:
            # First run
            self.args = parser.parse_args(args.get_arguments()[1:])
            if self.args.exit:  # kill dnf daemon and quit
                misc.dbus_dnfsystem('Exit')
                sys.exit(0)

            if self.args.debug:
                misc.logger_setup(loglvl=logging.DEBUG)
            else:
                misc.logger_setup()
            if self.args.install or self.args.remove or self.args.updateall:
                self.install_mode = True
        else:
            # Second Run
            # parse cmdline in a non quitting way
            self.current_args = \
                parser.parse_known_args(args.get_arguments()[1:])[0]
            if self.current_args.exit:
                if self.window.can_close():
                    self.quit()
                else:
                    self.logger.info("Application is busy")
            if self.current_args.install or self.current_args.remove or \
               self.current_args.updateall:
                self.install_mode = True
        self.activate()
        return 0

    def on_shutdown(self, app):
        if self.window and not self.install_mode:
            CONFIG.conf.info_paned = self.window.main_paned.get_position()
            if self.window.cur_maximized:
                CONFIG.conf.win_maximized = True
            else:
                CONFIG.conf.win_width = self.window.cur_width
                CONFIG.conf.win_height = self.window.cur_height
                CONFIG.conf.win_maximized = False
            self.window.release_root_backend(quit=True)
        logger.info('Saving config on exit')
        CONFIG.write()
        return 0

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

import gi  # isort:skip
from gi.repository import Gdk, Gtk  # isort:skip

import logging
import os.path
import shutil
import subprocess

from pathlib import Path

import yumex.common.const as const
import yumex.gui.dialogs as dialogs
import yumex.common as misc

from yumex.common import CONFIG, _, ngettext
from yumex.gui.dialogs.preferences import Preferences
from yumex.gui.dialogs.aboutdialog import AboutDialog
from yumex.gui.dialogs.progresssplash import ProgressSplash

from yumex.gui.views.packageview import PackageView
from yumex.gui.views.queueview import QueueView
from yumex.gui.views.historyview import HistoryView
from yumex.gui.views.groupview import GroupView
from yumex.gui.widgets.content import Content
from yumex.gui.widgets.filters import ExtraFilters, Filters
from yumex.gui.widgets.mainnenu import MainMenu
from yumex.gui.widgets.packageinfo import PackageInfo
from yumex.gui.widgets.progress import Progress
from yumex.gui.widgets.searchbar import SearchBar

from yumex.gui.window.basewindow import BaseWindow

logger = logging.getLogger('yumex.gui.window')


class Window(BaseWindow):
    def __init__(self, app, use_headerbar=True, install_mode=False):
        super(Window, self).__init__(app)
        self.use_headerbar = use_headerbar
        self.install_mode = install_mode
        # load custom styling from current theme
        self.load_custom_styling()

        # legacy cleanup from 4.1.x
        self.legacy_cleanup()

        # init vars
        self.cur_height = 0  # current window height
        self.cur_width = 0  # current windows width
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
        self._grps = None  # Group and Category cache
        self.active_page = 'packages'  # Active content page
        self.search_fields = CONFIG.conf.search_fields

        if self.install_mode:
            self._setup_gui_installmode()
            self._run_actions_installmode(self.app.args, quit_app=True)
        else:
            self._setup_gui()
            self.show_all()
            self._setup_arch()
            # setup default selections
            self.pkg_filter.set_active('updates')
            if CONFIG.conf.auto_select_updates:
                self.package_view.on_section_header_clicked(None)
            if CONFIG.conf.search_visible:
                self.search_bar.toggle()

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
                logger.debug('create autostart: %s', const.USER_DESKTOP_FILE)
                shutil.copy(const.SYS_DESKTOP_FILE, const.USER_DESKTOP_FILE)
        # key is renamed to keyword
        if CONFIG.conf.search_default == 'key':
            CONFIG.conf.search_default = 'keyword'

###############################################################################
# Gui Setup
###############################################################################

    def rerun_installmode(self, args):
        """call when yumex gui is already running and is idle
        and second instance is excuted in installmode
        """
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
        self.infobar = Progress(self.ui, self)
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
        if self.use_headerbar:  # Gnome, headerbar in titlebar
            hb = self.get_ui('headerbar')
            rb = self.get_ui('right_header')
            lb = self.get_ui('left_header')
            hb.set_custom_title(lb)
            hb.pack_end(rb)
            self.set_titlebar(hb)
            self._headerbar.set_show_close_button(True)
        else:
            hb = self.get_ui('headerbox')
            rb = self.get_ui('right_header')
            rb.set_margin_top(3)
            rb.set_margin_bottom(3)
            rb.set_margin_start(3)
            rb.set_margin_end(3)
            lb = self.get_ui('left_header')
            lb.set_margin_top(3)
            lb.set_margin_bottom(3)
            lb.set_margin_start(3)
            lb.set_margin_end(3)
            hb.set_center_widget(lb)
            hb.pack_end(rb, False, True, 0)
            box.pack_start(hb, False, True, 0)
        box.pack_start(self.get_ui('main_overlay'), False, True, 0)
        # Setup search
        self.search_bar = SearchBar(self)
        self.search_bar.connect('search', self.on_search)
        # Setup package filters
        self.pkg_filter = Filters(self)
        self.pkg_filter.connect('filter-changed', self.on_filter_changed)
        # Setup Content
        self.content = Content(self)
        self.content.connect('page-changed', self.on_page_changed)
        self._search_toggle = self.get_ui('sch_togglebutton')
        # Setup Options
        CONFIG.session.clean_instonly = CONFIG.conf.clean_instonly
        CONFIG.session.newest_only = CONFIG.conf.newest_only
        CONFIG.session.clean_unused = CONFIG.conf.clean_unused
        if CONFIG.conf.repo_saved:
            CONFIG.session.enabled_repos = CONFIG.conf.repo_enabled
        # setup the package/queue/history views
        self._setup_action_page()
        self._setup_package_page()
        self._setup_group_page()
        self._setup_history_page()

        # Setup info
        self.main_paned = self.get_ui('main_paned')
        self.main_paned.set_position(CONFIG.conf.info_paned)
        self.main_paned.set_wide_handle(True)  # use wide separator bar (off)

        # infobar
        self.infobar = Progress(self.ui, self)
        self.infobar.hide()

        # preferences dialog
        self.preferences = Preferences(self)

        # main menu setup
        self.main_menu = MainMenu(self)
        self.main_menu.connect('menu-changed', self.on_mainmenu)
        self.apply_button = self.get_ui('button_run')
        self.apply_button.connect('clicked', self.on_apply_changes)
        self.apply_button.set_sensitive(False)

        # shortcuts
        self.app.set_accels_for_action('win.quit', ['<Ctrl>Q'])
        self.app.set_accels_for_action('win.docs', ['F1'])
        self.app.set_accels_for_action('win.pref', ['<Alt>Return'])

        self.working_splash = ProgressSplash(self)

    def _setup_arch(self):
        self.infobar.message(_('Downloading Repository Metadata'))
        # setup the arch filter
        self.arch_filter = self.backend.get_filter('arch')
        self.arch_filter.set_active(True)
        self.arch_filter.change(self.active_archs)

    def _setup_action_page(self):
        """Setup Pending Action page."""
        queue_menu = self.get_ui('queue_menu')
        self.queue_view = QueueView(queue_menu)
        self.queue_view.connect('queue-refresh', self.on_queue_refresh)
        # Queue Page
        sw = self.get_ui('queue_sw')
        sw.add(self.queue_view)

    def _setup_package_page(self):
        """Setup the package page."""
        self.package_view = PackageView(self.queue_view)
        self.package_view.connect('pkg_changed',
                                  self.on_pkg_view_selection_changed)
        sw = self.get_ui('package_sw')
        sw.add(self.package_view)
        # setup info view
        self.info = PackageInfo(self, self)
        self.extra_filters = ExtraFilters(self)
        self.extra_filters.connect('changed', self.on_extra_filters)

    def _setup_group_page(self):
        """Setup the group page."""
        # Groups
        sw = self.get_ui('groups_sw')
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.groups = GroupView(self.queue_view, self)
        self.groups.connect('group-changed', self.on_group_changed)
        # sw.add(hb)
        sw.add(self.groups)
        sw = self.get_ui('group_pkg_sw')
        self.group_package_view = PackageView(self.queue_view, group_mode=True)
        self.group_package_view.connect(
            'pkg_changed', self.on_group_pkg_view_selection_changed)
        sw.add(self.group_package_view)

    def _setup_history_page(self):
        """Setup the history page."""
        right_sw = self.get_ui('history_right_sw')
        left_sw = self.get_ui('history_left_sw')
        self.history_view = HistoryView(self)
        left_sw.add(self.history_view)
        right_sw.add(self.history_view.pkg_view)
        # setup history buttons
        undo = self.get_ui('history_undo')
        # FIXME: History undo is broken in dnfdaemon, because of changes in private API
        # so disable the botton
        undo.set_sensitive(False)
        undo.connect('clicked', self.on_history_undo)

###############################################################################
# Helpers
###############################################################################

    def _show_shortcuts(self):
        builder = Gtk.Builder.new_from_file(const.UI_DIR + '/shortcuts.ui')
        shortcuts = builder.get_object('yumex-shortcuts')
        shortcuts.set_default_size(1000, 600)
        shortcuts.set_transient_for(self)
        shortcuts.present()

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
        self.last_search_pkgs = self.backend.search(fields, data.split(' '),
                                                    True, newest_only, True)
        self.info.set_package(None)
        self.set_working(False)
        self.pkg_filter.set_active('all')

    def _filter_search_pkgs(self, flt):
        """Get filtered search results."""
        if flt == 'updates':  # get update only
            pkgs = [
                po for po in self.last_search_pkgs if po.action in ('u', 'o')
            ]
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
        self.set_working(True, splash=True)
        self.infobar.hide()
        self.set_working(False, splash=True)

    def _reset_on_error(self):
        """Reset gui on transaction errors."""
        self.set_working(True, splash=True)
        self.infobar.hide()
        self.release_root_backend()
        self.backend.reload()
        self.set_working(False, splash=True)

    @misc.exception_handler
    def _reset(self):
        """Reset the gui on transaction completion."""
        self.set_working(True, splash=True)
        self.infobar.message(_("Reloading package information..."))
        self.release_root_backend()
        self.backend.reload()
        # clear the package queue
        self.queue_view.queue.clear()
        self.queue_view.refresh()
        # clear search entry
        self.last_search = None
        self.search_bar.reset()
        # reset groups
        self._grps = None
        self._load_groups
        # reset history
        self.history_view.reset()
        self._load_history()
        self.set_working(False, splash=True)
        # show updates
        self.content.select_page('packages')
        self.pkg_filter.set_active('updates')

    def _load_groups(self):
        """Load groups into group cache and populate group view."""
        if not self._grps:
            logger.debug('getting group and categories')
            self._grps = self.backend.get_groups()
            self.groups.populate(self._grps)
            self.group_package_view.populate([])

    def _load_history(self):
        """Load history and populate view."""
        if not self.history_view.is_populated:
            result = self.backend.GetHistoryByDays(0, CONFIG.conf.history_days)
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
        package = None
        if args.install:
            action = 'install'
            if '.rpm' in args.install:  # this is an .rpm file
                path = Path(args.install)
                path = path.expanduser()
                path = path.resolve()
                logger.debug(f'Install (rpm): {path}')
                package = path.as_posix()
            else:
                package = args.install
        elif args.remove:
            action = 'remove'
            package = args.remove
        elif args.updateall:
            action = 'update'
            package = '*'
        if action:
            self._process_actions_installmode(action, package, args.yes,
                                              quit_app)

    def _populate_transaction(self):
        self.backend.ClearTransaction()
        errors = 0
        error_msgs = []
        for action in const.QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    logger.debug(
                        'adding: %s %s' %
                        (const.QUEUE_PACKAGE_TYPES[action], pkg.pkg_id))
                    rc, msgs = self.backend.AddTransaction(
                        pkg.pkg_id, const.QUEUE_PACKAGE_TYPES[action])
                    if not rc:
                        logger.debug('result : %s: %s' % (rc, pkg))
                        errors += 1
                        error_msgs.add(
                            '%s : %s' %
                            (const.QUEUE_PACKAGE_TYPES[action], pkg))
                else:
                    logger.debug(
                        'adding: %s %s' %
                        (const.QUEUE_PACKAGE_TYPES[action], pkg.pkg_id))
                    rc, msgs = self.backend.AddTransaction(
                        pkg.pkg_id, const.QUEUE_PACKAGE_TYPES[action])
                    if not rc:
                        logger.debug('result: %s: %s' % (rc, pkg))
                        errors += 1
                        error_msgs.add(
                            '%s : %s' %
                            (const.QUEUE_PACKAGE_TYPES[action], pkg))
        for grp_id, action in self.queue_view.queue.get_groups():
            if action == 'i':
                rc, msgs = self.backend.GroupInstall(grp_id)
                logger.debug(f'GroupInstall : {grp_id} {rc=} {msgs=}')
            else:
                rc, msgs = self.backend.GroupRemove(grp_id)
            if not rc:
                errors += 1
                if action == 'i':
                    error_msgs.append(f'\ngroup install : {grp_id} ')
                    error_msgs.extend(msgs)
                else:
                    error_msgs.append(f'\ngroup remove : {grp_id} ')
                    error_msgs.extend(msgs)

        if errors > 0:
            raise misc.TransactionBuildError(error_msgs)

    def _check_protected(self, trans):
        """Check for deletion protected packages in transaction"""
        protected = []
        for action, pkgs in trans:
            if action == 'remove':
                for pkgid, size, replaces in pkgs:
                    (n, e, v, r, a, repo_id) = str(pkgid).split(',')
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
        self.infobar.message(_('Searching for dependencies'))
        rc, result = self.backend.BuildTransaction()
        self.infobar.message(_('Dependencies resolved'))
        if not rc:
            raise misc.TransactionSolveError(result)
        return result

    def _get_transaction(self):
        """Get current transaction."""
        rc, result = self.backend.GetTransaction()
        logger.debug(f'GetTransaction : {rc=}')
        if not rc:
            raise misc.TransactionSolveError(result)
        return result

    def _run_transaction(self):
        """Run the current transaction."""
        self.infobar.message(_('Applying changes to the system'))
        self.set_working(True, True, splash=True)
        rc, result = self.backend.RunTransaction()
        logger.debug(f'RunTransaction : {rc=}')
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
                self,
                ngettext('Downloading error\n', 'Downloading errors\n',
                         len(result)), '\n'.join(result))
            self._reset_on_cancel()
            return
        elif rc != 0:  # other transaction errors
            dialogs.show_information(
                self,
                ngettext('Error in transaction\n', 'Errors in transaction\n',
                         len(result)), '\n'.join(result))
        self._reset()
        return

    @misc.exception_handler
    def _process_actions_installmode(self, action, package, always_yes,
                                     app_quit):
        """Process the pending actions from the command line.

        :param action: action to perform (install/remove)
        :param package: package to work on
        :param always_yes: ask the user or default to yes/ok to all questions
        """
        exit_msg = ""
        if action == 'install':
            self.infobar.message(_('Installing package: %s') % package)
            exit_msg = _('%s was installed successfully') % package
            self.infobar.message_sub(package)
            txmbrs = self.backend.Install(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
        elif action == 'remove':
            self.infobar.message(_('Removing package: %s') % package)
            exit_msg = _('%s was removed successfully') % package
            self.infobar.message_sub(package)
            txmbrs = self.backend.Remove(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
        elif action == 'update':
            self.infobar.message(_('Updating all available updates'))
            exit_msg = _('Available updates was applied successfully')
            txmbrs = self.backend.Update('*')
        self.infobar.message(_('Searching for dependencies'))
        rc, result = self.backend.BuildTransaction()
        self.infobar.message(_('Dependencies resolved'))
        if rc:
            self.transaction_result.populate(result, '')
            if not always_yes:
                ok = self.transaction_result.run()
            else:
                ok = True
            if ok:  # Ok pressed
                self.infobar.message(_('Applying changes to the system'))
                self.backend.RunTransaction()
                self.release_root_backend()
                self.hide()
                misc.notify('Yum Extender', exit_msg)
        else:
            dialogs.show_information(
                self,
                ngettext('Error in search for dependencies',
                         'Errors in search for dependencies', len(result)),
                '\n'.join(result))
        if app_quit:
            self.release_root_backend(quit_dnfdaemon=True)
            self.app.quit()

    @misc.exception_handler
    def _process_actions(self, from_queue=True):
        """Process the current actions in the queue.

        - setup the Dnf transaction
        - resolve dependencies
        - ask user for confirmation on result of depsolve
        - run the transaction
        """
        self.set_working(True, True)
        self.infobar.message(_('Preparing system for applying changes'))
        try:
            if from_queue:
                result = self._build_from_queue()
            else:
                result = self._get_transaction()
            self.set_working(False)
            # check for protected packages
            check = self._check_protected(result)
            if check:
                self.error_dialog.show(
                    ngettext("Can't remove protected package:",
                             "Can't remove protected packages:", len(check)) +
                    misc.list_to_string(check, "\n ", ",\n "))
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
        except misc.TransactionBuildError as e:
            # Error in building transaction
            self.error_dialog.show(
                ngettext('Error in building transaction\n',
                         'Errors in building transaction\n', len(e.msgs)) +
                '\n'.join(e.msgs))
            self._reset_on_cancel()
        except misc.TransactionSolveError as e:
            self.error_dialog.show(
                ngettext('Error in search for dependencies\n',
                         'Errors in search for dependencies\n', len(e.msgs)) +
                '\n'.join(e.msgs))
            self._reset_on_error()


###############################################################################
# Callback handlers
###############################################################################

    def on_key_press(self, widget, event):
        shortcut = Gtk.accelerator_get_label(event.keyval, event.state)
        logger.debug(f'keyboard shotcut : {shortcut}')

        if shortcut == 'Ctrl+F' or shortcut == 'Shift+Ctrl+F':
            if self.active_page == 'packages':
                self.search_bar.toggle()
        elif shortcut == 'Alt+1':
            self._switch_to('packages')
        elif shortcut == 'Alt+2':
            self._switch_to('groups')
        elif shortcut == 'Alt+3':
            self._switch_to('history')
        elif shortcut == 'Alt+4':
            self._switch_to('actions')
        elif shortcut == 'Alt+A':
            self._process_actions()
        elif shortcut == 'Alt+X':
            self.extra_filters.popup()
        elif shortcut == 'Ctrl+1':
            if self.active_page == 'packages':
                self.pkg_filter.set_active('updates')
        elif shortcut == 'Ctrl+2':
            if self.active_page == 'packages':
                self.pkg_filter.set_active('installed')
        elif shortcut == 'Ctrl+3':
            if self.active_page == 'packages':
                self.pkg_filter.set_active('available')
        elif shortcut == 'Ctrl+4':
            if self.active_page == 'packages':
                self.pkg_filter.set_active('all')
        elif shortcut == 'Ctrl+Alt+1':
            if self.active_page == 'packages':
                self.info.set_active('desc')
        elif shortcut == 'Ctrl+Alt+2':
            if self.active_page == 'packages':
                self.info.set_active('updinfo')
        elif shortcut == 'Ctrl+Alt+3':
            if self.active_page == 'packages':
                self.info.set_active('files')
        elif shortcut == 'Ctrl+Alt+4':
            if self.active_page == 'packages':
                self.info.set_active('deps')

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
            dialog = AboutDialog(self)
            dialog.run()
            dialog.destroy()
        elif action == 'docs':
            self._open_url('http://yumex-dnf.readthedocs.org/en/latest/')
        elif action == 'reload':
            self.reset_cache()
        elif action == 'shortcuts':
            self._show_shortcuts()

    def on_extra_filters(self, widget, data, para):
        """Handle the Extra Filters"""
        if data == 'arch':
            self.active_archs = para
            self.arch_filter.change(self.active_archs)
            logger.debug('arch changed : %s' % self.active_archs)
            self._refresh()
        elif data == 'newest_only':
            CONFIG.session.newest_only = para
            logger.debug('newest_only changed : %s' % para)
            self._refresh()

    def on_apply_changes(self, widget):
        """Apply Changes button callback."""
        self._process_actions()

    def on_page_changed(self, widget, page):
        """Handle content page is changed."""
        if page == 'packages':
            self._search_toggle.set_sensitive(True)
            self.search_bar.show()
            self.info.show()
        else:
            self._search_toggle.set_sensitive(False)
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
        self.infobar.message(const.PACKAGE_LOAD_MSG[data])
        self.set_working(True, True)
        if self.last_search:  # we are searching
            pkgs = self._filter_search_pkgs(data)
        else:  # normal package filter
            self.current_filter = self.pkg_filter.current
            if data == 'updates':
                if CONFIG.session.newest_only:
                    pkgs = self.backend.get_packages(data)
                else:
                    pkgs = self.backend.get_packages('updates_all')
                obs_pkgs = self.backend.get_packages('obsoletes')
                pkgs.extend(obs_pkgs)
            else:
                pkgs = self.backend.get_packages(data)
        self.info.set_package(None)
        self.infobar.message(_('Adding packages to view'))
        self.package_view.populate(pkgs)
        self.set_working(False)
        self.infobar.hide()
        if data == 'updates':
            self.package_view.set_header_click(True)
        else:
            self.package_view.set_header_click(False)

    def on_queue_refresh(self, widget, total):
        """Handle content of the queue is changed."""
        if total > 0:
            self.apply_button.set_sensitive(True)
        else:
            self.apply_button.set_sensitive(False)

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
            self._process_actions(from_queue=False)
        else:
            msg = "Can't undo history transaction :\n%s" % \
                  ("\n".join(messages))
            logger.debug(msg)
            dialogs.show_information(self,
                                     _('Error in undo history transaction'),
                                     "\n".join(messages))

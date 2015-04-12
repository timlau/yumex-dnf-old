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
#    along with this program; if not, write to
#    the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from __future__ import absolute_import

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from yumex.misc import doGtkEvents, _, CONFIG, ExceptionHandler

import argparse
import logging
import datetime
import subprocess
import sys
import re
import yumex.const as const
import yumex.status
import yumex.dnf_backend
import yumex.gui.dialogs as dialogs
import yumex.gui.views as views
import yumex.gui.widgets

logger = logging.getLogger('yumex')


class BaseWindow(Gtk.ApplicationWindow):
    """ Common Yumex Base window """

    def __init__(self, app, status):
        Gtk.ApplicationWindow.__init__(
            self, title='Yum Extender - Powered by dnf', application=app)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.app = app
        self.status = status
        icon = Gtk.IconTheme.get_default().load_icon('yumex-dnf', 128, 0)
        self.set_icon(icon)
        self.connect('delete_event', self.on_delete_event)

        self._root_backend = None
        self._root_locked = False
        self.is_working = False

        # setup GtkBuilder
        self.ui = Gtk.Builder()
        self.ui.set_translation_domain('yumex-dnf')
        try:
            self.ui.add_from_file(const.DATA_DIR + '/yumex.ui')
        except:
            raise
            dialogs.show_information(
                self, 'GtkBuilder ui file not found : ' +
                const.DATA_DIR + '/yumex.ui')
            sys.exit()

        # transaction result dialog
        self.transaction_result = dialogs.TransactionResult(self)

    def set_working(self, state, insensitive=False):
        """Set the working state."""
        self.is_working = state

    def _check_cache_expired(self, cache_type):
        time_fmt = '%Y-%m-%d %H:%M'
        now = datetime.datetime.now()
        refresh_period = datetime.timedelta(hours=CONFIG.conf.refresh_interval)
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

    @ExceptionHandler
    def get_root_backend(self):
        """Get the current root backend.

        if it is not setup yet, the create it
        if it is not locked, then lock it
        """
        if self._root_backend is None:
            self._root_backend = yumex.dnf_backend.DnfRootBackend(self)
        if self._root_locked is False:
            locked, msg = self._root_backend.setup()
            if locked:
                self._root_locked = True
                logger.debug('Lock the Dnf root daemon')
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
                        'Dnf root backend was not authorized\n'
                        ' Yum Extender will exit')
                # Dnf is locked by another process
                elif msg == 'locked-by-other':
                    errmsg = _(
                        'Dnf  is locked by another process \n\n'
                        'Yum Extender will exit')
                dialogs.show_information(self, errmsg)
                # close down and exit yum extender
                self.status.SetWorking(False)  # reset working state
                self.status.SetYumexIsRunning(False)
                sys.exit(1)
        return self._root_backend

    @ExceptionHandler
    def release_root_backend(self, quit=False):
        """Release the current root backend, if it is setup and locked."""
        if self._root_backend is None:
            return
        if self._root_locked is True:
            logger.debug('Unlock the Dnf root daemon')
            self._root_backend.Unlock()
            self._root_locked = False
        if quit:
            logger.debug('Exit the Dnf root daemon')
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
            errmsg = 'DNF is locked by another process \n'
            '\nYum Extender will exit'
            close = False
        elif err == 'NoReply':
            errmsg = 'DNF Dbus backend is not responding \n'
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
        self.status.SetWorking(False)  # reset working state
        self.status.SetYumexIsRunning(False)
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


class YumexInstallWindow(BaseWindow):
    """Simple ui windows class for doing actions from the command line."""
    def __init__(self, app, status):
        BaseWindow.__init__(self, app, status)
        self.set_default_size(600, 80)

        # Setup the main window ui
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)
        # infobar revealer
        infobar = self.ui.get_object('infobar')
        vbox.pack_start(infobar, False, False, 0)
        self.add(vbox)
        vbox.show()
        self.infobar = yumex.gui.widgets.InfoProgressBar(self.ui)
        self.infobar.show_all()
        info_spinner = self.ui.get_object('info_spinner')
        info_spinner.set_from_file(const.PIX_DIR + '/spinner-small.gif')
        self.system_backend_refreshed = True  # dont refresh metadata

    def on_delete_event(self, *args):
        if CONFIG.conf.hide_on_close or self.is_working:
            self.hide()
            return True
        else:
            self.app.on_quit()

    @ExceptionHandler
    def process_actions(self, action, package, always_yes):
        """Process the pending actions from the command line.

        :param action: action to perform (install/remove)
        :param package: package to work on
        :param always_yes: ask the user or default to yes/ok to all questions
        """
        self.status.SetWorking(True)
        if action == 'install':
            self.infobar.info(_('Installing package : %s') % package)
            self.infobar.info_sub(package)
            txmbrs = self.backend.Install(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
        elif action == 'remove':
            self.infobar.info(_('Removing package : %s') % package)
            self.infobar.info_sub(package)
            txmbrs = self.backend.Remove(package)
            logger.debug('txmbrs: %s' % str(txmbrs))
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
                if not always_yes:
                    dialogs.show_information(
                        self,
                        _('Changes was successfully applied to the system'))
        else:
            dialogs.show_information(
                self, _('Error(s) in search for dependencies'),
                        '\n'.join(result))
        self.release_root_backend(quit=True)
        self.status.SetWorking(False)
        self.app.quit()


class YumexHeaderBar(Gtk.HeaderBar):
    """Header bar for main window."""
    # TODO: move to gui.widget
    def __init__(self, ui):
        Gtk.HeaderBar.__init__(self)
        self.props.show_close_button = True
        self.ui = ui
        self.pack_start(self.ui.get_object('header_start'))
        self.pack_end(self.ui.get_object('header_end'))
        self.ui.get_object('header_menu').set_popup(
            self.ui.get_object('main_menu'))
        self.ui.get_object('header_search_options').set_popup(
            self.ui.get_object('search_menu'))
        self.ui.get_object('header_filters').set_popup(
            self.ui.get_object('menu_filters'))


class YumexToolBar(Gtk.Box):
    """Header bar for main window."""
    # TODO: move to gui.widget
    def __init__(self, ui):
        Gtk.Box.__init__(self)
        self.props.orientation = Gtk.Orientation.HORIZONTAL
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.ui = ui
        self.pack_start(self.ui.get_object('header_start'), True, True, 0)
        self.pack_end(self.ui.get_object('header_end'), False, False, 0)
        self.ui.get_object('header_menu').set_popup(
            self.ui.get_object('main_menu'))
        self.ui.get_object('header_search_options').set_popup(
            self.ui.get_object('search_menu'))
        self.ui.get_object('header_filters').set_popup(
            self.ui.get_object('menu_filters'))


class YumexWindow(BaseWindow):
    """Main application window class."""
    def __init__(self, app, status):
        BaseWindow.__init__(self, app, status)
        self.set_default_size(1024, 700)

        screen = Gdk.Screen.get_default()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(const.DATA_DIR + '/gtk-style.css')
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_USER)
        # init vars
        self.last_search = None
        self.current_filter = None
        self._root_backend = None
        self._root_locked = False
        self.search_type = 'prefix'
        self.last_search_pkgs = []
        self.current_filter_search = None
        self.active_archs = const.PLATFORM_ARCH
        self._grps = None   # Group and Category cache
        self.active_page = None  # Active content page

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # setup the main gui
        if CONFIG.conf.headerbar:
            self.hb = YumexHeaderBar(self.ui)
            self.set_titlebar(self.hb)
            self.hb.show()
        else:
            toolbar = YumexToolBar(self.ui)
            toolbar.show()
            vbox.pack_start(toolbar, False, False, 0)

        # Setup the main window ui
        self.add(vbox)
        # infobar revealer
        infobar = self.ui.get_object('infobar')
        vbox.pack_start(infobar, False, False, 0)
        # content Stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(500)
        for name in ['packages', 'groups', 'history', 'queue']:
            page = self.ui.get_object('page_%s' % name)
            self.stack.add_named(page, name)
        vbox.pack_start(self.stack, True, True, 0)
        self.stack.show()
        vbox.show()
        self.add_accel_group(self.ui.get_object('main_accelgroup'))

        # Setup package filters
        for name in ['updates', 'installed', 'available', 'all']:
            rb = self.ui.get_object('filter_' + name)
            rb.connect('toggled', self.on_pkg_filter, name)

        # Connect menu radio buttons to handler
        for name in ['newest_only', 'clean_unused']:
            rb = self.ui.get_object('option_' + name)
            rb.set_active(getattr(CONFIG.session, name))
            rb.connect('toggled', self.on_options, name)

        # build the search_conf widget
        # Connect menu radio buttons to handler
        # setup search type option
        for key in ['prefix', 'key', 'fields']:
            wid = self.ui.get_object('search_%s' % key)
            if key == self.search_type:
                wid.set_active(True)
            wid.connect('toggled', self.on_search_config, key)

        self.search_fields = ['name', 'summary']
        self.set_fields_active(False)

        # setup search fields
        for field in ['name', 'summary', 'description']:
            wid = self.ui.get_object('field_%s' % field)
            if field in self.search_fields:
                wid.set_active(True)
            else:
                wid.set_active(False)
            wid.connect('toggled', self.on_search_field, field)

        # Setup search entry
        self.search_entry = self.ui.get_object('search')
        self.search_entry.connect('activate', self.on_search_changed)
        self.search_entry.connect('icon-press', self.on_search_icon)

        # setup the package/queue/history views
        self.setup_main_content()

        # spinner
        self.spinner = self.ui.get_object('progress_spinner')
        self.info_spinner = self.ui.get_object('info_spinner')
        self.info_spinner.set_from_file(const.PIX_DIR + '/spinner-small.gif')
        self.spinner.hide()

        # infobar
        self.infobar = yumex.gui.widgets.InfoProgressBar(self.ui)
        self.infobar.hide()

        # preferences dialog

        self.preferences = dialogs.Preferences(self)

        # setup actions

        wid = self.ui.get_object('main_pref')
        wid.connect('activate', self.on_pref)
        wid = self.ui.get_object('main_packages')
        wid.set_active(True)
        wid.connect('activate', self.on_packages)
        wid = self.ui.get_object('main_groups')
        wid.connect('activate', self.on_groups)
        wid = self.ui.get_object('main_actions')
        wid.connect('activate', self.on_queue)
        wid = self.ui.get_object('main_history')
        wid.connect('activate', self.on_history)
        wid = self.ui.get_object('main_about')
        wid.connect('activate', self.on_about)
        wid = self.ui.get_object('main_doc')
        wid.connect('activate', self.on_docs)
        wid = self.ui.get_object('header_execute')
        wid.connect('clicked', self.on_apply_changes)

        self.show_now()

        # setup the package manager backend
        # get the default enabled repos
        CONFIG.session.enabled_repos = self.backend.get_repo_ids('enabled')

        # get the arch filter
        self.arch_filter = self.backend.get_filter('arch')
        self.arch_filter.set_active(True)
        self.arch_filter.change(self.active_archs)

        # setup default selections
        self.ui.get_object('filter_updates').set_active(True)
        # self.ui.get_object('search_keyword').set_active(True)

    def set_fields_active(self, state=True):
        """Set search fields active/inactive."""
        for field in ['name', 'summary', 'description']:
            wid = self.ui.get_object('field_%s' % field)
            wid.set_sensitive(state)

    def on_delete_event(self, *args):
        if CONFIG.conf.hide_on_close or self.is_working:
            self.hide()
            return True
        else:
            self.app.on_quit()

    def _is_url(self, url):
        """Check for a legal web URL."""
        urls = re.findall(
            '^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]'
            '|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url)
        if urls:
            return True
        else:
            return False

    def _open_url(self, url):
        """Open URL in default browser."""
        if self._is_url(url):  # just to be sure and prevent shell injection
            rc = subprocess.call('xdg-open %s' % url, shell=True)
            # failover to gtk.show_uri, if xdg-open fails or is not installed
            if rc != 0:
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            dialogs.show_information('%s is not an url' % url)

    def on_about(self, widget):
        """ Main Menu: Help -> About """
        dialog = dialogs.AboutDialog()
        dialog.run()
        dialog.destroy()

    def on_docs(self, widget):
        """ Main Menu: Help -> Documentation"""
        self._open_url('http://yumex-dnf.readthedocs.org/en/latest/')
        pass

    def on_search_field(self, widget, field):
        if widget.get_active():
            if not field in self.search_fields:
                self.search_fields.append(field)
        else:
            if field in self.search_fields:
                self.search_fields.remove(field)
        print(self.search_fields)

    def on_status_icon_clicked(self, force=False):
        """Left click on statusicon callback.

        hide/show the window, based on current state
        """
        if force:
            self.present()
        elif self.get_property('visible'):
            self.hide()
        else:
            self.show()

    def setup_main_content(self):
        """Setup the main content

        Setup the package, history and queue views pages
        """
        # Package Page
        queue_menu = self.ui.get_object('queue_menu')
        self.queue_view = views.QueueView(queue_menu)
        arch_menu_widget = self.ui.get_object('arch_menu')
        self.arch_menu = yumex.gui.widgets.ArchMenu(arch_menu_widget,
                                                    self.active_archs)
        self.arch_menu.connect('arch-changed', self.on_arch_changed)
        self.package_view = views.PackageView(self.queue_view, self.arch_menu)
        self.package_view.connect(
            'pkg_changed', self.on_pkg_view_selection_changed)
        sw = self.ui.get_object('package_sw')
        sw.add(self.package_view)
        # setup info view
        info = self.ui.get_object('info_box')
        self.info = yumex.gui.widgets.PackageInfo(self, self)
        info.pack_start(self.info, True, True, 0)
        self.info.show_all()
        # Queue Page
        sw = self.ui.get_object('queue_sw')
        sw.add(self.queue_view)
        # History Page
        sw = self.ui.get_object('history_sw')
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.history_view = views.HistoryView(self)
        hb.pack_start(self.history_view, False, False, 0)
        hb.pack_start(self.history_view.pkg_view, True, True, 0)
        sw.add(hb)
        # Groups
        sw = self.ui.get_object('groups_sw')
        hb = Gtk.Box()
        hb.set_direction(Gtk.Orientation.HORIZONTAL)
        self.groups = views.GroupView(self.queue_view, self)
        self.groups.connect('group-changed', self.on_group_changed)
        #hb.pack_start(self.groups, True, True, 0)
        # sw.add(hb)
        sw.add(self.groups)
        sw = self.ui.get_object('group_pkg_sw')
        self.group_package_view = views.PackageView(
            self.queue_view, self.arch_menu, group_mode=True)
        #self.group_package_view.connect('arch-changed', self.on_arch_changed)
        self.group_package_view.connect(
            'pkg_changed', self.on_group_pkg_view_selection_changed)
        sw.add(self.group_package_view)
        info = self.ui.get_object('group_pkg_info_sw')
        self.group_info = yumex.gui.widgets.PackageInfo(self, self)
        info.add(self.group_info)
        self.info.show_all()
        self.stack.show_all()

    def set_content_page(self, page):
        """Set the visible content page.

        :param page: active page (PAGE_PACKAGES, PAGE_QUEUE, PAGE_HISTORY)
        """
        self.active_page = page
        self.stack.set_visible_child_name(page)

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
        self.status.SetWorking(False)  # reset working state
        self.status.SetYumexIsRunning(False)
        Gtk.main_quit()
        sys.exit(1)

    def set_working(self, state, insensitive=False):
        """Set the working state.

        - show/hide the progress spinner
        - show busy/normal mousepointer
        - make gui insensitive/sensitive
        - set/unset the woring state in the status icon
        based on the state.
        """
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
        """Check for updates in status icon callback."""
        self.backend.reload()  # Reload backend
        widget = self.ui.get_object('filter_updates')
        if widget.get_active():
            self.on_pkg_filter(widget, 'updates')
        else:
            self.ui.get_object('filter_updates').set_active(True)

    def _set_busy_cursor(self, insensitive=False):
        """Set busy cursor in main window and
        make it insensitive if selected.
        """
        win = self.get_window()
        if win is not None:
            win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
            if insensitive:
                for widget in const.WIDGETS_INSENSITIVE:
                        self.ui.get_object(widget).set_sensitive(False)
                self.stack.set_sensitive(False)
        doGtkEvents()

    def _set_normal_cursor(self):
        """Set Normal cursor in main window and make it sensitive."""
        win = self.get_window()
        if win is not None:
            win.set_cursor(None)
            for widget in const.WIDGETS_INSENSITIVE:
                self.ui.get_object(widget).set_sensitive(True)
            self.stack.set_sensitive(True)
        doGtkEvents()

#
# Callback handlers
#

    def on_pkg_view_selection_changed(self, widget, pkg):
        """Package selected in the view callback."""
        self.info.set_package(pkg)

    def on_group_pkg_view_selection_changed(self, widget, pkg):
        """Package selected in the group view callback."""
        self.group_info.set_package(pkg)

    def on_packages(self, action, data=None):
        """Switching to package page callback."""
        self.set_content_page(const.PAGE_PACKAGES)
        self.hide_search_buttons(hide=False)

    def set_search_focus(self):
        """Set focus on search entry and move cursor to end of text."""
        self.search_entry.grab_focus()
        self.search_entry.emit(
            'move-cursor', Gtk.MovementStep.BUFFER_ENDS, 1, False)

    def on_search_config(self, widget, data):
        """Search config callback."""
        self.search_type = data
        if data == 'fields':
            self.set_fields_active(True)
        else:
            self.set_fields_active(False)
        if self.last_search:
            self.last_search = None
            # send an active signal from the search entry & grap focus & place
            # cursor
            self.search_entry.emit('activate')
            self.set_search_focus()

    def on_pkg_filter(self, widget, data):
        """Switching package filter callback."""
        if widget.get_active():
            self.on_packages(None, None)
            if data in ['installed', 'available', 'updates', 'all']:
                self.infobar.info(const.PACKAGE_LOAD_MSG[data])
                self.set_working(True, True)
                if self.last_search:  # we are searching
                    self.current_filter_search = (widget, data)
                    pkgs = self.filter_search_pkgs(data)
                else:  # normal package filter
                    self.current_filter = (widget, data)
                    pkgs = self.backend.get_packages(data)
                    if data == 'updates':
                        #obs_pkgs = self.backend.get_packages('obsoletes')
                        #pkgs.extend(obs_pkgs)
                        self.status.SetUpdateCount(len(pkgs))
                self.info.set_package(None)
                self.infobar.info(_('Adding packages to view'))
                self.package_view.populate(pkgs)
                self.set_working(False)
                self.infobar.hide()
                if data == 'updates':
                    self.package_view.set_header_click(True)
                else:
                    self.package_view.set_header_click(False)
                self.set_search_focus()

    def on_arch_changed(self, widget, data):
        """Arch changed in arch menu callback."""
        self.active_archs = data.split(',')
        logger.debug('arch-changed : %s' % self.active_archs)
        if self.last_search:
            data = self.last_search
            self.last_search = None
            self.on_search_changed(self.search_entry, data)
        elif self.active_page == const.PAGE_PACKAGES and self.current_filter:
            widget, flt = self.current_filter
            self.on_pkg_filter(widget, flt)

    def on_search_icon(self, widget, icon_pos, event):
        """Search entry callback."""
        #print(icon_pos)
        # clear icon pressed
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            widget.set_text('')
            widget.emit('activate')

    def on_search_changed(self, widget):
        """Search entry callback."""
        data = widget.get_text()
        if data == '':  # revert to the current selected filter
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
            if self.search_type == 'key':
                flt = '*%s*'
                self._search_name(data, flt)
            elif self.search_type == 'prefix':
                flt = '%s*'
                self._search_name(data, flt)
            elif self.search_type == 'fields':
                self._search_keys(self.search_fields, data)

    def filter_search_pkgs(self, flt):
        """Get filtered search results.

        :param flt: filter (updates, install or all)
        """
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

    def _search_name(self, data, search_flt):
        """Search package name for keyword with wildcards."""
        # only search for word larger than 3 chars
        if len(data) >= 3 and data != self.last_search:
            self.last_search = data
            self.set_working(True)
            newest_only = CONFIG.session.newest_only
            self.last_search_pkgs = self.backend.get_packages_by_name(
                search_flt % data, newest_only)
            logger.debug('Packages found : %d' % len(self.last_search_pkgs))
            self.info.set_package(None)
            self.set_working(False)
            if self.current_filter_search:
                widget, flt = self.current_filter_search
                self.on_pkg_filter(widget, flt)
            else:
                self._set_available_active()

    def _search_keys(self, fields, data):
        """Search given package attributes for given keywords."""
        self.last_search = data
        self.set_working(True, True)
        newest_only = CONFIG.session.newest_only
        self.last_search_pkgs = self.backend.search(
            fields, data.split(' '), True, newest_only, True)
        self.on_packages(None, None)  # switch to package view
        self.info.set_package(None)
        self.set_working(False)
        if self.current_filter_search:
            widget, flt = self.current_filter_search
            self.on_pkg_filter(widget, flt)
        else:
            self._set_available_active()

    def _set_available_active(self):
        """Make the 'available' filter active, by selecting 'updates' and
        the back to 'available'"""
        widget = self.ui.get_object('filter_updates')
        widget.set_active(True)
        widget = self.ui.get_object('filter_all')
        widget.set_active(True)

    def on_groups(self, widget):
        """Group page selected callback."""
        if widget.get_active():
            self.set_content_page(const.PAGE_GROUPS)
            self.hide_search_buttons()
            if not self._grps:
                logger.debug('getting group and categories')
                self._grps = self.backend.get_groups()
                self.groups.populate(self._grps)

    def on_group_changed(self, widget, grp_id):
        """ Group changed callback

        called when a new group is selected and the group package view
        shall be updated with the packages in the group

        :param widget:
        :param grp_id: group id to show packages for.
        """
        logger.debug('on_group_changed : %s ' % grp_id)
        self.set_working(True, True)
        pkgs = self.backend.get_group_packages(grp_id, 'all')
        self.group_package_view.populate(pkgs)
        self.set_working(False)

    def hide_search_buttons(self, hide=True):
        """Hide search releated button, only shown on package page."""
        for widget in ['header_filters', 'header_search_options', 'search']:
                self.ui.get_object(widget).set_sensitive(not hide)

    def on_history(self, widget):
        """History page selected callback"""
        if widget.get_active():
            if not self.history_view.is_populated:
                result = self.backend.GetHistoryByDays(
                    0, CONFIG.conf.history_days)
                self.history_view.populate(result)
            self.set_content_page(const.PAGE_HISTORY)
            self.hide_search_buttons()
        else:
            self.release_root_backend()

    def on_queue(self, widget):
        """Queue page selected callback."""
        if widget.get_active():
            self.set_content_page(const.PAGE_QUEUE)
            self.hide_search_buttons()

    def on_info(self, action, parameter):
        """Package info page radiobuttons callback."""
        widget = self.ui.get_object(action.get_name())
        if widget.get_active():
            self.info.clear()
            self.info.write(action.get_name())

    def on_apply_changes(self, widget):
        """Apply Changes button callback."""
        self.process_actions()

    def on_options(self, widget, parameter):
        """Options menu callback.

        Set the CONFIG parameter values based on the menu checkbox states
        """
        state = widget.get_active()
        setattr(CONFIG.session, parameter, state)
        logger.debug('Option : %s = %s' %
                     (parameter, getattr(CONFIG.session, parameter)))

    def on_pref(self, widget):
        """Preferences selected callback."""

        need_reset = self.preferences.run()
        if need_reset:
            self.reset()

    @ExceptionHandler
    def process_actions(self):
        """Process the current actions in the queue.

        - setup the Dnf transaction
        - resolve dependencies
        - ask user for confirmation on result of depsolve
        - run the transaction
        """
        if self.queue_view.queue.total() == 0:
            dialogs.show_information(self, _('No pending actions in queue'))
            return
        self.set_working(True, True)
        # switch to queue view
        # switch to package page
        widget = self.ui.get_object('main_actions')
        widget.set_active(True)
        self.set_content_page(const.PAGE_QUEUE)
        self.infobar.info(_('Preparing system for applying changes'))
        self.backend.ClearTransaction()
        errors = 0
        error_msgs = set()
        for action in const.QUEUE_PACKAGE_TYPES:
            pkgs = self.queue_view.queue.get(action)
            for pkg in pkgs:
                if action == 'do':
                    logger.debug('adding : %s %s' %
                                 (action, pkg.downgrade_po.pkg_id))
                    rc, trans = self.backend.AddTransaction(
                        pkg.downgrade_po.pkg_id,
                        const.QUEUE_PACKAGE_TYPES[action])
                    logger.debug('%s: %s' % (rc, trans))
                    if not rc:
                        errors += 1
                        error_msgs |= set(trans)
                else:
                    logger.debug('adding : %s %s' % (action, pkg.pkg_id))
                    rc, trans = self.backend.AddTransaction(
                        pkg.pkg_id, const.QUEUE_PACKAGE_TYPES[action])
                    logger.debug('%s: %s' % (rc, trans))
                    if not rc:
                        errors += 1
                        error_msgs |= set(trans)
        for grp_id, action in self.queue_view.queue.get_groups():
            if action == 'i':
                rc, trans = self.backend.GroupInstall(grp_id)
            else:
                rc, trans = self.backend.GroupRemove(grp_id)
            logger.debug('%s: %s' % (rc, trans))
            if not rc:
                errors += 1
                error_msgs |= set(trans)

        if not errors:
            self.backend.GetTransaction()
            self.infobar.info(_('Searching for dependencies'))
            rc, result = self.backend.BuildTransaction()
            self.infobar.info(_('Dependencies resolved'))
            self.set_working(False)
            if rc:
                self.transaction_result.populate(result, '')
                ok = self.transaction_result.run()
                if ok:  # Ok pressed
                    self.infobar.info(_('Applying changes to the system'))
                    self.set_working(True, True)
                    rc, result = self.backend.RunTransaction(
                        max_err=CONFIG.conf.max_dnl_errors)
                    # This can happen more than once (more gpg keys to be
                    # imported)
                    while rc == 1:
                        # get info about gpgkey to be comfirmed
                        values = self.backend._gpg_confirm
                        (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
                        logger.debug('GPGKey : %s' % repr(values))
                        ok = yumex.gui.widgets.ask_for_gpg_import(self, values)
                        if ok:
                            # tell the backend that the gpg key is confirmed
                            self.backend.ConfirmGPGImport(hexkeyid, True)
                            rc, result = self.backend.RunTransaction(
                                max_err=CONFIG.conf.max_dnl_errors)
                        else:
                            break
                    if rc == 4:  # Download errors
                        dialogs.show_information(
                            self, _('Downloading error(s)\n'),
                                     '\n'.join(result))
                    self.reset()
                    return
                else:  # user cancelled transaction
                    self.reset_on_cancel()
                    return
            else:  # error in depsolve
                dialogs.show_information(
                    self, _('Error(s) in search for dependencies'),
                            '\n'.join(result))
        else:  # error in population of the transaction
            dialogs.show_information(
                self, _('Error(s) in search for dependencies'),
                        '\n'.join(error_msgs))
        self.reset_on_error()

    def reset_on_cancel(self):
        """Reset gui on user cancel"""
        self.set_working(True)
        self.infobar.hide()
        self.set_working(False)

    def reset_on_error(self):
        """Reset gui on transaction errors."""
        self.set_working(True)
        self.infobar.hide()
        self.release_root_backend()
        self.set_working(False)

    @ExceptionHandler
    def reset(self):
        """Reset the gui to inital state.

        Used after a transaction is completted.
        """
        self.set_working(True)
        self.infobar.hide()
        self.release_root_backend()
        self.backend.reload()
        # clear the package queue
        self.queue_view.queue.clear()
        self.queue_view.refresh()
        # clear search entry
        self.last_search = None
        self.current_filter_search = None
        self.search_entry.set_text('')
        # reset groups
        self._grps = self.backend.get_groups()
        self.groups.populate(self._grps)
        self.group_package_view.populate([])
        self.set_working(False)
        # switch to package page
        widget = self.ui.get_object('main_packages')
        widget.set_active(True)
        self.set_content_page(const.PAGE_PACKAGES)
        # show updates
        widget = self.ui.get_object('filter_updates')
        widget.set_active(True)
        self.on_pkg_filter(widget, 'updates')


class YumexApplication(Gtk.Application):
    """Main Gtk.Application class."""

    def __init__(self):
        Gtk.Application.__init__(
            self, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.args = None
        self.status = None

    def do_activate(self):
        """Gtk.Application activate callback."""
        logger.debug('do_activate')
        if self.args.install:
            self.install = YumexInstallWindow(self, self.status)
            self.install.show()
            self.install.process_actions(
                'install', self.args.install, self.args.yes)
        elif self.args.remove:
            self.install = YumexInstallWindow(self, self.status)
            self.install.show()
            self.install.process_actions(
                'remove', self.args.remove, self.args.yes)
        else:
            self.win = YumexWindow(self, self.status)
            self.win.connect('delete_event', self.on_quit)
            self.win.show()

    def do_startup(self):
        """Gtk.Application startup callback."""
        logger.debug('do_startup')
        Gtk.Application.do_startup(self)
        # Setup actions
        self._create_action('quit', self.on_quit)

    def _create_action(self, name, callback, para=None):
        """Create and Gio.Action and connect it to a callback handler
        handles app.<name> actions defined in GtkBuilder ui file.
        """
        action = Gio.SimpleAction.new(name, para)
        action.connect('activate', callback)
        self.add_action(action)

    def on_quit(self, action=None, parameter=None):
        """Quit callback."""
        # If we quit from the StatusIcon, then quit the status icon also
        if action is None:
            self.keep_icon_running = False
        self.quit()  # quit the application

    def do_command_line(self, args):
        """Gtk.Application command line callback.

        Called if Gio.ApplicationFlags.HANDLES_COMMAND_LINE is set.
        must call the self.do_activate() to get the application up and running.
        """
        Gtk.Application.do_command_line(self, args)
        parser = argparse.ArgumentParser(prog='yumex')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument(
            '-y', '--yes', action='store_true',
             help='Answer yes/ok to all questions')
        parser.add_argument(
            '--icononly', action='store_true',
            help='Start only the status icon')
        parser.add_argument('--exit', action='store_true',
            help='tell session dbus services used by yumex to exit')
        parser.add_argument(
            '-I', '--install', type=str, metavar='PACKAGE',
            help='Install Package')
        parser.add_argument(
            '-R', '--remove', type=str, metavar='PACKAGE',
            help='Remove Package')
        self.args = parser.parse_args(args.get_arguments()[1:])
        if self.args.debug:
            self.doTextLoggerSetup(loglvl=logging.DEBUG)
            # setup log handler for yumdaemon API
            self.doTextLoggerSetup(
                logroot='yumdaemon',
                logfmt='%(asctime)s: [%(name)s] - %(message)s',
                loglvl=logging.DEBUG)
        else:
            self.doTextLoggerSetup()
        logger.debug('cmdline : %s ' % repr(self.args))
        if self.args.exit:
            subprocess.call(
                '/usr/bin/dbus-send --session --print-reply '
                '--dest=dk.yumex.StatusIcon / dk.yumex.StatusIcon.Exit',
                shell=True)
            subprocess.call(
                '/usr/bin/dbus-send --system --print-reply '
                '--dest=org.baseurl.DnfSystem / org.baseurl.DnfSystem.Exit',
                shell=True)
            sys.exit(0)
        # Start the StatusIcon dbus client
        self.status = yumex.status.StatusIcon(self)
        self.status.Start()  # Show the icon
        if self.args.icononly:  # Only start the icon and exit
            sys.exit(0)
        # Check if yumex is running already
        if self.status.SetYumexIsRunning(True):
            self.do_activate()
        else:
            if dialogs.yes_no_dialog(None, 'Yum Extender is already running',
                                        'Do you want to kill it'):
                if not self.status.GetYumexIsWorking():
                    self.status.QuitYumex()
                    subprocess.call(
                    '/usr/bin/dbus-send --system --print-reply '
                    '--dest=org.baseurl.DnfSystem / org.baseurl.DnfSystem.Exit',
                    shell=True)
                else:  # not safe to kill yumex, when it is working
                    self.status.ShowYumex()
            else:
                self.status.ShowYumex()
            sys.exit(1)
        return 0

    def do_shutdown(self):
        """Gtk.Application shutdown callback.

        Do clean up before the application is closed.
        """
        Gtk.Application.do_shutdown(self)
        if self.status:
            self.status.SetYumexIsRunning(False)
            if not CONFIG.conf.autostart and not CONFIG.conf.autocheck_updates:
                self.status.Exit()
        # if windows object exist, unlock and exit backends
        if hasattr(self, 'win'):
            self.win.release_root_backend(quit=True)

    def doTextLoggerSetup(self, logroot='yumex',
                          logfmt='%(asctime)s: %(message)s',
                          loglvl=logging.INFO):
        """Setup Python logging."""
        logger = logging.getLogger(logroot)
        logger.setLevel(loglvl)
        formatter = logging.Formatter(logfmt, '%H:%M:%S')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.propagate = False
        logger.addHandler(handler)

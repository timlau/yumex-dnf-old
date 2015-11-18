#!/usr/bin/python3
# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A GUI for yum
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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

from configparser import SafeConfigParser
from gi.repository import Gtk, GObject, GdkPixbuf, Notify
from subprocess import Popen
from xdg import BaseDirectory

import argparse
import cairo
import dnfdaemon.client
import dbus
import dbus.service
import dbus.mainloop.glib
import gettext
import logging
import os
import os.path
import random
import sys
import time

api_version = 1  # must be integer

DAEMON_ORG = 'dk.yumex.StatusIcon'
DAEMON_INTERFACE = DAEMON_ORG
LOG_ROOT = 'yumex-statusicon'

logger = logging.getLogger(LOG_ROOT)
gettext.bindtextdomain('yumex-dnf')
gettext.textdomain('yumex-dnf')
_ = gettext.gettext
P_ = gettext.ngettext


BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

if BIN_PATH in ['/usr/share/yumex-dnf']:
    DATA_DIR = '/usr/share/yumex-dnf'
    PIX_DIR = DATA_DIR + '/gfx'
    MISC_DIR = DATA_DIR
    YUMEX_BIN = '/usr/bin/yumex-dnf'
else:
    DATA_DIR = BIN_PATH
    PIX_DIR = DATA_DIR + '/../gfx'
    MISC_DIR = DATA_DIR + '/../misc'
    YUMEX_BIN = '../src/main.py'

ICON_TRAY_ERROR = PIX_DIR + '/tray-error.png'
ICON_TRAY_NO_UPDATES = PIX_DIR + '/tray-no-updates.png'
ICON_TRAY_UPDATES = PIX_DIR + '/tray-updates.png'
ICON_TRAY_WORKING = PIX_DIR + '/tray-working.png'
ICON_TRAY_INFO = PIX_DIR + '/tray-info.png'

CONF_DIR = BaseDirectory.save_config_path('yumex-dnf')
CONF_FILE = os.path.join(CONF_DIR, 'yumex.conf')
TIMESTAMP_FILE = os.path.join(CONF_DIR, 'update_timestamp.conf')
TIMER_STARTUP_DELAY = 30
UPDATE_INTERVAL = 5

# Setup configs
# every 60 minutes, start delay = 30 seconds
CONF_DEFAULTS = {
    'update_interval': '60',
    'update_startup_delay': '30',
    'autocheck_updates': '0',
    'update_notify': True,
    'update_showicon': True
    }

CONFIG = SafeConfigParser(CONF_DEFAULTS)
if not CONFIG.has_section('yumex'):
    CONFIG.add_section('yumex')
if os.path.exists(CONF_FILE):
    CONFIG.read(CONF_FILE)


TIMER_STARTUP_DELAY = CONFIG.getint('yumex', 'update_startup_delay')
UPDATE_INTERVAL = CONFIG.getint('yumex', 'update_interval')
AUTOCHECK_UPDATE = CONFIG.getboolean('yumex', 'autocheck_updates')
NOTIFY = CONFIG.getboolean('yumex', 'update_notify')
SHOWICON = CONFIG.getboolean('yumex', 'update_showicon')


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


class UpdateTimestamp:

    '''
    a persistent timestamp. eg for storing the last update check
    '''

    def __init__(self, file_name=TIMESTAMP_FILE):
        self.time_file = file_name
        self.last_time = -1

    def get_last_time_diff(self):
        '''
        returns time difference to last check in seconds >=0 or -1 on error
        '''
        try:
            t = int(time.time())
            if self.last_time == -1:
                f = open(self.time_file, 'r')
                t_old = int(f.read())
                f.close()
                self.last_time = t_old
            if self.last_time > t:
                return -1
            return t - self.last_time
        except:
            pass
        return -1

    def store_current_time(self):
        t = int(time.time())
        f = open(self.time_file, 'w')
        f.write(str(t))
        f.close()
        self.last_time = t


def Logger(func):
    '''
    This decorator catch yum exceptions and send fatal signal to frontend
    '''
    def newFunc(*args, **kwargs):
        logger.debug('%s started args: %s ' % (func.__name__, repr(args[1:])))
        rc = func(*args, **kwargs)
        logger.debug('%s ended' % func.__name__)
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc


class Notification(GObject.GObject):
    __gsignals__ = {
        'notify-action': (GObject.SIGNAL_RUN_FIRST, None,
                      (str,))
    }

    def __init__(self, summary, body):
        GObject.GObject.__init__(self)
        Notify.init('Yum Extender')
        icon = "yumex-dnf"
        self.notification = Notify.Notification.new(summary, body, icon)
        self.notification.set_timeout(10000)  # timeout 10s
        self.notification.add_action('open', _('Open Yum Extender'),
                                     self.callback)
        self.notification.add_action('apply', _('Apply Updates'), self.callback)
        self.notification.connect('closed', self.on_closed)

    def show(self):
        self.notification.show()

    def callback(self, widget, action):
        self.emit('notify-action', action)

    def on_closed(self, widget):
        self.emit('notify-action', 'closed')


def error_notify(summary, body):
    Notify.init('Yum Extender')
    icon = "yumex-dnf"
    notification = Notify.Notification.new(summary, body, icon)
    notification.set_timeout(5000)  # timeout 5s
    notification.show()


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

        self.quit_menu = Gtk.MenuItem(_('Quit'))
        self.search_updates_menu = Gtk.MenuItem(_('Search for Updates'))
        self.run_yumex = Gtk.MenuItem(_('Start Yum Extender'))

        menu.append(self.search_updates_menu)
        menu.append(self.run_yumex)
        menu.append(self.quit_menu)
        menu.show_all()
        self.statusicon.connect('popup-menu', self.on_popup)

    def set_popup_menu_sensitivity(self, sensitive):
        self.quit_menu.set_sensitive(sensitive)
        self.search_updates_menu.set_sensitive(sensitive)
        self.run_yumex.set_sensitive(sensitive)

    def on_popup(self, icon, button, time):
        self.popup_menu.popup(None, None, self.statusicon.position_menu, self.statusicon, button, time)

    def get_status_icon(self):
        return self.statusicon

    def update_tray_icon(self):
        self.statusicon.set_visible(True)
        if self.need_input:
            self.statusicon.set_tooltip_text(_('Yum Extender: Need user input'))
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_info)
            self.set_popup_menu_sensitivity(False)
        elif self.is_working > 0:
            self.statusicon.set_tooltip_text(_('Yum Extender: Working'))
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_checking)
            self.set_popup_menu_sensitivity(False)
            if not SHOWICON:
                self.statusicon.set_visible(False)
        else:
            self.set_popup_menu_sensitivity(True)
            update_count = self.update_count
            if update_count == -2:
                self.statusicon.set_tooltip_text(_('Yum Extender'))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
                if not SHOWICON:
                    self.statusicon.set_visible(False)
            elif update_count == -1:
                self.statusicon.set_tooltip_text(_('Yum Extender: Error'))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_error)
            elif update_count == 0:
                self.statusicon.set_tooltip_text(_('Yum Extender: No updates'))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
                if not SHOWICON:
                    self.statusicon.set_visible(False)
            else:
                self.statusicon.set_tooltip_text(
                    _('Yum Extender: %s updates available') % update_count)
                pixbuf = self.get_pixbuf_with_text(
                    self.image_updates, str(update_count), self.rel_font_size)
        self.statusicon.set_from_pixbuf(pixbuf)
        Gtk.main_iteration()

    # png_file must be a squared image
    def get_pixbuf_with_text(self, png_file, text, relative_font_size):
        img = cairo.ImageSurface.create_from_png(png_file)
        size = img.get_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        ctx.set_source_surface(img, 0, 0)
        ctx.paint()

        font_size = size * relative_font_size
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        # resize font size until text fits ...
        while font_size > 1.0:
            ctx.set_font_size(int(font_size))
            ctx.select_font_face('Sans', cairo.FONT_SLANT_NORMAL,
                                 cairo.FONT_WEIGHT_BOLD)
            [bearing_x, bearing_y, font_x, font_y, ax, ay] =\
                ctx.text_extents(text)
            if font_x < size:
                break
            font_size = font_size * 0.9
        ctx.move_to(int(size - font_x) / 2 - bearing_x,
                    int(size - font_y) / 2 - bearing_y)
        ctx.show_text(text)
        ctx.stroke()

        # this is ugly but the easiest way to get a pixbuf from a cairo image
        # surface...
        r = int(random.random() * 999999)
        file_name = '/tmp/notifier_tmp_' + str(r) + '.png'
        surface.write_to_png(file_name)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_name)
        os.remove(file_name)
        return pixbuf

    def set_update_count(self, update_count):
        """
        set the available update count
        @param update_count: =0: no updates, -1: error occured
        """
        self.update_count = update_count
        self.update_tray_icon()

    def set_is_working(self, is_working=True):
        """
        set working: show a busy tray icon if is_working is True
        """
        if is_working:
            self.is_working = 1
        else:
            self.is_working = 0
        self.update_tray_icon()

    def need_user_input(self, need_input=True):
        """ call this when a user interacton/input is needed """

        self.need_input = need_input
        self.update_tray_icon()


#-------------------------------------------------------------- DBus Exception
class StatusIconError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG + 'StatusIconError'


#------------------------------------------------------------------ Main class
class YumexStatusDaemon(dbus.service.Object):

    def __init__(self):
        bus_name = dbus.service.BusName(DAEMON_ORG, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/')
        logger.debug('starting %s api version : %d' %
                     (DAEMON_ORG, api_version))

        # Vars
        self.started = False
        self.status_icon = None
        self.yumex_running = False
        self.yumex_pid = 0
        self.yumex_working = False
        # update checking
        self.update_timer_id = -1
        self.update_timestamp = UpdateTimestamp()
        self.next_update = 0
        self.last_timestamp = 0

        # yum daemon client setup
        try:
            self.backend = dnfdaemon.client.Client()
        except dnfdaemon.client.DaemonError as e:
            msg = str(e)
            logger.debug('Error starting dnfdaemon service: [%s]', msg)
            error_notify('Error starting dnfdaemon service\n\n%s' % msg, msg)
            sys.exit(1)

    def setup_statusicon(self):
        self.status_icon = StatusIcon()
        icon = self.status_icon.get_status_icon()
        icon.connect('activate', self.on_status_icon_clicked)
        self.status_icon.quit_menu.connect('activate', self.on_quit)
        self.status_icon.search_updates_menu.connect('activate',
                                                     self.on_check_updates)
        self.status_icon.run_yumex.connect('activate', self.on_run_yumex)

#=========================================================================
# DBus Methods
#=========================================================================

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='i')
    def GetVersion(self):
        """
        Get the daemon version
        """
        return api_version

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='',
                         sender_keyword='sender')
    def Exit(self, sender=None):
        """
        Exit the daemon
        :param sender:
        """
        Gtk.main_quit()

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='b',
                         sender_keyword='sender')
    def Start(self, sender=None):
        """
        """
        if not self.started:
            self.setup_statusicon()
            self.started = True
            self.startup_init_update_timer()
            if self.yumex_running:
                self.status_icon.run_yumex.hide()
            else:
                self.status_icon.run_yumex.show()
            return True
        else:
            return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='b',
                         out_signature='',
                         sender_keyword='sender')
    def SetWorking(self, is_working, sender=None):
        if self.started:
            self.status_icon.set_is_working(is_working)
            self.yumex_working = is_working

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='i',
                         out_signature='',
                         sender_keyword='sender')
    def SetUpdateCount(self, count, sender=None):
        if self.started:
            self.status_icon.set_update_count(count)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='i',
                         sender_keyword='sender')
    def CheckUpdates(self, sender=None):
        if self.started:
            return self.get_updates()

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='ib',
                         out_signature='b',
                         sender_keyword='sender')
    def SetYumexIsRunning(self, pid, state, sender=None):
        # pid for caller must match
        if not state and pid != self.yumex_pid:
            return False
        if not self.yumex_running == state:
            self.yumex_running = state
            if state:
                self.yumex_pid = pid
            else:
                self.yumex_pid = 0
            if self.started:
                if self.yumex_running:
                    self.status_icon.run_yumex.hide()
                else:
                    self.status_icon.run_yumex.show()
            return True
        else:  # Yumex is already running
            return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='i',
                         sender_keyword='sender')
    def GetYumexIsRunning(self, sender=None):
        if self.yumex_running:
            return self.yumex_pid
        else:
            return 0

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='b',
                         sender_keyword='sender')
    def GetYumexIsWorking(self, sender=None):
        if self.yumex_working:
            return True
        else:
            return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='b',
                         sender_keyword='sender')
    def ShowYumex(self, sender=None):
        if self.yumex_running:
            self.ShowSignal(self.yumex_pid)
            return True
        else:  # Yumex is already running
            return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                         in_signature='',
                         out_signature='',
                         sender_keyword='sender')
    def QuitYumex(self, sender=None):
        if self.yumex_running:
            self.QuitSignal(self.yumex_pid)

#=========================================================================
# DBus signals
#=========================================================================
    @dbus.service.signal(DAEMON_INTERFACE)
    def QuitSignal(self, pid):
        """
        """
        pass

    @dbus.service.signal(DAEMON_INTERFACE)
    def IconClickSignal(self, pid):
        """
        """
        pass

    @dbus.service.signal(DAEMON_INTERFACE)
    def ShowSignal(self, pid):
        """
        """
        pass

    @dbus.service.signal(DAEMON_INTERFACE)
    def CheckUpdateSignal(self, pid):
        """
        """
        pass

#=========================================================================
# yum helpers
#=========================================================================

    def get_updates(self, *args):
        logger.debug('get_updates')
        self.status_icon.set_is_working(True)
        try:
            self.backend.Lock()
            logger.debug('Check for updates')
            pkgs = self.backend.GetPackages('updates')
            rc = len(pkgs)
            logger.debug('# of updates : %d' % rc)
            self.backend.Unlock()
        except:  # Get locking errors
            logger.debug('Error getting the yum lock')
            rc = -1
        self.status_icon.set_is_working(False)
        self.status_icon.set_update_count(rc)
        if rc > 0:
            logger.debug('notification')
            notify = Notification(_('New Updates'),
                                  _('%s available updates') % rc)
            notify.connect('notify-action', self.on_notify_action)
            notify.show()
        self.update_timestamp.store_current_time()
        self.start_update_timer()  # restart update timer if necessary
        return rc

#=========================================================================
# GUI Callback
#=========================================================================
    def on_notify_action(self, widget, action):
        """Handle notification actions. """
        logger.debug('notify-action: %s', action)
        if action == 'open':
            self.run_yumex()
        elif action == 'apply':
            self.run_yumex(['--updateall'])

    def on_status_icon_clicked(self, event):
        """
        left click on status icon handler
        hide/show the window, based on current state
        """
        logger.debug('status-icon clicked')
        if self.yumex_running:
            self.IconClickSignal(self.yumex_pid)
        elif self.status_icon.update_count > 0:
            self.on_run_yumex()

    def on_quit(self, *args):
        """
        left click on status icon handler
        hide/show the window, based on current state
        """
        logger.debug('quit clicked')
        if self.yumex_running:
            self.QuitSignal(self.yumex_pid)
        else:
            Gtk.main_quit()

    def on_check_updates(self, * args):
        logger.debug('check updates clicked')
        if self.yumex_running:
            self.CheckUpdateSignal(self.yumex_pid)
        else:
            self.get_updates()

    def on_run_yumex(self, *args):
        self.run_yumex()

    def run_yumex(self, param=[]):
        logger.debug('run yumex')
        if not self.yumex_running:
            cmd = [YUMEX_BIN]
            cmd.extend(param)
            logger.debug('Starting: %s' % " ".join(cmd))
            Popen(cmd).pid

    def startup_init_update_timer(self):
        """ start the update timer with a delayed startup
        """
        if AUTOCHECK_UPDATE:
            logger.debug('Starting delayed update timer')
            GObject.timeout_add_seconds(
                TIMER_STARTUP_DELAY, self.start_update_timer)

    def start_update_timer(self):
        """
        start or restart the update timer: check when the last update was done
        """
        if AUTOCHECK_UPDATE:
            if self.update_timer_id != -1:
                GObject.source_remove(self.update_timer_id)

            # in seconds
            time_diff = self.update_timestamp.get_last_time_diff()
            delay = UPDATE_INTERVAL - int(time_diff / 60)
            if time_diff == -1 or delay < 0:
                delay = 0

            logger.debug(
                'Starting update timer with a '
                'delay of {0} min (time_diff={1})'.format(delay, time_diff))
            self.next_update = delay
            self.last_timestamp = int(time.time())
            self.update_timer_id = GObject.timeout_add_seconds(
                1, self.update_timeout)
        return False

    def update_timeout(self):
        if AUTOCHECK_UPDATE:
            self.next_update = self.next_update - 1
            self.update_timer_id = -1
            if self.next_update < 0:
                if self.yumex_running:
                    # do not check for updates now: retry in a minute
                    logger.debug('Yumex is running, try again in 1 minut')
                    self.update_timer_id = GObject.timeout_add_seconds(
                        60, self.update_timeout)
                else:
                    # check for updates: this will automatically restart the
                    # timer
                    self.get_updates()
            else:
                cur_timestamp = int(time.time())
                if cur_timestamp - self.last_timestamp > 60 * 2:
                    # this can happen on hibernation/suspend
                    # or when the system time changes
                    logger.debug('Time changed: restarting update timer')
                    self.start_update_timer()
                else:
                    self.update_timer_id = GObject.timeout_add_seconds(
                        60, self.update_timeout)
                self.last_timestamp = cur_timestamp
        return False


def doTextLoggerSetup(logroot=LOG_ROOT,
                      logfmt='%(asctime)s: %(message)s',
                      loglvl=logging.INFO):
    """ Setup Python logging  """
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, '%H:%M:%S')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)


def main():
    parser = argparse.ArgumentParser(
        description='Yumex Status Icon D-Bus Daemon')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        if args.debug:
            doTextLoggerSetup(loglvl=logging.DEBUG)
        else:
            doTextLoggerSetup()

    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    YumexStatusDaemon()
    Gtk.main()


if __name__ == '__main__':
    main()

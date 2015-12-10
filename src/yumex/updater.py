#!/usr/bin/python3
# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A GUI for yum
#    Copyright (C) 2015 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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

from gi.repository import Gio, Gtk, Notify, GObject
from yumex.misc import _, CONFIG
from subprocess import Popen
from xdg import BaseDirectory

import argparse
import dnfdaemon.client
import logging
import os
import sys
import time

import yumex.misc as misc
import yumex.const as const

LOG_ROOT = 'yumex.updater'

logger = logging.getLogger(LOG_ROOT)


BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

YUMEX_BIN = '/usr/bin/yumex-dnf'

CONF_DIR = BaseDirectory.save_config_path('yumex-dnf')
TIMESTAMP_FILE = os.path.join(CONF_DIR, 'update_timestamp.conf')
DELAYED_START = 5 * 60  # Seconds before first check


class Notification(GObject.GObject):
    __gsignals__ = {
        'notify-action': (GObject.SignalFlags.RUN_FIRST, None,
                      (str,))
    }

    def __init__(self, summary, body):
        GObject.GObject.__init__(self)
        Notify.init('Yum Extender')
        icon = "yumex-dnf"
        self.notification = Notify.Notification.new(summary, body, icon)
        self.notification.set_timeout(10000)  # timeout 10s
        self.notification.add_action('later', _('Not Now'),
                                     self.callback)
        self.notification.add_action('show', _('Show Updates'), self.callback)
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


class Updater:

    def __init__(self):
        # update checking
        self.update_timer_id = -1
        self.update_timestamp = UpdateTimestamp()
        self.next_update = 0
        self.last_timestamp = 0
        self.muted = False
        self.mute_count = 0
        self.last_num_updates = 0

        # dnfdaemon client setup
        try:
            self.backend = dnfdaemon.client.Client()
        except dnfdaemon.client.DaemonError as e:
            msg = str(e)
            logger.debug('Error starting dnfdaemon service: [%s]', msg)
            error_notify('Error starting dnfdaemon service\n\n%s' % msg, msg)
            sys.exit(1)

    def get_updates(self, *args):
        logger.debug('Checking for updates')
        try:
            self.backend.Lock()
            pkgs = self.backend.GetPackages('updates')
            rc = len(pkgs)
            logger.debug('# of updates : %d' % rc)
            self.backend.Unlock()
        except:  # Get locking errors
            logger.debug('Error getting the dnfdaemon lock')
            rc = -1
        if rc > 0:
            if self.mute_count < 1:
                # Only show the same notification once
                # until the user closes the notification
                if rc != self.last_num_updates:
                    logger.debug('notification opened : # updates = %d', rc)
                    notify = Notification(_('New Updates'),
                                          _('%s available updates') % rc)
                    notify.connect('notify-action', self.on_notify_action)
                    notify.show()
                    self.last_num_updates = rc
                else:
                    logger.debug('skipping notification (same # of updates)')
            else:
                self.mute_count -= 1
                logger.debug('skipping notification : mute_count = %s',
                             self.mute_count)
        self.update_timestamp.store_current_time()
        self.start_update_timer()  # restart update timer if necessary
        return rc

#=========================================================================
# Callbacks
#=========================================================================
    def on_notify_action(self, widget, action):
        """Handle notification actions. """
        logger.debug('notify-action: %s', action)
        if action == 'later':
            logger.debug('setting mute_count = 10')
            self.mute_count = 10
        elif action == 'show':
            self.run_yumex()
        elif action == 'closed':
            # reset the last number of updates notified
            # so we will get a new notification at next check
            self.last_num_updates = 0

    def run_yumex(self, param=[]):
        logger.debug('run yumex')
        cmd = [YUMEX_BIN]
        cmd.extend(param)
        logger.debug('Starting: %s' % " ".join(cmd))
        Popen(cmd).pid

    def startup_init_update_timer(self):
        """ start the update timer with a delayed startup
        """
        logger.debug('Starting delayed update timer')
        GObject.timeout_add_seconds(DELAYED_START, self.start_update_timer)

    def start_update_timer(self):
        """
        start or restart the update timer: check when the last update was done
        """
        if self.update_timer_id != -1:
            GObject.source_remove(self.update_timer_id)

        # in seconds
        time_diff = self.update_timestamp.get_last_time_diff()
        delay = CONFIG.conf.update_interval - int(time_diff / 60)
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
        self.next_update = self.next_update - 1
        self.update_timer_id = -1
        if self.next_update < 0:
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


class UpdateApplication(Gio.Application):
    """Update application."""

    def __init__(self):
        Gio.Application.__init__(self,
                    application_id="dk.yumex.yumex-updater",
                    flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

        self.connect("activate", self.on_activate)
        self.connect("command-line", self.on_command_line)
        self.connect("shutdown", self.on_shutdown)
        self.running = False
        self.args = None
        self.updater = None

    def on_activate(self, app):
        self.running = True
        self.updater = Updater()
        if not self.args.delay:
            self.updater.startup_init_update_timer()
        else:
            self.updater.start_update_timer()
        Gtk.main()
        return 0

    def _log_setup(self):
        if self.args.debug:
            misc.logger_setup(
                logroot='yumex.updater',
                logfmt='%(asctime)s: [%(name)s] - %(message)s',
                loglvl=logging.DEBUG)
        else:
            misc.logger_setup()

    def on_command_line(self, app, args):
        parser = argparse.ArgumentParser(prog='app')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument('--exit', action='store_true')
        parser.add_argument('--delay', type=int)
        if not self.running:
            # First run
            self.args = parser.parse_args(args.get_arguments()[1:])
            self._log_setup()
            if self.args.delay:
                CONFIG.conf.update_interval = self.args.delay
            logger.debug('first run')
        else:
            logger.debug('second run')
            # Second Run
            # parse cmdline in a non quitting way
            self.current_args = \
                parser.parse_known_args(args.get_arguments()[1:])[0]
            if self.current_args.exit:
                logger.debug('quitting')
                self.quit()
                sys.exit(0)
        if self.args.exit:  # kill dnf daemon and quit
            misc.dbus_dnfsystem('Exit')
            sys.exit(0)
        self.activate()
        return 0

    def on_shutdown(self, app):
        return 0
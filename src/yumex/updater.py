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


import argparse
import logging
import os
import sys
import time
from subprocess import Popen

from gi.repository import Gio, Gtk, Notify, GObject
from xdg import BaseDirectory

import dnfdaemon.client

from yumex.misc import _, CONFIG
import yumex.misc as misc

LOG_ROOT = 'yumex.updater'

logger = logging.getLogger(LOG_ROOT)


BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

YUMEX_BIN = '/usr/bin/yumex-dnf'

CONF_DIR = BaseDirectory.save_config_path('yumex-dnf')
TIMESTAMP_FILE = os.path.join(CONF_DIR, 'update_timestamp.conf')
DELAYED_START = 5 * 60  # Seconds before first check


class _Notification(GObject.GObject):
    """Used to notify users of available updates"""

    __gsignals__ = {
        'notify-action': (GObject.SignalFlags.RUN_FIRST, None,
                          (str,))
    }

    def __init__(self, summary, body):
        GObject.GObject.__init__(self)
        Notify.init('Yum Extender')
        icon = "yumex-dnf"
        self.__notification = Notify.Notification.new(summary, body, icon)
        self.__notification.set_timeout(10000)  # timeout 10s
        self.__notification.add_action('later', _('Not Now'),
                                       self.__callback)
        self.__notification.add_action('show', _('Show Updates'),
                                       self.__callback)
        self.__notification.connect('closed', self.__on_closed)

    def show(self):
        """Show the notification. This call does not block."""
        self.__notification.show()

    def __callback(self, notification, action):
        self.emit('notify-action', action)

    def __on_closed(self, notification):
        self.emit('notify-action', 'closed')


class _UpdateTimestamp:

    '''
    a persistent timestamp. e.g. for storing the last update check
    '''

    def __init__(self, file_name=TIMESTAMP_FILE):
        self.__time_file = file_name
        self.__last_time = -1

    def get_last_time_diff(self):
        '''
        returns time difference to last check in seconds >=0 or -1 on error
        '''
        now = int(time.time())
        if self.__last_time == -1:
            try:
                file = open(self.__time_file, 'r')
                t_old = int(file.read())
                file.close()
                self.__last_time = t_old
            except OSError as ose:
                # File has not been written yet, this might happen on first run
                logger.info('Error reading last timestamp from file: %s',
                            ose.strerror)
                self.__last_time = 0
        if self.__last_time > now:
            return -1
        return now - self.__last_time

    def store_current_time(self):
        """Save current time stamp permanently."""
        now = int(time.time())
        file = open(self.__time_file, 'w')
        file.write(str(now))
        file.close()
        self.__last_time = now


class _Updater:

    def __init__(self):
        # update checking
        self.__update_timer_id = -1
        self.__update_timestamp = _UpdateTimestamp()
        self.__next_update = 0
        self.__last_timestamp = 0
        self.__muted = False
        self.__mute_count = 0
        self.__last_num_updates = 0

        # dnfdaemon client setup
        try:
            self.__backend = dnfdaemon.client.Client()
        except dnfdaemon.client.DaemonError as error:
            msg = str(error)
            logger.debug('Error starting dnfdaemon service: [%s]', msg)
            misc.notify('Error starting dnfdaemon service\n\n%s' % msg, msg)
            sys.exit(1)

    def __get_updates(self):
        logger.debug('Checking for updates')
        if self.__backend.Lock():
            pkgs = self.__backend.GetPackages('updates')
            update_count = len(pkgs)
            self.__backend.Unlock()
            logger.debug('#Number of updates : %d', update_count)
        else:
            logger.debug('Could not get the dnfdaemon lock')
            update_count = -1
        if update_count > 0:
            if self.__mute_count < 1:
                # Only show the same notification once
                # until the user closes the notification
                if update_count != self.__last_num_updates:
                    logger.debug('notification opened : # updates = %d',
                                 update_count)
                    notify = _Notification(_('New Updates'),
                                           _('%s available updates')
                                           % update_count)
                    notify.connect('notify-action', self.__on_notify_action)
                    notify.show()
                    self.__last_num_updates = update_count
                else:
                    logger.debug('skipping notification (same # of updates)')
            else:
                self.__mute_count -= 1
                logger.debug('skipping notification : mute_count = %s',
                             self.__mute_count)
        self.__update_timestamp.store_current_time()
        self.start_update_timer()  # restart update timer if necessary
        return update_count

#=========================================================================
# Callbacks
#=========================================================================
    def __on_notify_action(self, notification, action):
        """Handle notification actions. """
        logger.debug('notify-action: %s', action)
        if action == 'later':
            logger.debug('setting mute_count = 10')
            self.__mute_count = 10
        elif action == 'show':
            logger.debug('Starting: %s', YUMEX_BIN)
            flags = Gio.AppInfoCreateFlags.NONE
            yumex_app = Gio.AppInfo.create_from_commandline(
                YUMEX_BIN, YUMEX_BIN, flags)
            yumex_app.launch(None, None)
        elif action == 'closed':
            # reset the last number of updates notified
            # so we will get a new notification at next check
            self.__last_num_updates = 0

    def startup_init_update_timer(self):
        """ start the update timer with a delayed startup. """
        logger.debug('Starting delayed update timer')
        GObject.timeout_add_seconds(DELAYED_START, self.start_update_timer)

    def start_update_timer(self):
        """
        start or restart the update timer: check when the last update was done
        """
        if self.__update_timer_id != -1:
            GObject.source_remove(self.__update_timer_id)

        # in seconds
        time_diff = self.__update_timestamp.get_last_time_diff()
        delay = CONFIG.conf.update_interval - int(time_diff / 60)
        if time_diff == -1 or delay < 0:
            delay = 0

        logger.debug(
            'Starting update timer with a '
            'delay of {0} min (time_diff={1})'.format(delay, time_diff))
        self.__next_update = delay
        self.__last_timestamp = int(time.time())
        self.__update_timer_id = GObject.timeout_add_seconds(
            1, self.__update_timeout)
        return False

    def __update_timeout(self):
        self.__next_update = self.__next_update - 1
        self.__update_timer_id = -1
        if self.__next_update < 0:
            # check for updates: this will automatically restart the
            # timer
            self.__get_updates()
        else:
            cur_timestamp = int(time.time())
            if cur_timestamp - self.__last_timestamp > 60 * 2:
                # this can happen on hibernation/suspend
                # or when the system time changes
                logger.debug('Time changed: restarting update timer')
                self.start_update_timer()
            else:
                self.__update_timer_id = GObject.timeout_add_seconds(
                    60, self.__update_timeout)
            self.__last_timestamp = cur_timestamp
        return False


class UpdateApplication(Gio.Application):
    """Update application."""

    def __init__(self):
        Gio.Application.__init__(
            self,
            application_id="dk.yumex.yumex-updater",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

        self.connect("activate", self.__on_activate)
        self.connect("command-line", self.__on_command_line)
        self.connect("shutdown", self.__on_shutdown)
        self.__running = False
        self.__args = None
        self.__updater = None

    def __on_activate(self, app):
        self.__running = True
        self.__updater = _Updater()
        if not self.__args.delay:
            self.__updater.startup_init_update_timer()
        else:
            self.__updater.start_update_timer()
        Gtk.main()
        return 0

    def __log_setup(self):
        if self.__args.debug:
            misc.logger_setup(
                logroot='yumex.updater',
                logfmt='%(asctime)s: [%(name)s] - %(message)s',
                loglvl=logging.DEBUG)
        else:
            misc.logger_setup()

    def __on_command_line(self, app, args):
        parser = argparse.ArgumentParser(prog='app')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument('--exit', action='store_true')
        parser.add_argument('--delay', type=int)
        if not self.__running:
            # First run
            self.__args = parser.parse_args(args.get_arguments()[1:])
            self.__log_setup()
            if self.__args.delay:
                CONFIG.conf.update_interval = self.__args.delay
            logger.debug('first run')
        else:
            logger.debug('second run')
            # Second Run
            # parse cmdline in a non quitting way
            self.__current_args = \
                parser.parse_known_args(args.get_arguments()[1:])[0]
            if self.__current_args.exit:
                logger.debug('quitting')
                self.quit()
                sys.exit(0)
        if self.__args.exit:  # kill dnf daemon and quit
            misc.dbus_dnfsystem('Exit')
            sys.exit(0)
        self.activate()
        return 0

    def __on_shutdown(self, app):
        return 0

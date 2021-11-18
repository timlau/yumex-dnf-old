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
#pylint: disable=no-member
import datetime
import logging
import sys

import yumex.common.const as const
import yumex.common as misc

from yumex.common import CONFIG, _

from yumex.backend.dnf import DnfRootBackend
from yumex.gui.dialogs import show_information

logger = logging.getLogger('yumex.base')


class BaseYumex:
    def __init__(self):
        self._root_backend = None
        self._root_locked = False
        self.is_working = False
        self.infobar = None

    def set_working(self, state, insensitive=True, splash=False):
        """Set the working state. (implement in subclass)"""
        raise NotImplementedError

    def _check_cache_expired(self, cache_type):
        time_fmt = '%Y-%m-%d %H:%M'
        now = datetime.datetime.now()
        refresh_period = datetime.timedelta(hours=CONFIG.conf.refresh_interval)
        # check if cache management is disabled
        if CONFIG.conf.refresh_interval == 0:
            return False
        if cache_type == 'session':
            last_refresh = datetime.datetime.strptime(
                CONFIG.conf.session_refresh, time_fmt)
            period = now - last_refresh
            logger.debug(f'time since last cache refresh : {period}')
            return period > refresh_period
        elif cache_type == 'system':
            last_refresh = datetime.datetime.strptime(
                CONFIG.conf.system_refresh, time_fmt)
            period = now - last_refresh
            logger.debug(f'time since last cache refresh : {period}')
            return period > refresh_period

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

    @misc.exception_handler
    def reset_cache(self):
        logger.debug('Refresh system cache')
        self.set_working(True, True, splash=True)
        self.infobar.message(_('Refreshing Repository Metadata'))
        rc = self._root_backend.ExpireCache()
        self.set_working(False, splash=True)
        if rc:
            self._set_cache_refreshed('system')
        else:
            show_information(self, _('Could not refresh the DNF cache (root)'))

    @misc.exception_handler
    def get_root_backend(self):
        """Get the current root backend.

        if it is not setup yet, the create it
        if it is not locked, then lock it
        """
        if self._root_backend is None:
            self._root_backend = DnfRootBackend(self)
        if self._root_locked is False:
            logger.debug('Lock the DNF root daemon')
            locked, msg = self._root_backend.setup()
            errmsg = ""
            if locked:
                self._root_locked = True
                if self._check_cache_expired('system'):
                    logger.debug("cache is expired, reloading")
                    self.reset_cache()
            else:
                logger.critical("can't get root backend lock")
                if msg == 'not-authorized':  # user canceled the polkit dialog
                    errmsg = _('DNF root backend was not authorized.\n'
                               'Yum Extender will exit')
                # DNF is locked by another process
                elif msg == 'locked-by-other':
                    errmsg = _('DNF is locked by another process.\n\n'
                               'Yum Extender will exit')
                self.error_dialog.show(errmsg)
                sys.exit(1)
        return self._root_backend

    @misc.exception_handler
    def release_root_backend(self, quit_dnfdaemon=False):
        """Release the current root backend, if it is setup and locked."""
        if self._root_backend is None:
            return
        if self._root_locked is True:
            logger.debug('Unlock the DNF root daemon')
            self._root_backend.Unlock()
            self._root_locked = False
        if quit_dnfdaemon:
            logger.debug('Exit the DNF root daemon')
            self._root_backend.Exit()

    def exception_handler(self, e):
        """Called if exception occours in methods with the
        @ExceptionHandler decorator.
        """
        close = True
        msg = str(e)
        logger.error(f'BASE EXCEPTION : {msg}')
        err, errmsg = self._parse_error(msg)
        logger.debug(f'BASE err:  [{err}] - msg: {errmsg}')
        if err == 'LockedError':
            errmsg = 'DNF is locked by another process.\n' \
                '\nYum Extender will exit'
            close = False
        elif err == 'NoReply':
            errmsg = 'DNF D-Bus backend is not responding.\n' \
                '\nYum Extender will exit'
            close = False
        if errmsg == '':
            errmsg = msg
        self.error_dialog.show(errmsg)

        # try to exit the backends, ignore errors
        if close:
            try:
                self.release_root_backend(quit_dnfdaemon=True)
            except Exception:  # pylint: disable=broad-except
                pass
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

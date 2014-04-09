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

import sys
import re
import weakref
import logging

logger = logging.getLogger("yumex.status")

from gi.repository import Gio, GObject

ORG = 'dk.yumex.StatusIcon'
INTERFACE = ORG

DBUS_ERR_RE = re.compile('^GDBus.Error:([\w\.]*): (.*)$')


#
# Helper Classes
#


class DBus:
    '''
    Helper class to work with GDBus in a easier way
    '''
    def __init__(self, conn):
        self.conn = conn

    def get(self, bus, obj, iface=None):
        if iface is None:
            iface = bus
        return Gio.DBusProxy.new_sync(
            self.conn, 0, None, bus, obj, iface, None
        )

    def get_async(self, callback, bus, obj, iface=None):
        if iface is None:
            iface = bus
        Gio.DBusProxy.new(
            self.conn, 0, None, bus, obj, iface, None, callback, None
        )


class WeakMethod:
    '''
    helper class to work with a weakref class method
    '''
    def __init__(self, inst, method):
        self.proxy = weakref.proxy(inst)
        self.method = method

    def __call__(self, *args):
        return getattr(self.proxy, self.method)(*args)


# Get the system bus
session = DBus(Gio.bus_get_sync(Gio.BusType.SESSION, None))

#
# Main Client Class
#


class StatusIcon:
    def __init__(self, app):
        self.app = app
        self.bus = session
        self.dbus_org = ORG
        self.dbus_interface = INTERFACE
        self.daemon = self._get_daemon(
            self.bus, self.dbus_org, self.dbus_interface)
        logger.debug("%s daemon loaded - version :  %s" %
                     (self.dbus_interface, self.daemon.GetVersion()))

    def _get_daemon(self, bus, org, interface):
        ''' Get the daemon dbus proxy object'''
        try:
            proxy = bus.get(org, "/", interface)
            proxy.GetVersion()  # Get daemon version, to check if it is alive
            # Connect the Dbus signal handler
            proxy.connect('g-signal', WeakMethod(self, '_on_g_signal'))
            return proxy
        except Exception as err:
            self._handle_dbus_error(err)

    def _on_g_signal(self, proxy, sender, signal, params):
        '''
        DBUS signal Handler
        :param proxy: DBus proxy
        :param sender: DBus Sender
        :param signal: DBus signal
        :param params: DBus signal parameters
        '''
        args = params.unpack()  # unpack the glib variant
        self.handle_dbus_signals(proxy, sender, signal, args)

    def handle_dbus_signals(self, proxy, sender, signal, args):
        """
        Overload in child class
        """
        logger.debug("Signal : %s " % signal)
        if signal == 'IconClickSignal':
            self.app.win.on_status_icon_clicked()
        elif signal == 'QuitSignal':
            self.app.on_quit()
        elif signal == 'CheckUpdateSignal':
            self.app.win.check_for_updates()

    def _handle_dbus_error(self, err):
        '''
        Parse error from service and raise python Exceptions
        :param err:
        :type err:
        '''
        exc, msg = self._parse_error()
        print (exc, msg)

    def _parse_error(self):
        '''
        parse values from a DBus releated exception
        '''
        (type, value, traceback) = sys.exc_info()
        res = DBUS_ERR_RE.match(str(value))
        if res:
            return res.groups()
        return "", ""

    def _return_handler(self, obj, result, user_data):
        '''
        Async DBus call, return handler
        :param obj:
        :type obj:
        :param result:
        :type result:
        :param user_data:
        :type user_data:
        '''
        if isinstance(result, Exception):
            # print(result)
            user_data['result'] = None
            user_data['error'] = result
        else:
            user_data['result'] = result
            user_data['error'] = None
        user_data['main_loop'].quit()

    def _get_result(self, user_data):
        '''
        Get return data from async call or handle error
        :param user_data:
        :type user_data:
        '''
        if user_data['error']:  # Errors
            self._handle_dbus_error(user_data['error'])
        else:
            return user_data['result']

    def _run_dbus_async(self, cmd, *args):
        '''
        Make an async call to a DBus method in the yumdaemon service
        :param cmd: method to run
        :type cmd: string
        '''
        main_loop = GObject.MainLoop()
        data = {'main_loop': main_loop}
        func = getattr(self.daemon, cmd)
        # timeout = infinite
        func(*args, result_handler=self._return_handler,
             user_data=data, timeout=GObject.G_MAXINT)
        data['main_loop'].run()
        result = self._get_result(data)
        return result

    def _run_dbus_sync(self, cmd, *args):
        '''
        Make a sync call to a DBus method in the yumdaemon service
        :param cmd:
        :type cmd:
        '''
        func = getattr(self.daemon, cmd)
        return func(*args)

    def Exit(self):
        self.daemon.Exit()

    def Start(self):
        return self.daemon.Start()

    def SetWorking(self, is_working):
        self.daemon.SetWorking("(b)", is_working)

    def SetUpdateCount(self, count):
        self.daemon.SetUpdateCount("(i)", count)

    def CheckUpdates(self):
        return self._run_dbus_async("CheckUpdate")

    def SetYumexIsRunning(self, state):
        return self.daemon.SetYumexIsRunning("(b)", state)

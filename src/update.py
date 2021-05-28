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

from yumex.updater import UpdateApplication
import sys
import traceback
import subprocess
import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')


here = sys.path[0]
if here != '/usr/bin':
    # git checkout
    sys.path[0] = here
    print("set PYTHONPATH to %s" % here)

try:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = UpdateApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
except Exception as e:
    print("Exception in user code:")
    print('-' * 80)
    traceback.print_exc(file=sys.stdout)
    print('-' * 80)

    # Try to close backend dbus daemon
    print('Closing backend D-Bus daemons')
    try:
        subprocess.call(
            '/usr/bin/dbus-send --system --print-reply '
            '--dest=org.baseurl.DnfSystem / org.baseurl.DnfSystem.Exit',
            shell=True)
    finally:
        sys.exit(1)

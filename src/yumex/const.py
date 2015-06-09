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

from gi.repository import Pango
from yumex.misc import _

import os.path
import re
import subprocess
import sys
import hawkey

VERSION = "4.1.3"

NEEDED_DAEMON_API = 2  # The needed dnfdaemon API version
NEEDED_STATUS_API = 1  # The needed statusicon API version

# find the data dir for resources
BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
if BIN_PATH in ["/usr/bin", "/bin"]:
    DATA_DIR = '/usr/share/yumex-dnf'
    PIX_DIR = DATA_DIR + "/gfx"
    MISC_DIR = DATA_DIR
else:
    DATA_DIR = BIN_PATH
    PIX_DIR = DATA_DIR + "/../gfx"
    MISC_DIR = DATA_DIR + "/../misc"

ARCH = subprocess.check_output(
    '/usr/bin/rpm --eval %_arch', shell=True).decode("utf-8")[:-1]

ARCH_DICT = {
    "x86_64": set(['x86_64', 'i686', 'i386', 'noarch']),
    "i386": set(['i686', 'i386', 'noarch']),
    "armhfp": set(['armv7hl', 'noarch'])
}

# arch for this platform
if ARCH in ARCH_DICT:
    PLATFORM_ARCH = ARCH_DICT[ARCH]
else:  # use x86_64 as fallback
    PLATFORM_ARCH = ARCH_DICT['x86_64']

DBUS_ERR_RE = re.compile('.*GDBus.Error:([\w\.]*): (.*)$')

ICON_TRAY_ERROR = PIX_DIR + '/tray-error.png'
ICON_TRAY_NO_UPDATES = PIX_DIR + '/tray-no-updates.png'
ICON_TRAY_UPDATES = PIX_DIR + '/tray-updates.png'
ICON_TRAY_WORKING = PIX_DIR + '/tray-working.png'
ICON_TRAY_INFO = PIX_DIR + '/tray-info.png'

# Fonts
XSMALL_FONT = Pango.FontDescription("sans 6")
SMALL_FONT = Pango.FontDescription("sans 8")
BIG_FONT = Pango.FontDescription("sans 12")

# Constants

# Main UI stack names
PAGE_PACKAGES = 'packages'
PAGE_QUEUE = 'queue'
PAGE_HISTORY = 'history'
PAGE_GROUPS = 'groups'

ACTIONS_FILTER = {'u': 'updates', 'i': 'available',
                  'r': 'installed', 'o': 'obsoletes',
                  'do': 'downgrade', 'ri': 'reinstall', 'li': 'localinstall'}

FILTER_ACTIONS = {'updates': 'u', 'available': 'i', 'installed': 'r',
                  'obsoletes': 'o', 'downgrade': 'do', 'reinstall': 'ri',
                  'localinstall': 'li', 'updates_all': 'u'}


PACKAGE_COLORS = {
    'i': 'black',
    'u': 'red',
    'r': 'darkgreen',
    'o': 'blue',
    'ri': 'red',
    'do': 'goldenrod',
    'li': 'black'

}

BACKEND_ACTIONS = {'update': 'u', 'install': 'i', 'remove': 'r',
                   'obsolete': 'o', 'downgrade': 'do'}


QUEUE_PACKAGE_TYPES = {
    'i': 'install',
    'u': 'update',
    'r': 'remove',
    'o': 'obsolete',
    'ri': 'reinstall',
    'do': 'downgrade',
    'li': 'localinstall'
}

# Package info filters (widget : info_xxxxxx)
PKGINFO_FILTERS = ['desc', 'updinfo', 'changelog', 'files', 'deps']

# FIXME: The url should not be hardcoded
BUGZILLA_URL = 'https://bugzilla.redhat.com/show_bug.cgi?id='
FEDORA_PACKAGES_URL = 'https://apps.fedoraproject.org/packages/'


PACKAGE_LOAD_MSG = {
    'installed': _('Getting installed packages'),
    'available': _('Getting available packages'),
    'updates': _('Getting available updates'),
    'all': _('Getting all packages')
}

HISTORY_NEW_STATES = ['Update', 'Downgrade', 'Obsoleting']
HISTORY_OLD_STATES = ['Updated', 'Downgraded', 'Obsoleted']

HISTORY_UPDATE_STATES = ['Update', 'Downgrade', 'Updated', 'Downgraded']

HISTORY_SORT_ORDER = ['Install', 'True-Install', 'Reinstall', 'Update',
                      'Downgrade', 'Obsoleting', 'Obsoleted', 'Erase',
                      'Dep-Install']

HISTORY_STATE_LABLES = {
    'Update': _('Updated packages'),
    'Downgrade': _('Downgraded packages'),
    'Obsoleting': _('Obsoleting packages'),
    'Obsoleted': _('Obsoleted packages'),
    'Erase': _('Erased packages'),
    'Install': _('Installed packages'),
    'True-Install': _('Installed packages'),
    'Dep-Install': _('Installed for dependencies'),
    'Reinstall': _('Reinstalled packages')}


TRANSACTION_RESULT_TYPES = {
    'install': _('Installing'),
    'update': _('Updating'),
    'remove': _('Removing'),
    'downgrade': _('Downgrading'),
    'reinstall': _('Replacing')
}

RPM_ACTIONS = {
    'update': _("Updating: %s"),
    'install': _("Installing: %s"),
    'reinstall': _("Reinstalling: %s"),
    'cleanup': _("Cleanup: %s"),
    'erase': _("Removing: %s"),
    'obsolete': _("Obsoleting: %s"),
    'downgrade': _("Downgrading: %s"),
    'verify': _("Verifying: %s"),
}

WIDGETS_INSENSITIVE = ["header_menu", "header_filters",
                       "header_search_options", "header_execute", "search"]

FEDORA_REPOS = ['fedora', 'updates', 'updates-testing', 'rawhide']


ADVISORY_TYPES = {
hawkey.ADVISORY_BUGFIX: _('Bugfix'),
hawkey.ADVISORY_UNKNOWN: _('New Package'),
hawkey.ADVISORY_SECURITY: _('Security'),
hawkey.ADVISORY_ENHANCEMENT: _('Enhancement')
}

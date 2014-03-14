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


from gi.repository import Pango
import os.path
import sys
import re
from .misc import _, P_  # @UnusedImport
from subprocess import check_output


__yumex_version__ = "3.99.1"


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

ARCH = check_output('/usr/bin/rpm --eval %_arch', shell=True).decode("utf-8")[:-1]

ARCH_DICT = {
"x86_64" : ['x86_64','i686','i386','noarch'],
"i386"   : ['i686','i386','noarch'],
"armhfp"    : ['armv7hl','noarch']
}

# arch for this platform
if ARCH in ARCH_DICT:
    PLATFORM_ARCH = ARCH_DICT[ARCH]
else: # use x86_64 as fallback
    PLATFORM_ARCH = ARCH_DICT['x86_64']

DBUS_ERR_RE = re.compile('^GDBus.Error:([\w\.]*): (.*)$')

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

# Notebook page numbers
PAGE_PACKAGES = 0
PAGE_QUEUE = 1
PAGE_HISTORY = 2
PAGE_GROUPS = 3

ACTIONS_FILTER = { 'u' : 'updates', 'i' : 'available', \
                   'r' : 'installed' , 'o' : 'obsoletes', \
                    'do' : 'downgrade', 'ri' : 'reinstall', 'li' : 'localinstall' }

FILTER_ACTIONS = {'updates' : 'u', 'available': 'i', 'installed' : 'r', \
                   'obsoletes' : 'o', 'downgrade'  : 'do', 'reinstall' : 'ri', 'localinstall' : 'li'}


PACKAGE_COLORS = {
'i' : 'black',
'u' : 'red',
'r' : 'darkgreen',
'o' : 'blue',
'ri' : 'red',
'do' : 'goldenrod',
'li' : 'black'

}

BACKEND_ACTIONS = {'update' : 'u', 'install': 'i', 'remove' : 'r', \
                   'obsolete' : 'o', 'downgrade'  : 'do'}


QUEUE_PACKAGE_TYPES = {
'i' : 'install',
'u' : 'update',
'r' : 'remove',
'o' : 'obsolete',
'ri' : 'reinstall',
'do' : 'downgrade',
'li' : 'localinstall'
}

# Package info filters (widget : info_xxxxxx)
PKGINFO_FILTERS = ['desc', 'updinfo', 'changelog', 'files', 'deps']

# FIXME: The url should not be hardcoded
BUGZILLA_URL = 'https://bugzilla.redhat.com/show_bug.cgi?id='



PACKAGE_LOAD_MSG = {
 'installed'    : _('Getting installed packages'),
 'available'    : _('Getting available packages'),
 'updates'      : _('Getting available updates'),
 }

HISTORY_NEW_STATES = ['Update', 'Downgrade', 'Obsoleting']
HISTORY_OLD_STATES = ['Updated', 'Downgraded', 'Obsoleted']

HISTORY_UPDATE_STATES = ['Update', 'Downgrade', 'Updated', 'Downgraded']

HISTORY_SORT_ORDER = ['Install', 'True-Install', 'Reinstall', 'Update', 'Downgrade', 'Obsoleting', 'Obsoleted', 'Erase', 'Dep-Install' ]

HISTORY_STATE_LABLES = {
     'Update' : _('Updated packages'),
     'Downgrade' : _('Downgraded packages'),
     'Obsoleting' : _('Obsoleting packages'),
     'Obsoleted' : _('Obsoleted packages'),
     'Erase' : _('Erased packages'),
     'Install' : _('Installed packages'),
     'True-Install' : _('Installed packages'),
     'Dep-Install' : _('Installed for dependencies'),
     'Reinstall' : _('Reinstalled packages')}


TRANSACTION_RESULT_TYPES = {
'install'       : _('Installing'),
'update'        : _('Updating'),
'remove'        : _('Removing'),
'downgrade'     : _('Downgrading'),
'reinstall'     : _('Replacing')
}

RPM_ACTIONS = {
'update'    : _("Updating : %s"),
'install'   : _("Installing : %s"),
'cleanup'   : _("Cleanup : %s"),
'erase'     : _("Removing : %s"),
'obsolete'  : _("Obsoleting :"),
}


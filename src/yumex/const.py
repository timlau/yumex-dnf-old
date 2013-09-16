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
from .misc import _, P_

__yumex_version__ = "3.99.1"


# find the data dir for resources
BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
if BIN_PATH in ["/usr/bin", "/bin"]:
    DATA_DIR = '/usr/share/yumex-nextgen'
    PIX_DIR = DATA_DIR+"/gfx"
else:
    DATA_DIR = BIN_PATH
    PIX_DIR = DATA_DIR+"/../gfx"


DBUS_ERR_RE = re.compile('^GDBus.Error:([\w\.]*): (.*)$')


# Fonts
XSMALL_FONT = Pango.FontDescription("sans 6")
SMALL_FONT = Pango.FontDescription("sans 8")
BIG_FONT = Pango.FontDescription("sans 12")

# Constants

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
                   'obsoletes' : 'o', 'downgrade'  : 'do'}


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
PKGINFO_FILTERS = ['desc','updinfo','changelog','files','deps']

#FIXME: The url should not be hardcoded
BUGZILLA_URL='https://bugzilla.redhat.com/show_bug.cgi?id='



PACKAGE_LOAD_MSG = {
 'installed'    : _('Getting installed packages'),
 'available'    : _('Getting available packages'),
 'updates'      : _('Getting available updates'),
 }
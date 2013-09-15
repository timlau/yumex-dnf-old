from gi.repository import Pango
import gettext
import os.path
import sys

gettext.bindtextdomain('yumex')
gettext.textdomain('yumex')
_ = gettext.gettext
P_ = gettext.ngettext

__yumex_version__ = "3.99.1"

# find the data dir for resources
BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
if BIN_PATH in ["/usr/bin", "/bin"]:
    DATA_DIR = '/usr/share/yumex-nextgen'
else:
    DATA_DIR = BIN_PATH


# Fonts
XSMALL_FONT = Pango.FontDescription("sans 6")
SMALL_FONT = Pango.FontDescription("sans 8")
BIG_FONT = Pango.FontDescription("sans 12")

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

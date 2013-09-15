from gi.repository import Pango
import gettext


gettext.bindtextdomain('yumex')
gettext.textdomain('yumex')
_ = gettext.gettext
P_ = gettext.ngettext

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

# -*- coding: utf-8 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 -2014 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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

from gi.repository import Gtk, Gio, GLib
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
from yumex.misc import _, CONFIG

import datetime
import hawkey
import logging
import subprocess
import urllib.parse


import yumex.const as const
import yumex.misc

logger = logging.getLogger('yumex.gui.widget')
G_TRUE = GLib.Variant.new_boolean(True)
G_FALSE = GLib.Variant.new_boolean(False)


class InfoProgressBar:

    def __init__(self, ui):
        self.ui = ui
        self.infobar = ui.get_object("info_revealer")  # infobar revealer
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")
        self.spinner = ui.get_object("info_spinner")

    def _show_infobar(self, show=True):
        self.infobar.set_reveal_child(show)
        if show:
            self.infobar.show()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.infobar.hide()
            self.label.hide()
            self.sublabel.hide()
            self.progress.hide()
            self.progress.set_show_text(False)

    def show_progress(self, state):
        if state:
            self.show_label()
        else:
            self._show_infobar(False)

    def hide(self):
        self._show_infobar(False)

    def hide_sublabel(self):
        self.sublabel.hide()

    def show_label(self, msg=""):
        self.label.set_text(msg)
        self.label.show()

    def show_sublabel(self, msg=""):
        self.sublabel.set_text(msg)
        self.sublabel.show()

    def show_all(self):
        self.show_label()
        self.show_sublabel()
        self.progress.show()

    def info(self, msg):
        self._show_infobar(True)
        self.show_label(msg)

    def info_sub(self, msg):
        self._show_infobar(True)
        self.show_sublabel(msg)

    def set_progress(self, frac, label=None):
        if frac >= 0.0 and frac <= 1.0:
            self._show_infobar()
            self.progress.show()
            self.progress.set_fraction(frac)
            # make sure that the main label is shown, else the progress
            # looks bad. this normally happens when changlog or filelist info
            # is needed for a package and it will trigger the yum daemon to
            # download the need metadata.
            if not self.label.get_property('visible'):
                self.info(_("Getting Package Metadata"))


class SearchBar(GObject.GObject):
    """Handling the search UI."""

    __gsignals__ = {'search': (GObject.SignalFlags.RUN_FIRST,
                               None,
                               (GObject.TYPE_STRING,
                                GObject.TYPE_STRING,
                                GObject.TYPE_PYOBJECT,))
                    }

    FIELDS = ['name', 'summary', 'description']
    TYPES = ['prefix', 'keyword', 'fields']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self.search_type = CONFIG.conf.search_default
        self.search_fields = CONFIG.conf.search_fields
        self.active = False
        # widgets
        self._bar = self.win.get_ui('search_bar')
        # Searchbar togglebutton
        self._toggle = self.win.get_ui('sch_togglebutton')
        self._toggle.connect('toggled', self.on_toggle)
        # Search Entry
        self._entry = self.win.get_ui('search_entry')
        self._entry.connect('activate', self.on_entry_activate)
        self._entry.connect('icon-press', self.on_entry_icon)
        # Search Options
        self._options = self.win.get_ui('search-options')
        self._options_button = self.win.get_ui('sch_options_button')
        self._options_button.connect('clicked', self.on_options_button)
        # Search Spinner
        self._spinner = self.win.get_ui('search_spinner')
        self._spinner.stop()
        # setup field checkboxes
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            if key in self.search_fields:
                wid.set_active(True)
            wid.connect('toggled', self.on_fields_changed, key)
        # set fields sensitive if type == 'fields'
        self._set_fields_sensitive(self.search_type == 'fields')
        # setup search type radiobuttons
        for key in SearchBar.TYPES:
            wid = self.win.get_ui('sch_opt_%s' % key)
            if key == self.search_type:
                wid.set_active(True)
            wid.connect('toggled', self.on_type_changed, key)
        # setup search option popover
        self.opt_popover = self.win.get_ui('sch_opt_popover')

    def show_spinner(self, state=True):
        """Set is spinner in searchbar is running."""
        if state:
            self._spinner.start()
        else:
            self._spinner.stop()

    def toggle(self):
        self._toggle.set_active(not self._toggle.get_active())

    def _set_fields_sensitive(self, state=True):
        """Set sensitivity of field checkboxes."""
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            wid.set_sensitive(state)

    def _get_active_field(self):
        """Get the active search fields, based on checkbox states."""
        active = []
        for key in SearchBar.FIELDS:
            wid = self.win.get_ui('sch_fld_%s' % key)
            if wid.get_active():
                active.append(key)
        return active

    def _set_focus(self):
        """Set focus on search entry and move cursor to end of text."""
        self._entry.grab_focus()
        self._entry.emit(
            'move-cursor', Gtk.MovementStep.BUFFER_ENDS, 1, False)

    def on_options_button(self, widget):
        """Search Option button is toggled."""
        if self.opt_popover.get_visible():
            self.opt_popover.hide()
            self._set_focus()
        else:
            self.opt_popover.show_all()

    def on_toggle(self, widget=None):
        """Search Toggle button is toggled."""
        self._bar.set_search_mode(not self._bar.get_search_mode())
        if self._bar.get_search_mode():
            self._set_focus()
        self.active = self._bar.get_search_mode()

    def on_type_changed(self, widget, key):
        """Search type is changed."""
        if widget.get_active():
            self.search_type = key
            CONFIG.conf.search_default = key
            if self.search_type == 'fields':
                self._set_fields_sensitive(True)
            else:
                self._set_fields_sensitive(False)

    def on_fields_changed(self, widget, key):
        """Search fields is changed."""
        self.search_fields = self._get_active_field()
        CONFIG.conf.search_fields = self.search_fields

    def on_entry_activate(self, widget):
        """Seach entry is activated"""
        # make sure search option is hidden
        self.signal()

    def on_entry_icon(self, widget, icon_pos, event):
        """Search icon press callback."""
        # clear icon pressed
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            self._entry.set_text('')
            self._entry.emit('activate')

    def signal(self):
        """Emit a seach signal with key, search type & fields."""
        txt = self._entry.get_text()
        if self.search_type == 'fields':
            self.emit('search', txt, self.search_type, self.search_fields)
        else:
            self.emit('search', txt, self.search_type, [])

    def reset(self):
        self._entry.set_text('')

    def hide(self):
        if self.active:
            self._bar.set_search_mode(False)

    def show(self):
        if self.active:
            self._bar.set_search_mode(True)
            self._set_focus()


class FilterSidebar(GObject.GObject):
    """Sidebar selector widget. """

    __gsignals__ = {'sidebar-changed': (GObject.SignalFlags.RUN_FIRST,
                                        None,
                                        (GObject.TYPE_STRING,))}

    INDEX = {0: 'updates', 1: 'installed', 2: 'available', 3: 'all'}

    def __init__(self, parent):
        GObject.GObject.__init__(self)
        self._lb = parent.get_ui('pkg_listbox')
        self._parent = parent
        self._current = None
        self._lb.unselect_all()
        self._lb.connect('row-selected', self.on_toggled)

    def on_toggled(self, widget, row):
        """Active filter is changed."""
        if row:
            ndx = row.get_index()
            key = FilterSidebar.INDEX[ndx]
            if key != self._current:
                self.emit('sidebar_changed', key)
                self._current = key

    def set_active(self, key):
        """Set the active item based on key."""
        if self._current == key:
            self.emit('sidebar_changed', key)
        else:
            row_name = 'pkg_flt_row_' + key
            row = self._parent.get_ui(row_name)
            self._lb.select_row(row)


class Filters(GObject.GObject):
    """Handling the package filter UI."""

    __gsignals__ = {'filter-changed': (GObject.SignalFlags.RUN_FIRST,
                                       None,
                                       (GObject.TYPE_STRING,)
                                       )}

    FILTERS = ['updates', 'installed', 'available', 'all']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self._sidebar = FilterSidebar(self.win)
        self.current = 'updates'
        self._sidebar.connect('sidebar-changed', self.on_toggled)

    def on_toggled(self, widget, flt):
        """Active filter is changed."""
        self.current = flt
        self.emit('filter-changed', flt)

    def set_active(self, flt):
        """Set the active filter."""
        self._sidebar.set_active(flt)


class Content(GObject.GObject):
    """Handling the content pages"""

    __gsignals__ = {'page-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,)
                                     )}

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self._stack = self.win.get_ui('main_stack')
        self.switcher = self.win.get_ui('main_switcher')
        # catch changes in active page in stack
        self._stack.connect('notify::visible-child', self.on_switch)

    def select_page(self, page):
        """Set the active page."""
        self._stack.set_visible_child_name(page)

    def on_menu_select(self, widget, page):
        """Main menu page entry is seleceted"""
        self.select_page(page)

    def on_switch(self, widget, data):
        """The active page is changed."""
        child = self._stack.get_visible_child_name()
        self.emit('page-changed', child)


class PackageDetails(GObject.GObject):
    __gsignals__ = {'info-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,))
                    }

    VALUES = {0: 'desc', 1: 'updinfo', 2: 'files', 3: 'deps'}
    DEFAULT_STYLES = ['description', 'filelist', 'changelog',
                      'changelog-header']

    def __init__(self, win, url_handler=None):
        super(PackageDetails, self).__init__()
        self.win = win
        self.widget = self.win.get_ui('info_box')
        self._listbox = self.win.get_ui('info_list')
        self._listbox.connect('row-selected', self.on_toggled)

        self._text = self.win.get_ui('info_text')
        self._text.connect("motion_notify_event", self.on_mouse_motion)
        self._buffer = self.win.get_ui('info_buffer')
        self._tags = self.win.get_ui('info_tags')
        self._default_style = self._tags.lookup('')
        self._url_handler = url_handler
        # List of active URLs in the tab
        self.url_tags = []
        self.underlined_url = False
        self.url_list = {}

    def show(self, show=True):
        if show:
            self.widget.show_all()
            self.clear()
        else:
            self.widget.hide()

    def on_toggled(self, listbox, row):
        if row:
            ndx = row.get_index()
            key = PackageDetails.VALUES[ndx]
            self.emit('info-changed', key)

    def get_style(self, tag_name):
        if tag_name in PackageDetails.DEFAULT_STYLES and \
           yumex.misc.check_dark_theme():
            tag_name += '_dark'
        style = self._tags.lookup(tag_name)
        return style

    def write(self, txt, style_name=None, newline=True):
        if not txt:
            return
        if newline and txt[-1] != '\n':
            txt += '\n'
        start, end = self._buffer.get_bounds()
        if style_name:
            style = self.get_style(style_name)
        else:
            style = self.get_style('description')
        if style:
            self._buffer.insert_with_tags(end, txt, style)
        else:
            self._buffer.insert(end, txt)
        self._text.scroll_to_iter(self._buffer.get_end_iter(),
                                  0.0, True, 0.0, 0.0)

    def clear(self):
        self._buffer.set_text('')

    def goto_top(self):
        self._text.scroll_to_iter(self._buffer.get_start_iter(),
                                  0.0, False, 0.0, 0.0)

    def on_url_event(self, tag, widget, event, iterator):
        """ Catch when the user clicks the URL """
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            url = self.url_list[tag.get_property("name")]
            if self._url_handler:
                self._url_handler(url)

    def on_mouse_motion(self, widget, event, data=None):
        '''
        Mouse movement handler for TextView

        :param widget:
        :param event:
        :param data:
        '''
        window = widget.get_window(Gtk.TextWindowType.WIDGET)
        # Get x,y pos for widget
        w, x, y, mask = window.get_pointer()
        # convert coords to TextBuffer coords
        x, y = widget.window_to_buffer_coords(Gtk.TextWindowType.TEXT, x, y)
        # Get the tags on current pointer location
        itr = widget.get_iter_at_location(x, y)
        if isinstance(itr, tuple):
            itr = itr[1]
            tags = itr.get_tags()
            # Remove underline and hand mouse pointer
            if self.underlined_url:
                self.underlined_url.set_property("underline",
                                                 Pango.Underline.NONE)
                widget.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)
                self.underlined_url = None
            for tag in tags:
                if tag in self.url_tags:
                    # underline the tags and change mouse pointer to hand
                    tag.set_property("underline", Pango.Underline.SINGLE)
                    widget.get_window(Gtk.TextWindowType.TEXT).set_cursor(
                        Gdk.Cursor(Gdk.CursorType.HAND2))
                    self.underlined_url = tag
        return False

    def add_url(self, text, url, newline=False):
        """ Append URL to textbuffer and connect an event """
        # Try to see if we already got the current url as a tag
        tag = self._tags.lookup(text)
        if not tag:
            if yumex.misc.check_dark_theme():
                tag = self._buffer.create_tag(text,
                                              foreground="#4C4CFF")
            else:
                tag = self._buffer.create_tag(text,
                                              foreground="blue")
            tag.connect("event", self.on_url_event)
            self.url_tags.append(tag)
            self.url_list[text] = url
        self.write(text, style_name=text, newline=False)
        self.write(' ', style_name='describtion', newline=newline)


class PackageInfo(PackageDetails):
    '''
    class for handling the Package Information view
    '''

    def __init__(self, window, base):
        PackageDetails.__init__(self, window, self._url_handler)
        self.window = window
        self.base = base
        self.current_package = None
        self.active_filter = const.PKGINFO_FILTERS[0]
        self.connect('info-changed', self.on_filter_changed)
        self.update()

    def on_filter_changed(self, widget, data):
        self.active_filter = data
        self.update()

    def set_package(self, pkg):
        '''
        Set current active package to show information about in the
        Package Info view.

        :param pkg: package to set as active package
        '''
        self.current_package = pkg
        self.update()

    def update(self):
        '''
        update the information in the Package info view
        '''
        self.clear()
        if self.current_package:
            if self.active_filter == 'desc':
                self._show_description()
            elif self.active_filter == 'updinfo':
                self._show_updateinfo()

            elif self.active_filter == 'changelog':
                self._show_changelog()

            elif self.active_filter == 'files':
                self._show_filelist()

            elif self.active_filter == 'deps':
                self._show_requirements()
            else:
                logger.error("Package info not found: %s", self.active_filter)
        self.goto_top()

    def _url_handler(self, url):
        logger.debug('URL activated: ' + url)
        # just to be sure and prevent shell injection
        if yumex.misc.is_url(url):
            rc = subprocess.call("xdg-open '%s'" % url, shell=True)
            # failover to gtk.show_uri, if xdg-open fails or is not installed
            if rc != 0:
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            self.frontend.warning("%s is not an URL" % url)

    def _get_name_for_url(self):
        return urllib.parse.quote_plus(self.current_package.name)

    def _is_fedora_pkg(self):
        if self.current_package:
            if self.current_package.repository in const.FEDORA_REPOS:
                return True
        return False

    def _show_description(self):
        tags = self.current_package.pkgtags
        if tags:
            self.write(_("Tags: %s\n") %
                       ", ".join(tags), "changelog-header")
        desc = self.current_package.description
        self.write(desc)
        self.write('\n')
        self.write(_("Links: "), "changelog-header", newline=True)
        self.write('  ', newline=False)
        url_hp = self.current_package.URL
        self.add_url(url_hp, url_hp, newline=True)
        if self._is_fedora_pkg():
            self.write('  ', newline=False)
            url_fp = const.FEDORA_PACKAGES_URL + self._get_name_for_url()
            self.add_url(url_fp, url_fp, newline=True)
            self.base.set_working(False)

    def _show_updateinfo(self):
        self.base.set_working(True, False)
        updinfo = self.current_package.updateinfo
        if updinfo:
            updinfo.reverse()
            cnt = 0
            for info in updinfo:
                self._write_update_info(info)
                cnt += 1
                # only show max 3 advisories
                if cnt == 3:
                    break
        else:
            self.write(_("No update information is available"))
            if self._is_fedora_pkg():
                self.write(_("\nFedora Updates:"), "changelog-header",
                           newline=True)
                url = const.FEDORA_PACKAGES_URL + self._get_name_for_url() \
                                                + "/updates"
                self.add_url(url, url, newline=True)

        self.base.set_working(False, False)

    def _write_update_info(self, upd_info):
        head = ""
        head += ("%14s " % _("Release")) + ": %(id)s\n"
        head += ("%14s " % _("Type")) + ": "
        head += const.ADVISORY_TYPES[upd_info['type']] + "\n"
        #head += ("%14s " % _("Status")) + ": %(status)s\n"
        head += ("%14s " % _("Issued")) + ": %(updated)s\n"
        head = head % upd_info

        #if upd_info['updated'] and upd_info['updated'] != upd_info['issued']:
        #    head += "    Updated : %s" % upd_info['updated']

        self.write(head)
        head = ""

        # Add our bugzilla references
        if upd_info['references']:
            bzs = [r for r in upd_info['references']
                   if r and r[0] == hawkey.REFERENCE_BUGZILLA]
            if len(bzs):
                self.write('\n')
                header = "Bugzilla"
                for bz in bzs:
                    (typ, bug, title, url) = bz
                    bug_msg = '- %s' % title
                    self.write("%14s : " % header, newline=False)
                    self.add_url(bug, url)
                    self.write(bug_msg)
                    header = " "

        ## Add our CVE references
        #if upd_info['references']:
            #cves = [r for r in upd_info['references']
                    #if r and r['type'] == 'cve']
            #if len(cves):
                #cvelist = ""
                #header = "CVE"
                #for cve in cves:
                    #cvelist += "%14s : %s\n" % (header, cve['id'])
                    #header = " "
                #head += cvelist[:-1].rstrip() + '\n\n'

        desc = upd_info['description']
        head += "\n%14s : %s\n" % (_("Description"),
                                   yumex.misc.format_block(desc, 17))
        head += "\n"
        self.write(head)

    def _show_changelog(self):
        self.base.set_working(True, False)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.write(
                    "* %s %s" %
                    (datetime.date.fromtimestamp(c_date).isoformat(), c_ver),
                    "changelog-header")
                for line in msg.split('\n'):
                    self.write("%s" % line, "changelog")
                self.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        else:
            self.write(_("No changelog information is available"))
            if self._is_fedora_pkg():
                self.write(_("\nOnline Changelog:"), "changelog-header",
                           newline=True)
                url = const.FEDORA_PACKAGES_URL + self._get_name_for_url() \
                                                + "/changelog"
                self.add_url(url, url, newline=True)

        self.base.set_working(False, False)

    def _show_filelist(self):
        self.base.set_working(True, False)
        filelist = self.current_package.filelist
        if filelist:
            for fname in sorted(filelist):
                self.write(fname)
        else:
            self.write(_("No filelist information is available"))
        self.base.set_working(False, False)

    def _show_requirements(self):
        self.base.set_working(True, False)
        reqs = self.current_package.requirements
        for key in reqs:
            self.write(key)
            for pkg_id in reqs[key]:
                pkg = yumex.misc.id2fullname(pkg_id)
                self.write(' --> {}'.format(pkg))
        self.base.set_working(False, False)


class MainMenu(Gio.Menu):
    __gsignals__ = {'menu-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,
                                      GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, win):
        super(MainMenu, self).__init__()
        self.win = win
        self._button = self.win.get_ui('mainmenu_button')
        self._button.connect('clicked', self._on_button)
        self._popover = Gtk.Popover.new_from_model(self._button,
                                                   self)
        help_menu = Gio.Menu()
        self._add_menu(help_menu, _("About"), 'about')
        self._add_menu(help_menu, _("Documentation"), 'docs')
        self.append_section(_("Help"), help_menu)
        gen_menu = Gio.Menu()
        self._add_menu(gen_menu, _("Preferences"), 'pref')
        self._add_menu(gen_menu, _("Refresh Metadata"), 'reload')
        self._add_menu(gen_menu, _("Quit"), 'quit')
        self.append_section(None, gen_menu)

    def _add_menu(self, menu, label, name):
        # menu
        menu.append(label, 'win.{}'.format(name))
        # action
        action = Gio.SimpleAction.new(name, None)
        self.win.add_action(action)
        action.connect('activate', self._on_menu, name)
        return action

    def _on_menu(self, action, state, action_name):
        state = action.get_state()
        data = None
        if state == G_TRUE:
            action.change_state(G_FALSE)
            data = False
        elif state == G_FALSE:
            action.change_state(G_TRUE)
            data = True
        self.emit('menu-changed', action_name, data)

    def _on_button(self, button):
        self._popover.show_all()


class ExtraFilters(GObject.GObject):
    __gsignals__ = {'changed': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_STRING,
                                 GObject.TYPE_PYOBJECT,))
                    }

    def __init__(self, win):
        super(ExtraFilters, self).__init__()
        self.win = win
        self.all_archs = const.PLATFORM_ARCH
        self.current_archs = None
        self._button = self.win.get_ui('button_more_filters')
        self._button.connect('clicked', self._on_button)
        self._popover = self.win.get_ui('more_filters_popover')
        self._arch_box = self.win.get_ui('box_archs')
        self._setup_archs()
        self.newest_only = self.win.get_ui('cb_newest_only')
        self.newest_only.set_active(CONFIG.conf.newest_only)
        self.newest_only.connect('toggled', self._on_newest)

    def popup(self):
        self._on_button(self._button)

    def _on_button(self, button):
        self._popover.show_all()

    def _setup_archs(self):
        if not CONFIG.conf.archs:
            CONFIG.conf.archs = list(self.all_archs)
            CONFIG.write()
        self.current_archs = set(CONFIG.conf.archs)
        for arch in self.all_archs:
            cb = Gtk.CheckButton(label=arch)
            self._arch_box.pack_start(cb, True, True, 0)
            if arch in CONFIG.conf.archs:
                cb.set_active(True)
            else:
                cb.set_active(False)
            cb.show()
            cb.connect('toggled', self._on_arch)

    def _on_arch(self, widget):
        state = widget.get_active()
        label = widget.get_label()
        if state:
            self.current_archs.add(label)
        else:
            self.current_archs.remove(label)
        CONFIG.conf.archs = list(self.current_archs)
        CONFIG.write()
        self.emit("changed", 'arch', list(self.current_archs))

    def _on_newest(self, widget):
        state = widget.get_active()
        self.emit('changed', 'newest_only', state)

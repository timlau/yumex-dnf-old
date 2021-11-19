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

import datetime
import logging
import subprocess
import urllib.parse

import hawkey
import yumex.common.const as const
from gi.repository import Gdk, GObject, Gtk, Pango
from yumex.common import (_, check_dark_theme, format_block, is_url,
                          pkg_id_to_full_name)

logger = logging.getLogger('yumex.gui.widget')


class PackageDetails(GObject.GObject):
    __gsignals__ = {
        'info-changed':
        (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING, ))
    }

    VALUES = {0: 'desc', 1: 'updinfo', 2: 'files', 3: 'deps'}
    DEFAULT_STYLES = [
        'description', 'filelist', 'changelog', 'changelog-header'
    ]

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
        self._listbox.select_row(self.win.get_ui('list_desc'))

    def set_active(self, key):
        """Set the active item based on key."""
        if key in ('desc', 'updinfo', 'files', 'deps'):
            self._listbox.select_row(self.win.get_ui(f'list_{key}'))

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
           check_dark_theme():
            tag_name += '_dark'
        style = self._tags.lookup(tag_name)
        return style

    def write(self, txt, style_name=None, newline=True):
        if not txt:
            return
        if newline and txt[-1] != '\n':
            txt += '\n'
        _, end = self._buffer.get_bounds()
        if style_name:
            style = self.get_style(style_name)
        else:
            style = self.get_style('description')
        if style:
            self._buffer.insert_with_tags(end, txt, style)
        else:
            self._buffer.insert(end, txt)
        self._text.scroll_to_iter(self._buffer.get_end_iter(), 0.0, True, 0.0,
                                  0.0)

    def clear(self):
        self._buffer.set_text('')

    def goto_top(self):
        self._text.scroll_to_iter(self._buffer.get_start_iter(), 0.0, False,
                                  0.0, 0.0)

    def on_url_event(self, tag, widget, event, iterator):
        """ Catch when the user clicks the URL """
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            url = self.url_list[tag.get_property("name")]
            if self._url_handler:
                self._url_handler(url)

    def on_mouse_motion(self, widget, event, data=None):
        """
        Mouse movement handler for TextView

        :param widget:
        :param event:
        :param data:
        """
        window = widget.get_window(Gtk.TextWindowType.WIDGET)
        # Get x,y pos for widget
        _, x, y, _ = window.get_pointer()
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
            if check_dark_theme():
                tag = self._buffer.create_tag(text, foreground="#ff7800")
            else:
                tag = self._buffer.create_tag(text, foreground="#ff7800")
            tag.connect("event", self.on_url_event)
            self.url_tags.append(tag)
            self.url_list[text] = url
        self.write(text, style_name=text, newline=False)
        self.write(' ', style_name='describtion', newline=newline)


class PackageInfo(PackageDetails):
    """
    class for handling the Package Information view
    """
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
        """
        Set current active package to show information about in the
        Package Info view.

        :param pkg: package to set as active package
        """
        self.current_package = pkg
        self.win.set_working(True, True)
        self.update()
        self.win.set_working(False)

    def update(self):
        """
        update the information in the Package info view
        """
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
                logger.error(f"Package info not found: {self.active_filter}")
        self.goto_top()

    # pylint: disable=method-hidden
    def _url_handler(self, url):
        logger.debug('URL activated: {url}')
        # just to be sure and prevent shell injection
        if is_url(url):
            rc = subprocess.run("xdg-open", f"'{url}'", check=False)
            # failover to gtk.show_uri, if xdg-open fails or is not installed
            if rc != 0:
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            self.frontend.warning(f"%s is not an {url}")  #pylint: disable=no-member

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
            self.write(_("Tags: %s\n") % ", ".join(tags), "changelog-header")
        desc = self.current_package.description
        self.write(desc)
        self.write('\n')
        self.write(_("Links: "), "changelog-header", newline=True)
        self.write('  ', newline=False)
        url_hp = self.current_package.url
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
                self.write(_("\nFedora Updates:"),
                           "changelog-header",
                           newline=True)
                url = const.FEDORA_PACKAGES_URL + self._get_name_for_url() \
                                                + "/updates"
                self.add_url(url, url, newline=True)

        self.base.set_working(False, False)

    def _write_update_info(self, upd_info):
        head = ""
        # pylint: disable=consider-using-f-string
        head += ("%14s " % _("Release")) + ": %(id)s\n"
        head += ("%14s " % _("Type")) + ": "
        head += const.ADVISORY_TYPES[upd_info['type']] + "\n"
        head += ("%14s " % _("Issued")) + ": %(updated)s\n"
        head = head % upd_info

        # if upd_info['updated'] and upd_info['updated'] != upd_info['issued']:
        #    head += "    Updated : %s" % upd_info['updated']

        self.write(head, 'filelist')
        head = ""

        # Add our bugzilla references
        if upd_info['references']:
            bzs = [
                r for r in upd_info['references']
                if r and r[0] == hawkey.REFERENCE_BUGZILLA
            ]
            if len(bzs):
                self.write('\n')
                # pylint: disable=unused-variable
                header = "Bugzilla"
                for bz in bzs:
                    (_typ, bug, title, url) = bz
                    bug_msg = f'- {title}'
                    self.write("{header} : ", 'filelist', newline=False)
                    self.add_url(bug, url)
                    self.write(bug_msg, 'filelist')
                    header = " "

        desc = upd_info['description']
        head += f'\n{_("Description"):14} : {format_block(desc, 17)}\n'
        head += "\n"
        self.write(head, 'filelist')

    def _show_changelog(self):
        self.base.set_working(True, False)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                # pylint: disable=consider-using-f-string
                self.write(
                    "* %s %s" %
                    (datetime.date.fromtimestamp(c_date).isoformat(), c_ver),
                    "changelog-header")
                for line in msg.split('\n'):
                    self.write(line, "changelog")
                self.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        else:
            self.write(_("No changelog information is available"))
            if self._is_fedora_pkg():
                self.write(_("\nOnline Changelog:"),
                           "changelog-header",
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
                self.write(fname, 'filelist')
        else:
            self.write(_("No filelist information is available"))
        self.base.set_working(False, False)

    def _show_requirements(self):
        self.base.set_working(True, False)
        reqs = self.current_package.requirements
        if reqs:
            for key in reqs:
                self.write(key, 'filelist')
                for pkg_id in reqs[key]:
                    pkg = pkg_id_to_full_name(pkg_id)
                    self.write(f' --> {pkg}', 'filelist')
        self.base.set_working(False, False)

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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gio
from yumex.misc import _, CONFIG

import datetime
import hawkey
import logging
import re
import subprocess
import urllib.parse


import yumex.const as const
import yumex.gui.views
import yumex.misc

logger = logging.getLogger('yumex.gui.widget')


class InfoProgressBar:

    def __init__(self, ui):
        self.ui = ui
        self.infobar = ui.get_object("infobar")  # infobar revealer
        frame = ui.get_object("info_frame")
        new_bg = Gdk.RGBA()
        if yumex.misc.check_dark_theme():
            new_bg.parse("rgb(0,0,0)")
        else:
            new_bg.parse("rgb(255,255,255)")
        frame.override_background_color(Gtk.StateFlags.NORMAL, new_bg)
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")

    def _show_infobar(self, show=True):
        self.infobar.set_reveal_child(show)

    def show_progress(self, state):
        if state:
            self.show_label()
        else:
            self.hide()

    def hide(self):
        self.label.hide()
        self.sublabel.hide()
        self.progress.hide()
        self._show_infobar(False)
        self.progress.set_text("")
        #self.progress.set_show_text (False)

    def hide_sublabel(self):
        self.sublabel.hide()

    def show_label(self):
        self.label.show()
        self.label.set_text("")

    def show_sublabel(self):
        self.sublabel.show()
        self.sublabel.set_text("")

    def show_all(self):
        self.show_label()
        self.show_sublabel()
        self.progress.show()

    def info(self, msg):
        self._show_infobar(True)
        self.show_label()
        self.label.set_text(msg)

    def info_sub(self, msg):
        self._show_infobar(True)
        self.show_sublabel()
        self.sublabel.set_text(msg)

    def set_progress(self, frac, label=None):
        if label:
            self.progress.set_text(label)
        if frac >= 0.0 and frac <= 1.0:
            self.infobar.show()
            self.progress.show()
            self.progress.set_fraction(frac)
            # make sure that the main label is shown, else the progres
            # looks bad. this is normally happen when changlog
            # or filelist info is needed for at package
            # and it will trigger the yum daemon to download the need metadata.
            if not self.label.get_property('visible'):
                self.info(_("Getting Package Metadata"))


class ArchMenu(GObject.GObject):
    '''
    Class to handle a menu to select what arch to show in package view
    '''
    __gsignals__ = {'arch-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,))}

    def __init__(self, arch_menu_widget, archs):
        GObject.GObject.__init__(self)
        self.all_archs = archs
        self.arch_menu_widget = arch_menu_widget
        if not CONFIG.conf.archs:
            CONFIG.conf.archs = list(archs)
            CONFIG.write()
        self.current_archs = set(CONFIG.conf.archs)
        self.arch_menu = self._setup_archmenu()

    def _setup_archmenu(self):
        arch_menu = self.arch_menu_widget
        for arch in self.all_archs:
            cb = Gtk.CheckMenuItem()
            cb.set_label(arch)
            if arch in CONFIG.conf.archs:
                cb.set_active(True)
            else:
                cb.set_active(False)
            cb.show()
            cb.connect('toggled', self.on_archmenu_clicked)
            arch_menu.add(cb)

        return arch_menu

    def on_arch_clicked(self, button, event=None):
        #print('clicked : event : %s' % event.button)
        if event.button == 1:  # Left click
            self.arch_menu.popup(
                None, None, None, None, event.button, event.time)
            return True

    def on_archmenu_clicked(self, widget):
        state = widget.get_active()
        label = widget.get_label()
        if state:
            self.current_archs.add(label)
        else:
            self.current_archs.remove(label)
        archs = ",".join(list(self.current_archs))
        CONFIG.conf.archs = list(self.current_archs)
        CONFIG.write()
        self.emit("arch-changed", archs)


class PackageInfoWidget(Gtk.Box):
    __gsignals__ = {'info-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,))
                    }

    def __init__(self, window, url_handler):
        Gtk.Box.__init__(self)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        # PKGINFO_FILTERS = ['desc', 'updinfo', 'changelog', 'files', 'deps']
        tip = _("Package Description")
        rb = self._get_radio_button('dialog-information-symbolic', "desc",
                                    tooltip=tip)
        vbox.add(rb)
        tip = _("Package Update Information")
        vbox.add(self._get_radio_button(
            'software-update-available-symbolic', "updinfo", rb, tip))
        #tip = _("Package Changelog")
        #vbox.add(self._get_radio_button(
            #'bookmark-new-symbolic', "changelog", rb, tip))
        tip = _("Package Filelist")
        vbox.add(self._get_radio_button(
            'drive-multidisk-symbolic', "files", rb, tip))
        tip = _("Package Requirements")
        vbox.add(self._get_radio_button('insert-object-symbolic', "deps", rb,
                                        tip))
        vbox.set_margin_right(5)
        self.pack_start(vbox, False, False, 0)
        sw = Gtk.ScrolledWindow()
        self.view = yumex.gui.views.PackageInfoView(window, url_handler)
        sw.add(self.view)
        self.pack_start(sw, True, True, 0)

    def _get_radio_button(self, icon_name, name, group=None, tooltip=None):
        if group:
            wid = Gtk.RadioButton.new_from_widget(group)
        else:
            wid = Gtk.RadioButton.new(None)
        icon = Gio.ThemedIcon(name=icon_name)
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
        wid.set_image(image)
        if tooltip:
            wid.set_tooltip_text(tooltip)
        wid.connect('toggled', self._on_filter_changed, name)
        # we only want an image, not the black dot indicator
        wid.set_property("draw-indicator", False)
        return wid

    def _on_filter_changed(self, button, data):
        '''
        Radio Button changed handler
        Change the info in the view to match the selection
Gtk.Image()
        :param button:
        :param data:
        '''
        if button.get_active():
            logger.debug("pkginfo: %s selected" % data)
            self.emit("info-changed", data)


class PackageInfo(PackageInfoWidget):
    '''
    class for handling the Package Information view
    '''

    def __init__(self, window, base):
        PackageInfoWidget.__init__(self, window, url_handler=self._url_handler)
        self.set_name('YumexPackageInfo')
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
        self.view.clear()
        self.view.write("\n")
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
                print("Package info not found: ", self.active_filter)
        self.view.goTop()

    def _is_url(self, url):
        urls = re.findall(
            '^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|'
            '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url)
        if urls:
            return True
        else:
            return False

    def _url_handler(self, url):
        print('URL activated: ' + url)
        if self._is_url(url):  # just to be sure and prevent shell injection
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
            self.view.write(_("Tags: %s\n") %
                            ", ".join(tags), "changelog-header")
        desc = self.current_package.description
        self.view.write(desc)
        self.view.write('\n')
        self.view.write(_("Links: "), "changelog-header", newline=True)
        self.view.write('  ', newline=False)
        url_hp = self.current_package.URL
        self.view.add_url(url_hp, url_hp, newline=True)
        if self._is_fedora_pkg():
            self.view.write('  ', newline=False)
            url_fp = const.FEDORA_PACKAGES_URL + self._get_name_for_url()
            self.view.add_url(url_fp, url_fp, newline=True)
            self.base.set_working(False)

    def _show_updateinfo(self):
        self.base.set_working(True)
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
            self.view.write(_("No update information is available"))
            if self._is_fedora_pkg():
                self.view.write(_("\nFedora Updates:"), "changelog-header",
                                newline=True)
                url = const.FEDORA_PACKAGES_URL + self._get_name_for_url() \
                                                + "/updates"
                self.view.add_url(url, url, newline=True)

        self.base.set_working(False)

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

        self.view.write(head)
        head = ""

        # Add our bugzilla references
        if upd_info['references']:
            bzs = [r for r in upd_info['references']
                   if r and r[0] == hawkey.REFERENCE_BUGZILLA]
            if len(bzs):
                self.view.write('\n')
                header = "Bugzilla"
                for bz in bzs:
                    (typ, bug, title, url) = bz
                    bug_msg = '- %s' % title
                    self.view.write("%14s : " % header, newline=False)
                    self.view.add_url(bug, url)
                    self.view.write(bug_msg)
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
        self.view.write(head)

    def _show_changelog(self):
        self.base.set_working(True)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.view.write(
                    "* %s %s" %
                    (datetime.date.fromtimestamp(c_date).isoformat(), c_ver),
                    "changelog-header")
                for line in msg.split('\n'):
                    self.view.write("%s" % line, "changelog")
                self.view.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        else:
            self.view.write(_("No changelog information is available"))
            if self._is_fedora_pkg():
                self.view.write(_("\nOnline Changelog:"), "changelog-header",
                                newline=True)
                url = const.FEDORA_PACKAGES_URL + self._get_name_for_url() \
                                                + "/changelog"
                self.view.add_url(url, url, newline=True)

        self.base.set_working(False)

    def _show_filelist(self):
        self.base.set_working(True)
        filelist = self.current_package.filelist
        if filelist:
            for fname in sorted(filelist):
                self.view.write(fname)
        else:
            self.view.write(_("No filelist information is available"))
        self.base.set_working(False)

    def _show_requirements(self):
        self.base.set_working(True)
        reqs = self.current_package.requirements
        for key in reqs:
            self.view.write(key)
            for pkg_id in reqs[key]:
                pkg = yumex.misc.id2fullname(pkg_id)
                self.view.write(' --> {}'.format(pkg))
        self.base.set_working(False)


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
        self.search_type = 'prefix'
        self.search_fields = ['name', 'summary']
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
        self._set_fields_sensitive(False)
        # setup search type radiobuttons
        for key in SearchBar.TYPES:
            wid = self.win.get_ui('sch_opt_%s' % key)
            if key == self.search_type:
                wid.set_active(True)
            wid.connect('toggled', self.on_type_changed, key)
        # setup search option popover
        self.opt_popover = Gtk.Popover.new(self._options_button)
        self.opt_popover.set_size_request(50, 100)
        self.opt_popover.set_position(Gtk.PositionType.BOTTOM)
        opt_grid = self.win.get_ui('sch_opt_grid')
        self.opt_popover.add(opt_grid)

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
            if self.search_type == 'fields':
                self._set_fields_sensitive(True)
            else:
                self._set_fields_sensitive(False)

    def on_fields_changed(self, widget, key):
        """Search fields is changed."""
        self.search_fields = self._get_active_field()

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


class Options(GObject.GObject):
    """Handling the mainmenu options"""

    __gsignals__ = {'option-changed': (GObject.SignalFlags.RUN_FIRST,
                                       None,
                                       (GObject.TYPE_STRING,
                                        GObject.TYPE_BOOLEAN,)
                                       )}

    OPTIONS = ['newest_only', 'clean_unused', 'clean_instonly']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        for key in Options.OPTIONS:
            wid = self.win.get_ui('option_%s' % key)
            wid.set_active(getattr(CONFIG.session, key))
            wid.connect('toggled', self.on_toggled, key)

    def on_toggled(self, widget, flt):
        """An option is changed."""
        self.emit('option-changed', flt, widget.get_active())


class SidebarSelector(Gtk.Revealer):
    """Sidebar selector widget. """

    __gsignals__ = {'sidebar-changed': (GObject.SignalFlags.RUN_FIRST,
                                       None,
                                       (GObject.TYPE_STRING,)
                                       )}

    def __init__(self, parent):
        Gtk.Revealer.__init__(self)
        self._lb = Gtk.ListBox()
        self._lb.get_style_context().add_class('sidebar')
        self._lb.props.width_request = 100
        self._lb.set_vexpand(True)
        self.add(self._lb)
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.set_transition_duration(250)
        self._parent = parent
        self._rows = {}
        self._keys = {}
        self.ndx = -1
        self._current = None
        self._lb.unselect_all()
        self._lb.connect('row-selected', self.on_toggled)
        self.show_all()
        self.set_reveal_child(True)
        self._parent.add(self)

    def show_bar(self, show=True):
        """Show or hide the sidebar."""
        self.set_reveal_child(show)

    def on_toggled(self, widget, row):
        """Active filter is changed."""
        if row:
            ndx = row.get_index()
            key = self._keys[ndx]
            if key != self._current:
                self.emit('sidebar_changed', key)
                self._current = key

    def add_row(self, key, txt):
        """Add a row to the sidebar."""
        self.ndx += 1
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        hbox.props.margin_left = 6
        row.add(hbox)
        label = Gtk.Label(txt, xalign=0)
        hbox.pack_start(label, True, True, 0)
        self._keys[self.ndx] = key
        self._rows[key] = row
        self._lb.add(row)
        row.show()

    def set_active(self, key):
        """Set the active item based on key."""
        row = self._rows[key]
        self._lb.select_row(row)

    def get_visible(self):
        """Check if sidebar is shown or hidden."""
        return self.get_reveal_child()


class Filters(GObject.GObject):
    """Handling the package filter UI."""

    __gsignals__ = {'filter-changed': (GObject.SignalFlags.RUN_FIRST,
                                       None,
                                       (GObject.TYPE_STRING,)
                                       )}

    FILTERS = ['updates', 'installed', 'available', 'all']
    LABELS = {
                'updates': _('Updates'),
                'installed': _('Installed'),
                'available': _('Available'),
                'all': _('All'),
    }

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self._sidebar = SidebarSelector(self.win.get_ui('sidebar'))
        self.current = 'updates'
        for flt in Filters.FILTERS:
            self._sidebar.add_row(flt, Filters.LABELS[flt])
        self._sidebar.connect('sidebar-changed', self.on_toggled)
        self._sidebar.set_active(self.current)
        self.is_visible = True

    def show(self, show=True):
        if show != self.is_visible:
            self._sidebar.show_bar(show)
            self.is_visible = show

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

    MENUS = ['packages', 'groups', 'history', 'actions']

    def __init__(self, win):
        GObject.GObject.__init__(self)
        self.win = win
        self._stack = self.win.get_ui('main_stack')
        self.switcher = self.win.get_ui('main_switcher')
        # catch changes in active page in stack
        self._stack.connect('notify::visible-child', self.on_switch)
        for key in Content.MENUS:
            wid = self.win.get_ui('main_%s' % key)
            wid.connect('activate', self.on_menu_select, key)

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

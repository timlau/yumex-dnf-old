# -*- coding: utf-8 -*-
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
from gi.repository import GObject
from yumex import const
from yumex.misc import _, CONFIG

import logging
import os
import shutil
import yumex.gui.views
import yumex.misc

logger = logging.getLogger('yumex.gui.dialogs')


class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'Yum Extender (dnf)'
        self.props.version = const.VERSION
        self.props.authors = ['Tim Lauridsen <timlau@fedoraproject.org>']
        self.props.license_type = Gtk.License.GPL_2_0
        self.props.copyright = '(C) 2015 Tim Lauridsen'
        self.props.website = 'https://github.com/timlau/yumex-dnf'
        self.props.logo_icon_name = 'yumex-dnf'
        self.set_transient_for(parent)


class Preferences:

    VALUES = ['update_interval', 'refresh_interval', 'installonly_limit']
    COLORS = ['color_install', 'color_update', 'color_normal',
                     'color_obsolete', 'color_downgrade']
    FLAGS = ['autostart', 'clean_unused', 'newest_only',
             'headerbar', 'auto_select_updates', 'repo_saved', 'clean_instonly'
            ]

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("preferences")
        self.dialog.set_transient_for(base)
        self.repo_view = yumex.gui.views.RepoView()
        widget = self.base.ui.get_object('repo_sw')
        widget.add(self.repo_view)
        self.repos = []

    def run(self):
        self.get_settings()
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        need_reset = False
        if rc == 1:
            need_reset = self.set_settings()
        return need_reset

    def get_settings(self):
        # set boolean states
        for option in Preferences.FLAGS:
            logger.debug("%s : %s " % (option, getattr(CONFIG.conf, option)))
            widget = self.base.ui.get_object('pref_' + option)
            widget.set_active(getattr(CONFIG.conf, option))
        # cleanup installonly handler
        widget = self.base.ui.get_object('pref_clean_instonly')
        widget.connect('notify::active', self.on_clean_instonly)
        # set colors states
        for name in Preferences.COLORS:
            rgba = yumex.misc.get_color(getattr(CONFIG.conf, name))
            widget = self.base.ui.get_object(name)
            widget.set_rgba(rgba)
        # Set value states
        for name in Preferences.VALUES:
            widget = self.base.ui.get_object('pref_' + name)
            widget.set_value(getattr(CONFIG.conf, name))
        self.on_clean_instonly()
        # get the repositories
        self.repos = self.base.backend.get_repositories()
        self.repo_view.populate(self.repos)
        if CONFIG.conf.repo_saved:
            self.repo_view.select_by_keys(CONFIG.session.enabled_repos)

    def on_clean_instonly(self, *args):
        '''Handler for clean_instonly switch'''
        widget = self.base.ui.get_object('pref_clean_instonly')
        state = widget.get_active()
        postfix = 'installonly_limit'
        self._set_sensitive(postfix, state)

    def _set_sensitive(self, postfix, state):
        for prefix in ['pref_', 'label_']:
            id_ = prefix + postfix
            if state:
                self.base.ui.get_object(id_).set_sensitive(True)
            else:
                self.base.ui.get_object(id_).set_sensitive(False)

    def set_settings(self):
        changed = False
        need_reset = False
        # handle boolean options
        for option in Preferences.FLAGS:
            widget = self.base.ui.get_object('pref_' + option)
            state = widget.get_active()
            if state != getattr(CONFIG.conf, option):  # changed ??
                setattr(CONFIG.conf, option, state)
                changed = True
                self.handle_setting(option, state)
        # handle color options
        for name in Preferences.COLORS:
            widget = self.base.ui.get_object(name)
            rgba = widget.get_rgba()
            color = yumex.misc.color_to_hex(rgba)
            if color != getattr(CONFIG.conf, name):  # changed ??
                setattr(CONFIG.conf, name, color)
                changed = True
        # handle value options
        for name in Preferences.VALUES:
            widget = self.base.ui.get_object('pref_' + name)
            value = widget.get_value_as_int()
            if value != getattr(CONFIG.conf, name):  # changed ??
                setattr(CONFIG.conf, name, value)
                changed = True
        # handle repos
        repo_before = CONFIG.session.enabled_repos
        repo_now = self.repo_view.get_selected()
        # repo selection changed
        if repo_now != repo_before:
            CONFIG.session.enabled_repos = repo_now     # set the new selection
            # we need to reset the gui
            need_reset = True
            if CONFIG.conf.repo_saved:
                CONFIG.conf.repo_enabled = repo_now
                changed = True
        if changed:
            CONFIG.write()
        return need_reset

    def handle_setting(self, option, state):
        if option == 'autostart':
            if state:  # create an autostart .desktop for current user
                if not os.path.isdir(const.AUTOSTART_DIR):
                    logger.info("creating autostart directory : %s",
                                const.AUTOSTART_DIR)
                    os.makedirs(const.AUTOSTART_DIR, 0o700)
                shutil.copy(const.SYS_DESKTOP_FILE, const.USER_DESKTOP_FILE)
            else:  # remove the autostart file
                if os.path.exists(const.USER_DESKTOP_FILE):
                    os.unlink(const.USER_DESKTOP_FILE)


class ErrorDialog:

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("error_dialog")
        self.dialog.set_transient_for(base)
        self._buffer = self.base.ui.get_object('error_buffer')

    def show(self, txt):
        self._set_text(txt)
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        self._buffer.set_text('')
        return rc == 1

    def _set_text(self, txt):
        self._buffer.set_text(txt)


class TransactionResult:

    def __init__(self, base):
        self.base = base
        self.dialog = self.base.ui.get_object("transaction-results")
        self.dialog.set_transient_for(base)
        self.view = self.base.ui.get_object("result_view")
        self.store = self.setup_view(self.view)

    def run(self):
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        return rc == 1

    def clear(self):
        self.store.clear()

    def _fullname(self, pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s" % (n, e, v, r, a)
        else:
            return "%s-%s-%s.%s" % (n, v, r, a)

    def setup_view(self, view):
        '''
        Setup the TreeView
        @param view: the TreeView widget
        '''
        model = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_STRING,
                              GObject.TYPE_STRING, GObject.TYPE_STRING,
                              GObject.TYPE_STRING)
        view.set_model(model)
        self.create_text_column(_("Name"), view, 0, size=250)
        self.create_text_column(_("Arch"), view, 1)
        self.create_text_column(_("Ver"), view, 2)
        self.create_text_column(_("Repository"), view, 3, size=100)
        self.create_text_column(_("Size"), view, 4)
        return model

    def create_text_column(self, hdr, view, colno, size=None):
        '''
        Create at TreeViewColumn
        @param hdr: column header text
        @param view: the TreeView widget
        @param colno: the TreeStore column containing data for the column
        @param min_width: the min column view (optional)
        '''
        cell = Gtk.CellRendererText()  # Size Column
        column = Gtk.TreeViewColumn(hdr, cell, markup=colno)
        column.set_resizable(True)
        if size:
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_fixed_width(size)
        view.append_column(column)

    def populate(self, pkglist, dnl_size):
        '''
        Populate the TreeView with data
        @param pkglist: list containing view data
        '''
        model = self.store
        self.store.clear()
        total_size = 0
        for sub, lvl1 in pkglist:
            label = "<b>%s</b>" % const.TRANSACTION_RESULT_TYPES[sub]
            level1 = model.append(None, [label, "", "", "", ""])
            for id, size, replaces in lvl1:
                (n, e, v, r, a, repo_id) = str(id).split(',')
                level2 = model.append(
                    level1, [n, a, "%s.%s" % (v, r), repo_id,
                    yumex.misc.format_number(size)])
                # packages there need to be downloaded
                if sub in ['install', 'update', 'install-deps',
                           'update-deps', 'obsoletes']:
                    total_size += size
                for r in replaces:
                    (n, e, v, r, a, repo_id) = str(r).split(',')
                    model.append(level2, [_("<b>replacing</b> {}").format(n),
                                           a, "%s.%s" % (v, r), repo_id,
                                          yumex.misc.format_number(size)])
        self.base.ui.get_object("result_size").set_text(
            yumex.misc.format_number(total_size))
        self.view.expand_all()


def show_information(window, msg, add_msg=None):
    dialog = Gtk.MessageDialog(
        flags=0, message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK, text=msg)
    if add_msg:
        dialog.format_secondary_text(add_msg)
    if window:
        dialog.set_transient_for(window)
    dialog.run()
    dialog.destroy()


def yes_no_dialog(window, msg, add_msg=None):
    dialog = Gtk.MessageDialog(
        flags=0, message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.YES_NO, text=msg)
    if add_msg:
        dialog.format_secondary_text(add_msg)
    if window:
        dialog.set_transient_for(window)
    rc = dialog.run()
    dialog.destroy()
    return(rc == Gtk.ResponseType.YES)


def ask_for_gpg_import(window, values):
    (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
    pkg_name = pkg_id.split(',')[0]
    msg = (_(' Do you want to import this GPG key\n'
             ' needed to verify the %s package?\n\n'
             ' Key        : 0x%s:\n'
             ' Userid     : "%s"\n'
             ' From       : %s') %
          (pkg_name, hexkeyid, userid,
           keyurl.replace("file://", "")))

    dialog = Gtk.MessageDialog(
        window, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, msg)
    rc = dialog.run()
    dialog.destroy()
    return rc == Gtk.ResponseType.YES

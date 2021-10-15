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


import glob
import logging
import os
import shutil

from gi.repository import GObject, Gtk
from yumex import const
from yumex.misc import CONFIG, _, format_number

from .views import RepoView

logger = logging.getLogger('yumex.gui.dialogs')


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
        return rc == Gtk.ResponseType.OK

    def clear(self):
        self.store.clear()

    def setup_view(self, view):
        """
        Setup the TreeView
        @param view: the TreeView widget
        """
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
        """
        Create at TreeViewColumn
        @param hdr: column header text
        @param view: the TreeView widget
        @param colno: the TreeStore column containing data for the column
        @param size: the min column view (optional)
        """
        cell = Gtk.CellRendererText()  # Size Column
        column = Gtk.TreeViewColumn(hdr, cell, markup=colno)
        column.set_resizable(True)
        if size:
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_fixed_width(size)
        view.append_column(column)

    def populate(self, pkglist, dnl_size):
        """
        Populate the TreeView with data
        @param pkglist: list containing view data
        @param dnl_size:
        """
        model = self.store
        self.store.clear()
        total_size = 0
        for sub, lvl1 in pkglist:
            label = "<b>%s</b>" % const.TRANSACTION_RESULT_TYPES[sub]
            level1 = model.append(None, [label, "", "", "", ""])
            for pkgid, size, replaces in lvl1:
                (n, e, v, r, a, repo_id) = str(pkgid).split(',')
                level2 = model.append(
                    level1, [n, a, "%s.%s" % (v, r), repo_id,
                             format_number(size)])
                # packages there need to be downloaded
                if sub in ['install', 'update', 'install-deps',
                           'update-deps', 'obsoletes']:
                    total_size += size
                for r in replaces:
                    (n, e, v, r, a, repo_id) = str(r).split(',')
                    model.append(level2, [_("<b>replacing</b> {}").format(n),
                                          a, "%s.%s" % (v, r), repo_id,
                                          format_number(size)])
        self.base.ui.get_object("result_size").set_text(
            format_number(total_size))
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
    return rc == Gtk.ResponseType.YES


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

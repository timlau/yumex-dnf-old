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


import logging

from gi.repository import Gtk
from yumex.misc import CONFIG, _, format_number


logger = logging.getLogger('yumex.gui.dialogs')


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

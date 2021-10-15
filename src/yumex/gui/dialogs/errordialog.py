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

from gi.repository import  Gtk
from yumex.common import load_ui


class ErrorDialog:

    def __init__(self, base):
        self.ui = load_ui('errordialog.ui')
        self.dialog = self.ui.get_object("error_dialog")
        self.dialog.set_transient_for(base)
        self._buffer = self.ui.get_object('error_buffer')

    def show(self, txt):
        self._set_text(txt)
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        self._buffer.set_text('')
        return rc == Gtk.ResponseType.CLOSE

    def _set_text(self, txt):
        self._buffer.set_text(txt)

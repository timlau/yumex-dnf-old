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

import yumex.common.const as const
from yumex.gui import load_ui


class ProgressSplash:
    def __init__(self, base):
        self.base = base
        self.ui = load_ui("progresssplash.ui")
        self.win = self.ui.get_object("win_working")
        pix = self.ui.get_object("work_pix")
        pix_file = f"{const.PIX_DIR}/progress.gif"
        pix.set_from_file(pix_file)
        self.label = self.ui.get_object("work_label")
        self.sublabel = self.ui.get_object("work_sublabel")
        self.win.set_transient_for(self.base)

    def show(self):
        self.win.show()

    def hide(self):
        self.win.hide()

    def set_label(self, text):
        self.label.set_text(text)

    def set_sublabel(self, text):
        self.sublabel.set_text(text)

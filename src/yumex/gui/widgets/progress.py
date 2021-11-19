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

from yumex.common import _


class Progress:
    def __init__(self, ui, base):
        self.base = base
        self.ui = ui
        self._is_visible = False
        self.infobar = ui.get_object("info_revealer")  # infobar revealer
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")
        self.spinner = ui.get_object("info_spinner")

    def _show_infobar(self, show=True):
        """ Show or hide the info bar"""
        if show == self._is_visible:  # check if infobar already is in the wanted state
            return
        self.infobar.set_reveal_child(show)
        if show:
            self.infobar.show()
            self.spinner.start()
            self.progress.show()
            self.progress.set_show_text(False)
            self.label.show()
            self.sublabel.show()
            self.label.set_text("")
            self.sublabel.set_text("")
            self._is_visible = True
        else:
            self.spinner.stop()
            self.infobar.hide()
            self.label.hide()
            self.sublabel.hide()
            self.progress.hide()
            self.progress.set_show_text(False)
            self._is_visible = False

    def hide(self):
        self._show_infobar(False)

    def message(self, msg):
        self._show_infobar(True)
        self.label.set_text(msg)
        if hasattr(self.base, 'working_splash'):
            self.base.working_splash.set_label(msg)
            self.base.working_splash.set_sublabel("")

    def message_sub(self, msg):
        self._show_infobar(True)
        self.sublabel.set_text(msg)
        if hasattr(self.base, 'working_splash'):
            self.base.working_splash.set_sublabel(msg)

    def check_info(self):
        if self.label.get_text() == "":
            self.message(_("Getting Package Metadata"))

    #pylint: disable=unused-argument
    def set_progress(self, frac, label=None):
        if 0.0 <= frac <= 1.0:
            self._show_infobar()
            self.progress.set_fraction(frac)
            # make sure that the main label is shown, else the progress
            # looks bad. this normally happens when changlog or filelist info
            # is needed for a package and it will trigger the yum daemon to
            # download the need metadata.
            self.check_info()

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
from gi.repository import GObject
from yumex.common import _

logger = logging.getLogger('yumex.gui.widget')


class Content(GObject.GObject):
    """Handling the content pages"""

    __gsignals__ = {
        'page-changed':
        (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING, ))
    }

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

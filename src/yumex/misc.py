# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


from gi.repository import Gtk
from gi.repository import Gdk


def format_block(block, indent):
        ''' Format a block of text so they get the same indentation'''
        spaces = " " * indent
        lines = str(block).split('\n')
        result = lines[0]+"\n"
        for line in lines[1:]:
            result += spaces + line + '\n'
        return result        

def show_information(window, msg, add_msg = None):
    dialog = Gtk.MessageDialog(window, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, msg)
    if add_msg:
        dialog.format_secondary_text(add_msg)
    dialog.run()
    dialog.destroy()


def doGtkEvents():
    '''

    '''
    while Gtk.events_pending():      # process Gtk events
        Gtk.main_iteration()


def busyCursor(base, insensitive=False):
    ''' Set busy cursor in mainwin and make it insensitive if selected '''
    win = base.window.get_window()
    if win != None:
        win.set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        if insensitive:
            #base.window.set_sensitive(False)
            for widget in ['main_vpaned', 'toolbar', 'search_hb']:
                base.get_widget(widget).set_sensitive(False)

    doGtkEvents()

def normalCursor(base):
    ''' Set Normal cursor in mainwin and make it sensitive '''
    win = base.window.get_window()
    if win != None:
        win.set_cursor(None)
        for widget in ['main_vpaned', 'toolbar', 'search_hb']:
            base.get_widget(widget).set_sensitive(True)
        #base.window.set_sensitive(True)
    doGtkEvents()


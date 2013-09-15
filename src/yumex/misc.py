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


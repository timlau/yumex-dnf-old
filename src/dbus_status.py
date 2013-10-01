#!/usr/bin/python2 -tt
# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A GUI for yum
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


import dbus
import dbus.service
import dbus.glib
#import gobject
import logging
import argparse
import os.path
import sys
import gettext
from gi.repository import Gtk, GObject, GdkPixbuf
import cairo
import random
from yumdaemon import *


version = 100 # must be integer
DAEMON_ORG = 'dk.yumex.StatusIcon'
DAEMON_INTERFACE = DAEMON_ORG
LOG_ROOT = 'yumex-statusicon'

logger = logging.getLogger(LOG_ROOT)
gettext.bindtextdomain('yumex')
gettext.textdomain('yumex')
_ = gettext.gettext
P_ = gettext.ngettext


BIN_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
if BIN_PATH in ["/usr/share/yumex-nextgen"]:
    DATA_DIR = '/usr/share/yumex-nextgen'
    PIX_DIR = DATA_DIR + "/gfx"
    MISC_DIR = DATA_DIR
else:
    DATA_DIR = BIN_PATH
    PIX_DIR = DATA_DIR + "/../gfx"
    MISC_DIR = DATA_DIR + "/../misc"

ICON_TRAY_ERROR = PIX_DIR + '/tray-error.png'
ICON_TRAY_NO_UPDATES = PIX_DIR + '/tray-no-updates.png'
ICON_TRAY_UPDATES = PIX_DIR + '/tray-updates.png'
ICON_TRAY_WORKING = PIX_DIR + '/tray-working.png'
ICON_TRAY_INFO = PIX_DIR + '/tray-info.png'


def Logger(func):
    """
    This decorator catch yum exceptions and send fatal signal to frontend
    """
    def newFunc(*args, **kwargs):
        logger.debug("%s started args: %s " % (func.__name__, repr(args[1:])))
        rc = func(*args, **kwargs)
        logger.debug("%s ended" % func.__name__)
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

class YumReadOnlyBackend(YumDaemonReadOnlyClient):
    """
    Yumex Package Backend including Yum Daemon backend (ReadOnly, Running as current user)
    """

    def __init__(self):
        YumDaemonReadOnlyClient.__init__(self)

class StatusIcon:
    rel_font_size = 0.7
    is_working = 0
    need_input = False
    update_count = -2

    popup_menu = None
    quit_menu = None
    search_updates_menu = None


    def __init__(self):
        self.image_checking = ICON_TRAY_WORKING
        self.image_no_update = ICON_TRAY_NO_UPDATES
        self.image_updates = ICON_TRAY_UPDATES
        self.image_error = ICON_TRAY_ERROR
        self.image_info = ICON_TRAY_INFO

        self.statusicon = Gtk.StatusIcon()
        self.init_popup_menu()
        self.update_tray_icon()

    def init_popup_menu(self):
        menu = Gtk.Menu()
        self.popup_menu = menu

        quit = Gtk.MenuItem(_("Quit"))
        self.quit_menu = quit

        search_updates = Gtk.MenuItem(_("Search for Updates"))
        self.search_updates_menu = search_updates

        menu.append(search_updates)
        menu.append(quit)
        menu.show_all()
        self.statusicon.connect("popup-menu", self.on_popup)


    def set_popup_menu_sensitivity(self, sensitive):
        self.quit_menu.set_sensitive(sensitive)
        self.search_updates_menu.set_sensitive(sensitive)

    def on_popup(self, icon, button, time):
        # self.popup_menu.popup(None, None, Gtk.StatusIcon.position_menu, button,time, self.statusicon)
        def pos(menu, icon):
            return (Gtk.StatusIcon.position_menu(menu, icon))

        self.popup_menu.popup(None, None, pos, self.statusicon, button, time)
        # self.popup_menu.popup(None, None, None, Gtk.StatusIcon.position_menu, button, time)

    def get_status_icon(self):
        return self.statusicon

    def update_tray_icon(self):
        if self.need_input:
            self.statusicon.set_tooltip_text("Yum Extender: Need user input")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_info)
            self.set_popup_menu_sensitivity(False)
        elif self.is_working > 0:
            self.statusicon.set_tooltip_text("Yum Extender: Working")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_checking)
            self.set_popup_menu_sensitivity(False)
        else:
            self.set_popup_menu_sensitivity(True)
            update_count = self.update_count
            if update_count == -2:
                self.statusicon.set_tooltip_text(_("Yum Extender"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
            elif update_count == -1:
                self.statusicon.set_tooltip_text(_("Yum Extender: Error"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_error)
            elif update_count == 0:
                self.statusicon.set_tooltip_text(_("Yum Extender: No Updates"))
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.image_no_update)
            else:
                self.statusicon.set_tooltip_text(_("Yum Extender: %s Updates available")
                        % update_count)
                pixbuf = self.get_pixbuf_with_text(self.image_updates,
                        str(update_count), self.rel_font_size)
        self.statusicon.set_from_pixbuf(pixbuf)
        Gtk.main_iteration()

    # png_file must be a squared image
    def get_pixbuf_with_text(self, png_file, text, relative_font_size):
        img = cairo.ImageSurface.create_from_png(png_file)
        size = img.get_height()
        surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context (surface)
        ctx.set_source_surface(img, 0, 0)
        ctx.paint()

        font_size = size * relative_font_size
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        # resize font size until text fits ...
        while font_size > 1.0:
            ctx.set_font_size(int(font_size))
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                    cairo.FONT_WEIGHT_BOLD)
            [bearing_x, bearing_y, font_x, font_y, ax, ay] = ctx.text_extents(text)
            if font_x < size: break
            font_size = font_size * 0.9
        ctx.move_to(int(size - font_x) / 2 - bearing_x , int(size - font_y) / 2 - bearing_y)
        ctx.show_text(text)
        ctx.stroke()

        # this is ugly but the easiest way to get a pixbuf from a cairo image
        # surface...
        r = int(random.random() * 999999)
        file_name = "/tmp/notifier_tmp_" + str(r) + ".png"
        surface.write_to_png(file_name)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_name)
        os.remove(file_name)
        return pixbuf


    def set_update_count(self, update_count):
        '''
        set the available update count
        @param update_count: =0: no updates, -1: error occured
        '''
        self.update_count = update_count
        self.update_tray_icon()

    def set_is_working(self, is_working=True):
        '''
        set working: show a busy tray icon if is_working is True
        '''
        if is_working:
            self.is_working = self.is_working + 1
        else:
            self.is_working = self.is_working - 1
        self.update_tray_icon()

    def need_user_input(self, need_input=True):
        """ call this when a user interacton/input is needed """

        self.need_input = need_input
        self.update_tray_icon()


#------------------------------------------------------------------------------ DBus Exception
class StatusIconError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'StatusIconError'


#------------------------------------------------------------------------------ Main class
class YumexStatusDaemon(dbus.service.Object):

    def __init__(self, mainloop):
        self.mainloop = mainloop
        bus_name = dbus.service.BusName(DAEMON_ORG, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/')
        
        # Vars
        self.started = False
        self.status_icon = None
        self.yumex_running = False

        # yum daemon client setup
        self.backend = YumReadOnlyBackend()
        
    def setup_statusicon(self):
        self.status_icon = StatusIcon()
        icon = self.status_icon.get_status_icon()
        icon.connect("activate", self.on_status_icon_clicked)
        self.status_icon.quit_menu.connect("activate", self.on_quit)
        self.status_icon.search_updates_menu.connect("activate", self.get_updates)

#===============================================================================
# DBus Methods
#===============================================================================

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='i')
    def GetVersion(self):
        '''
        Get the daemon version
        '''
        return version

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='',
                                          sender_keyword='sender')
    def Exit(self, sender=None):
        '''
        Exit the daemon
        :param sender:
        '''
        self.mainloop.quit()
 
    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='b',
                                          sender_keyword='sender')
    def Start(self, sender=None):
        '''
        '''
        if not self.started:
            self.setup_statusicon()
            self.started = True
            return True
        else:
            return False
    
    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='s',
                                          sender_keyword='sender')
 
    def Test(self,sender=None):
        return "Hello World"
 
    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='b',
                                          out_signature='',
                                          sender_keyword='sender')
 
    def SetWorking(self, is_working, sender=None):
        if self.started:
            self.status_icon.set_is_working(is_working)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='i',
                                          out_signature='',
                                          sender_keyword='sender')
 
    def SetUpdateCount(self, count, sender=None):
        if self.started:
            self.status_icon.set_update_count(count)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='i',
                                          sender_keyword='sender')
 
    def CheckUpdates(self, sender=None):
        if self.started:
            return self.get_updates()


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='b',
                                          out_signature='b',
                                          sender_keyword='sender')
 
    def SetYumexIsRunning(self, state, sender=None):
        if self.yumex_running == not state:
            self.yumex_running = state
            return True
        else: # Yumex is already running  
            return False
        
        
        
#===============================================================================
# DBus signals
#===============================================================================
    @dbus.service.signal(DAEMON_INTERFACE)
    def TestSignal(self):
        '''
        '''
        pass

#===============================================================================
# yum helpers
#===============================================================================

    def get_updates(self, *args):
        self.status_icon.set_is_working(True)
        try:
            self.backend.Lock()
            logger.debug("Check for updates")
            pkgs = self.backend.GetPackages('updates')
            rc = len(pkgs)
            logger.debug("# of updates : %d" % rc)
            self.backend.Unlock()
        except: # Get locking errors
            logger.debug('Error getting the yum lock') 
            rc = -1
        self.status_icon.set_is_working(False)
        self.status_icon.set_update_count(rc)
        return rc
        
#===============================================================================
# GUI Callback
#===============================================================================

    def on_status_icon_clicked(self, event):
        '''
        left click on status icon handler
        hide/show the window, based on current state
        '''
        logger.debug('status-icon clicked')


    def on_quit(self, *args):
        '''
        left click on status icon handler
        hide/show the window, based on current state
        '''
        logger.debug('quit clicked')
        self.mainloop.quit()
        
        

def doTextLoggerSetup(logroot=LOG_ROOT, logfmt='%(asctime)s: %(message)s', loglvl=logging.INFO):
    ''' Setup Python logging  '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)

def main():
    parser = argparse.ArgumentParser(description='Yumex Status Icon D-Bus Daemon')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        if args.debug:
            doTextLoggerSetup(loglvl=logging.DEBUG)
        else:
            doTextLoggerSetup()

    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GObject.MainLoop()
    yd = YumexStatusDaemon(mainloop)
    mainloop.run()

if __name__ == '__main__':
    main()

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

import time

from gi.repository import Gtk
from yumdaemon import YumDaemonError
import gettext
import os.path
import configparser
import logging
from .config import *

gettext.bindtextdomain('yumex')
gettext.textdomain('yumex')
_ = gettext.gettext
P_ = gettext.ngettext

logger = logging.getLogger('yumex.misc')        


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


def ExceptionHandler(func):
    """
    This decorator catch yum backed exceptions
    """
    def newFunc(*args, **kwargs):
        try:
            rc = func(*args, **kwargs)
            return rc
        except YumDaemonError as e:
            base = args[0] # get current class
            base.exception_handler(e)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

def TimeFunction(func):
    """
    This decorator catch yum exceptions and send fatal signal to frontend
    """
    def newFunc(*args, **kwargs):
        t_start = time.time()
        rc = func(*args, **kwargs)
        t_end = time.time()
        name = func.__name__
        logger.debug("%s took %.2f sec" % (name, t_end - t_start))
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

def format_number(number, SI=0, space=' '):
    """Turn numbers into human-readable metric-like numbers"""
    symbols = ['',  # (none)
               'k', # kilo
               'M', # mega
               'G', # giga
               'T', # tera
               'P', # peta
               'E', # exa
               'Z', # zetta
               'Y'] # yotta

    if SI: step = 1000.0
    else: step = 1024.0

    thresh = 999
    depth = 0
    max_depth = len(symbols) - 1

    # we want numbers between 0 and thresh, but don't exceed the length
    # of our list.  In that event, the formatting will be screwed up,
    # but it'll still show the right number.
    while number > thresh and depth < max_depth:
        depth  = depth + 1
        number = number / step

    if type(number) == type(1) or type(number) == type(1):
        # it's an int or a long, which means it didn't get divided,
        # which means it's already short enough
        fmt = '%i%s%s'
    elif number < 9.95:
        # must use 9.95 for proper sizing.  For example, 9.99 will be
        # rounded to 10.0 with the .1f fmt string (which is too long)
        fmt = '%.1f%s%s'
    else:
        fmt = '%.0f%s%s'

    return(fmt % (float(number or 0), space, symbols[depth]))

class YumexConf(BaseConfig):
    """ Yum Extender Config Setting"""
    debug = BoolOption(False)
    autostart = BoolOption(False)
    color_install = Option('rgb(78,154,6)')
    color_update = Option('rgb(204,0,0)')
    color_normal = Option('rgb(0,0,0)')
    color_obsolete = Option('rgb(52,101,164)')
    color_downgrade = Option('rgb(193,125,17)')
    history_days = IntOption(180)
    bugzilla_url = Option('https://bugzilla.redhat.com/show_bug.cgi?id=')
    skip_broken = BoolOption(False)
    newest_only= BoolOption(True)
    clean_unused = BoolOption(False)

class SessionConf(BaseConfig):
    """ Yum Extender current session Setting"""
    skip_broken = BoolOption(False)
    newest_only= BoolOption(True)
    clean_unused = BoolOption(False)


class Config(object):
    '''
    Yum Extender Configuration class
    '''
    WRITE_ALWAYS = ['autostart']
    
    def __init__(self):
        object.__init__(self)
        self.conf_dir = os.environ['HOME'] + "/.config/yumex-nextgen"
        if not os.path.isdir(self.conf_dir):
            print("creating config directory : %s" % self.conf_dir)
            os.makedirs(self.conf_dir, 0o700)
        self.conf_file = self.conf_dir+"/yumex.conf"
        self.parser = configparser.ConfigParser()
        self.conf = YumexConf()
        self.session = SessionConf()
        self.read()
        
    def read(self):
        if not os.path.exists(self.conf_file):
            logger.info("creating default config file : %s" % self.conf_file)
            fh = open(self.conf_file,"w")
            print('[yumex]\n', file=fh)
            fh.close()
        self.parser.read_file(open(self.conf_file,"r"))
        if not self.parser.has_section('yumex'):
            self.parser.add_section('yumex')
        self.conf.populate(self.parser, 'yumex')
        self.session.populate(self.parser, 'yumex')
            
    def write(self):
        fp = open(self.conf_file,"w")
        self.conf.write(fp,"yumex", Config.WRITE_ALWAYS)
        fp.close()
       

CONFIG = Config()

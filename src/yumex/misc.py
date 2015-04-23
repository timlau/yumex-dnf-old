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
#    along with this program; if not, write to
#    the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from __future__ import absolute_import

import time

from gi.repository import Gtk
from gi.repository import Gdk

import configparser
import dnfdaemon.client
import gettext
import locale
import logging
import os.path
import sys
import yumex.config as config

LOCALE_DIR = os.path.join(sys.prefix, 'share', 'locale')
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain('yumex-dnf', LOCALE_DIR)
gettext.bindtextdomain('yumex-dnf', LOCALE_DIR)
gettext.textdomain('yumex-dnf')
_ = gettext.gettext
P_ = gettext.ngettext

logger = logging.getLogger('yumex.misc')


def color_floats(spec):
    rgba = Gdk.RGBA()
    rgba.parse(spec)
    return rgba.red, rgba.green, rgba.blue


def get_color(spec):
    rgba = Gdk.RGBA()
    rgba.parse(spec)
    return rgba


def rgb_to_hex(r, g, b):
    if isinstance(r, float):
        r *= 255
        g *= 255
        b *= 255
    return "#%02X%02X%02X" % (r, g, b)


def color_to_hex(color):
    return rgb_to_hex(color.red, color.green, color.blue)


def format_block(block, indent):
        ''' Format a block of text so they get the same indentation'''
        spaces = " " * indent
        lines = str(block).split('\n')
        result = lines[0] + "\n"
        for line in lines[1:]:
            result += spaces + line + '\n'
        return result


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
        except dnfdaemon.client.DaemonError as e:
            base = args[0]  # get current class
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
               'k',  # kilo
               'M',  # mega
               'G',  # giga
               'T',  # tera
               'P',  # peta
               'E',  # exa
               'Z',  # zetta
               'Y']  # yotta

    if SI:
        step = 1000.0
    else:
        step = 1024.0

    thresh = 999
    depth = 0
    max_depth = len(symbols) - 1

    # we want numbers between 0 and thresh, but don't exceed the length
    # of our list.  In that event, the formatting will be screwed up,
    # but it'll still show the right number.
    while number > thresh and depth < max_depth:
        depth = depth + 1
        number = number / step

    if isinstance(number, int):
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


class YumexConf(config.BaseConfig):
    """ Yum Extender Config Setting"""
    debug = config.BoolOption(False)
    autostart = config.BoolOption(False)
    color_install = config.Option('#4E9A06')
    color_update = config.Option('#CC0000')
    color_normal = config.Option('#000000')
    color_obsolete = config.Option('#3465A4')
    color_downgrade = config.Option('#C17D11')
    history_days = config.IntOption(180)
    bugzilla_url = config.Option(
        'https://bugzilla.redhat.com/show_bug.cgi?id=')
    skip_broken = config.BoolOption(False)
    newest_only = config.BoolOption(True)
    clean_unused = config.BoolOption(False)
    update_interval = config.IntOption(60)
    update_startup_delay = config.IntOption(30)
    autocheck_updates = config.BoolOption(False)
    hide_on_close = config.BoolOption(False)
    system_refresh = config.Option('2000-01-01 00:01')
    refresh_interval = config.IntOption(12)
    max_dnl_errors = config.IntOption(100)
    # headerbar is default if running gnome
    if 'GDMSESSION' in os.environ:
        hb_default = 'gnome' in os.environ['GDMSESSION']
    else:
        hb_default = False
    headerbar = config.BoolOption(hb_default)
    search_default = config.CaselessSelectionOption(
                            default='prefix',
                            allowed=('prefix', 'key', 'fields'))
    search_fields = config.KeyListOption(['name', 'summary'])
    win_height = config.IntOption(700)
    win_width = config.IntOption(1024)
    win_maximized = config.BoolOption(False)


class SessionConf(config.BaseConfig):
    """ Yum Extender current session Setting"""
    # skip broken for current session
    skip_broken = config.BoolOption(False)
    # show newest package version only for current session
    newest_only = config.BoolOption(True)
    # Clean orphan dependencies for this session
    clean_unused = config.BoolOption(False)
    # enabled repositories for this session
    enabled_repos = config.ListOption([])


class Config(object):
    '''
    Yum Extender Configuration class
    '''
    WRITE_ALWAYS = ['autostart', 'update_interval',
                    'update_startup_delay', 'autocheck_updates']

    def __init__(self):
        object.__init__(self)
        self.conf_dir = os.environ['HOME'] + "/.config/yumex-dnf"
        if not os.path.isdir(self.conf_dir):
            print("creating config directory : %s" % self.conf_dir)
            os.makedirs(self.conf_dir, 0o700)
        self.conf_file = self.conf_dir + "/yumex.conf"
        self.parser = configparser.ConfigParser()
        self.conf = YumexConf()
        self.session = SessionConf()
        self.read()

    def read(self):
        if not os.path.exists(self.conf_file):
            logger.info("creating default config file : %s" % self.conf_file)
            fh = open(self.conf_file, "w")
            print('[yumex]\n', file=fh)
            fh.close()
        self.parser.read_file(open(self.conf_file, "r"))
        if not self.parser.has_section('yumex'):
            self.parser.add_section('yumex')
        self.conf.populate(self.parser, 'yumex')
        self.session.populate(self.parser, 'yumex')

    def write(self):
        fp = open(self.conf_file, "w")
        self.conf.write(fp, "yumex", Config.WRITE_ALWAYS)
        fp.close()


CONFIG = Config()

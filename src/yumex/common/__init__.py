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


import configparser
import gettext
import locale
import logging
import os.path
import re
import subprocess
import sys
import time

import dnfdaemon.client
from gi.repository import Gdk, Gtk, Notify

LOCALE_DIR = os.path.join(sys.prefix, 'share', 'locale')
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain('yumex-dnf', LOCALE_DIR)
gettext.bindtextdomain('yumex-dnf', LOCALE_DIR)
gettext.textdomain('yumex-dnf')
_ = gettext.gettext
ngettext = gettext.ngettext

import yumex.common.config as config
import yumex.common.const as const

logger = logging.getLogger('yumex.common')


class QueueEmptyError(Exception):

    def __init__(self):
        super(QueueEmptyError, self).__init__()


class TransactionBuildError(Exception):

    def __init__(self, msgs):
        super(TransactionBuildError, self).__init__()
        self.msgs = msgs


class TransactionSolveError(Exception):

    def __init__(self, msgs):
        super(TransactionSolveError, self).__init__()
        self.msgs = msgs


def dbus_dnfsystem(cmd):
    subprocess.call(
        '/usr/bin/dbus-send --system --print-reply '
        '--dest=org.baseurl.DnfSystem / org.baseurl.DnfSystem.%s' % cmd,
        shell=True)


def load_ui(ui_file):
    ui = Gtk.Builder()
    ui.set_translation_domain('yumex-dnf')
    ui.add_from_file(os.path.join(const.UI_DIR, ui_file))
    return ui


def to_pkg_tuple(pkg_id):
    """Find the real package nevre & repoid from an package pkg_id"""
    (n, e, v, r, a, repo_id) = str(pkg_id).split(',')
    return n, e, v, r, a, repo_id


def list_to_string(pkg_list, first_delimitier, delimiter):
    """Creates a multiline string from a list of packages"""
    string = first_delimitier
    for pkg_name in pkg_list:
        string = string + pkg_name + delimiter
    return string


def pkg_id_to_full_name(pkg_id):
    (n, e, v, r, a, repo_id) = to_pkg_tuple(pkg_id)
    if e and e != '0':
        return "%s-%s:%s-%s.%s" % (n, e, v, r, a)
    else:
        return "%s-%s-%s.%s" % (n, v, r, a)


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
    return "#{0:02X}{1:02X}{2:02X}".format(int(r), int(g), int(b))


def color_to_hex(color):
    return rgb_to_hex(color.red, color.green, color.blue)


def is_url(url):
    urls = re.findall(
        r'^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|'
        r'[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+', url)
    return urls


def format_block(block, indent):
    """ Format a block of text so they get the same indentation"""
    spaces = " " * indent
    lines = str(block).split('\n')
    result = lines[0] + "\n"
    for line in lines[1:]:
        result += spaces + line + '\n'
    return result


def get_style_color(widget):
    """Get the default color for a widget in current theme."""
    context = widget.get_style_context()
    context.save()
    context.set_state(Gtk.StateFlags.NORMAL)
    color = context.get_color(context.get_state())
    context.restore()
    return color


def doGtkEvents():
    """

    """
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
    This decorator show the execution time of a function in the debug log
    """
    def newFunc(*args, **kwargs):
        t_start = time.time()
        rc = func(*args, **kwargs)
        t_end = time.time()
        name = func.__name__
        logger.debug("%s took %.2f sec", name, t_end - t_start)
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

    return fmt % (float(number or 0), space, symbols[depth])


def notify(summary, body):
    Notify.init('Yum Extender')
    icon = "yumex-dnf"
    notification = Notify.Notification.new(summary, body, icon)
    notification.set_timeout(5000)  # timeout 5s
    notification.show()


def check_dark_theme():
    """Returns True if Gtk using a dark theme"""
    gtk_settings = Gtk.Settings.get_default()
    return gtk_settings.get_property("gtk-application-prefer-dark-theme")


def logger_setup(logroot='yumex',
                 logfmt='%(asctime)s: %(message)s',
                 loglvl=logging.INFO):
    """Setup Python logging."""
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, '%H:%M:%S')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)


def is_gnome():
    """Return True if desktop is Gnome."""
    return os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"


class YumexConf(config.BaseConfig):
    """ Yum Extender Config Setting"""
    debug = config.BoolOption(False)
    autostart = config.BoolOption(False)
    theme = config.Option("System-Dark.theme")
    use_dark = config.BoolOption(False)
    show_splash = config.BoolOption(True)

    color_install = config.Option('#8BE8FD')
    color_update = config.Option('#FF79C6')
    color_downgrade = config.Option('#50FA7B')
    color_normal = config.Option('#D3DAE3')
    color_obsolete = config.Option('#FFB86C')

    history_days = config.IntOption(180)
    newest_only = config.BoolOption(True)
    clean_unused = config.BoolOption(False)
    update_interval = config.IntOption(60)
    autocheck_updates = config.BoolOption(False)
    system_refresh = config.Option('2000-01-01 00:01')
    refresh_interval = config.IntOption(12)
    # headerbar is default if running gnome
    hb_default = is_gnome()
    headerbar = config.BoolOption(hb_default)
    search_default = config.CaselessSelectionOption(
        default='prefix',
        allowed=('prefix', 'keyword', 'fields', 'key'))
    search_fields = config.KeyListOption(['name', 'summary'])
    win_height = config.IntOption(700)
    win_width = config.IntOption(1150)
    info_paned = config.IntOption(450)
    win_maximized = config.BoolOption(False)
    auto_select_updates = config.BoolOption(False)
    repo_saved = config.BoolOption(False)
    repo_enabled = config.KeyListOption([])
    archs = config.KeyListOption([])
    protected = config.KeyListOption(['yumex-dnf', 'python3-dnfdaemon'])
    clean_instonly = config.BoolOption(True)
    search_visible = config.BoolOption(False)
    installonly_limit = config.PositiveIntOption(3, range_min=2,
                                                 names_of_0=["0", "<off>"])


class SessionConf(config.BaseConfig):
    """ Yum Extender current session Setting"""
    # show newest package version only for current session
    newest_only = config.BoolOption(True)
    # Clean orphan dependencies for this session
    clean_unused = config.BoolOption(False)
    # enabled repositories for this session
    enabled_repos = config.ListOption([])
    clean_instonly = config.BoolOption(False)
    color_install = config.Option('#ffffff')
    color_update = config.Option('#ffffff')
    color_downgrade = config.Option('#ffffff')
    color_normal = config.Option('#ffffff')
    color_obsolete = config.Option('#ffffff')


class Config(object):
    """
    Yum Extender Configuration class
    """
    WRITE_ALWAYS = ['autostart', 'update_interval',
                    'update_startup_delay', 'autocheck_updates',
                    'update_notify', 'update_showicon']

    def __init__(self):
        object.__init__(self)
        self.conf_dir = os.environ['HOME'] + "/.config/yumex-dnf"
        if not os.path.isdir(self.conf_dir):
            logger.info("creating config directory : %s", self.conf_dir)
            os.makedirs(self.conf_dir, 0o700)
        self.conf_file = self.conf_dir + "/yumex.conf"
        self.parser = configparser.ConfigParser()
        self.conf = YumexConf()
        self.session = SessionConf()
        self.read()

    def read(self):
        first_read = False
        if not os.path.exists(self.conf_file):
            logger.info("creating default config file : %s", self.conf_file)
            first_read = True
        else:
            self.parser.read_file(open(self.conf_file, "r"))
        if not self.parser.has_section('yumex'):
            self.parser.add_section('yumex')
        self.conf.populate(self.parser, 'yumex')
        self.session.populate(self.parser, 'yumex')
        if first_read:
            self.write()

    def write(self):
        fp = open(self.conf_file, "w")
        self.conf.write(fp, "yumex", Config.WRITE_ALWAYS)
        fp.close()


CONFIG = Config()

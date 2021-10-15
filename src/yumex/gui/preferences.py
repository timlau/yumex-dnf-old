import glob
import logging
import os
import shutil

from gi.repository import GObject, Gtk
from yumex import const
from yumex.misc import CONFIG, _, format_number, load_ui

from .views import RepoView

logger = logging.getLogger('yumex.gui.preffernces')


class Preferences:

    VALUES = ['update_interval', 'refresh_interval', 'installonly_limit']
    FLAGS = ['autostart', 'clean_unused', 'newest_only',
             'headerbar', 'auto_select_updates', 'repo_saved', 'clean_instonly', 'use_dark', 'search_visible', 'show_splash'
             ]

    def __init__(self, base):
        self.base = base
        self.ui = load_ui('preferences.ui')
        self.dialog = self.ui.get_object("preferences")
        self.dialog.set_transient_for(base)
        self.repo_view = RepoView()
        widget = self.ui.get_object('repo_sw')
        widget.add(self.repo_view)
        self.repo_box = self.ui.get_object("box_repos")
        # track when repo page is active in stack
        self.repo_box.connect("map", self.on_repo_page_active)
        self.repos = []

    def run(self):
        self.get_settings()
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.hide()
        need_reset = False
        if rc == Gtk.ResponseType.OK:
            need_reset = self.set_settings()
        return need_reset

    def on_repo_page_active(self, widget, *args):
        """ Callback for ::map event there is called when repo page is active"""
        if not self.repos:
            self._load_repositories()

    def _load_repositories(self):
        """ Lazy load repositories """
        # get the repositories
        self.base.set_working(True, splash=True)
        self.base.infobar.message(_('Fetching repository information'))
        self.repos = self.base.backend.get_repositories()
        self.base.infobar.hide()
        self.repo_view.populate(self.repos)
        self.base.set_working(False, splash=True)
        if CONFIG.conf.repo_saved:
            self.repo_view.select_by_keys(CONFIG.session.enabled_repos)

    def get_themes(self):
        # Get Themes
        pattern = os.path.normpath(os.path.join(const.THEME_DIR, '*.theme'))
        theme_files = glob.glob(pattern)
        theme_names = [os.path.basename(theme).split('.')[0]
                       for theme in theme_files]
        widget = self.ui.get_object('pref_theme')
        widget.remove_all()
        default = CONFIG.conf.theme.split(".")[0]
        i = 0
        ndx = 0
        for theme in sorted(theme_names):
            widget.append_text(theme)
            if theme == default:
                ndx = i
            i += 1
        widget.set_active(ndx)

    def get_settings(self):
        # set boolean states
        for option in Preferences.FLAGS:
            logger.debug("%s : %s ", option, getattr(CONFIG.conf, option))
            widget = self.ui.get_object('pref_' + option)
            widget.set_active(getattr(CONFIG.conf, option))
        # cleanup installonly handler
        widget = self.ui.get_object('pref_clean_instonly')
        widget.connect('notify::active', self.on_clean_instonly)
        # Set value states
        for name in Preferences.VALUES:
            widget = self.ui.get_object('pref_' + name)
            widget.set_value(getattr(CONFIG.conf, name))
        self.on_clean_instonly()
        # Get Themes
        self.get_themes()

    def on_clean_instonly(self, *args):
        """Handler for clean_instonly switch"""
        widget = self.ui.get_object('pref_clean_instonly')
        state = widget.get_active()
        postfix = 'installonly_limit'
        self._set_sensitive(postfix, state)

    def _set_sensitive(self, postfix, state):
        for prefix in ['pref_', 'label_']:
            id_ = prefix + postfix
            if state:
                self.ui.get_object(id_).set_sensitive(True)
            else:
                self.ui.get_object(id_).set_sensitive(False)

    def set_settings(self):
        changed = False
        need_reset = False
        # handle boolean options
        for option in Preferences.FLAGS:
            widget = self.ui.get_object('pref_' + option)
            state = widget.get_active()
            if state != getattr(CONFIG.conf, option):  # changed ??
                setattr(CONFIG.conf, option, state)
                changed = True
                self.handle_setting(option, state)
        # handle value options
        for name in Preferences.VALUES:
            widget = self.ui.get_object('pref_' + name)
            value = widget.get_value_as_int()
            if value != getattr(CONFIG.conf, name):  # changed ??
                setattr(CONFIG.conf, name, value)
                changed = True
        # handle repos, if the repositories has been loaded
        if self.repos:
            repo_before = CONFIG.session.enabled_repos
            repo_now = self.repo_view.get_selected()
            # repo selection changed
            if repo_now != repo_before:
                CONFIG.session.enabled_repos = repo_now     # set the new selection
                # we need to reset the gui
                need_reset = True
                if CONFIG.conf.repo_saved:
                    CONFIG.conf.repo_enabled = repo_now
                    changed = True
        # Themes
        widget = self.ui.get_object('pref_theme')
        default = CONFIG.conf.theme.split(".")[0]
        theme = widget.get_active_text()
        if theme != default:
            CONFIG.conf.theme = f'{theme}.theme'
            self.base.load_custom_styling()
            changed = True
        if changed:
            CONFIG.write()
        return need_reset

    def handle_setting(self, option, state):
        if option == 'autostart':
            if state:  # create an autostart .desktop for current user
                if not os.path.isdir(const.AUTOSTART_DIR):
                    logger.info("creating autostart directory : %s",
                                const.AUTOSTART_DIR)
                    os.makedirs(const.AUTOSTART_DIR, 0o700)
                shutil.copy(const.SYS_DESKTOP_FILE, const.USER_DESKTOP_FILE)
            else:  # remove the autostart file
                if os.path.exists(const.USER_DESKTOP_FILE):
                    os.unlink(const.USER_DESKTOP_FILE)

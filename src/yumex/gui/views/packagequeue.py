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

from yumex import const

logger = logging.getLogger("yumex.gui.views")


class PackageQueue:
    """
    A Queue class to store selected packages/groups and the pending actions
    """

    def __init__(self):
        self.packages = {}
        self._setup_packages()
        self.groups = {"i": {}, "r": {}}
        self._name_arch_index = {}

    def _setup_packages(self):
        for key in const.QUEUE_PACKAGE_TYPES:
            self.packages[key] = []

    def clear(self):
        del self.packages
        self.packages = {}
        self._setup_packages()
        self.groups = {"i": {}, "r": {}}
        self._name_arch_index = {}

    def get(self, action=None):
        if action is None:
            return self.packages
        else:
            return self.packages[action]

    def total(self):
        num = 0
        for key in const.QUEUE_PACKAGE_TYPES:
            num += len(self.packages[key])
        num += len(self.groups["i"].keys())
        num += len(self.groups["r"].keys())
        return num

    def add(self, pkg, action=None):
        """Add a package to queue"""
        if not action:
            action = pkg.action
        name_arch = f"{pkg.name}.{pkg.arch}"
        if pkg not in self.packages[action] and name_arch not in self._name_arch_index:
            self.packages[action].append(pkg)
            self._name_arch_index[name_arch] = 1

    def remove(self, pkg, action=None):
        """Remove package from queue"""
        if not action:
            action = pkg.action
        name_arch = f"{pkg.name}.{pkg.arch}"
        if pkg in self.packages[action]:
            self.packages[action].remove(pkg)
            del self._name_arch_index[name_arch]

    def has_pkg_with_name_arch(self, pkg):
        name_arch = f"{pkg.name}.{pkg.arch}"
        return name_arch in self._name_arch_index

    def add_group(self, grp, action):
        """

        @param grp: Group object
        @param action:
        """
        logger.debug(f"add_group : {grp.id} - {action}")
        grps = self.groups[action]
        if grp.id not in grps:
            grps[grp.id] = grp
            grp.selected = True

    def remove_group(self, grp, action):
        """

        @param grp: Group object
        @param action:
        """
        logger.debug(f"remove_group : {grp.id} - {action}")
        grps = self.groups[action]
        if grp.id in grps:
            del grps[grp.id]
            grp.selected = False

    def remove_all_groups(self):
        """
        remove all groups from queue
        """
        for action in ("i", "r"):
            for grp in self.groups[action]:
                self.remove_group(grp, action)

    def remove_groups(self, group_names):
        """
        remove groups from queue based on list of grp_ids
        """
        for action in ("i", "r"):
            new_dict = {}
            grps = self.groups[action]
            for grp in grps.values():
                if grp.name not in group_names:
                    new_dict[grp.id] = grp  # copy to new dict
                else:  # unselect the group object
                    grp.selected = False
            self.groups[action] = new_dict

    def has_group(self, grp_id):
        """check if group is in package queue"""
        for action in ["i", "r"]:
            grps = self.groups[action]
            if grp_id in grps:
                return action
        return None

    def get_groups(self):
        """get (grp_id, action) generator"""
        for action in ("i", "r"):
            for grp in self.groups[action].values():
                yield grp.id, action

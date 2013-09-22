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


from .const import *


class Package:
    '''
    Base class for a package, must be implemented in a sub class
    '''

    def __init__(self, backend):
        self.backend = backend
        self.name = None
        # self.version = None
        self.arch = None
        self.repository = None
        self.summary = None
        # self.description = None
        self.size = None
        self.action = None
        # self.color = 'black'
        self.queued = False
        self.recent = False
        self.selected = False


    def __str__(self):
        '''
        Return a string representation of the package
        '''
        return self.fullname

    @property
    def fullname(self):
        '''
        fullname for the package :name-version.arch
        '''
        return "%s-%s.%s" % (self.name, self.version, self.arch)


    def get_attribute(self, attr):
        '''
        get attribute for the package
        :param attr:
        '''
        if hasattr(self, attr):
            return getattr(self, attr)
        else:
            return self.do_get_atributes(attr)

    def do_get_atributes(self, attr):
        '''
        get non local attributes for the package
        must be implemented in a sub class
        :param attr:
        '''
        raise NotImplementedError()


class Backend:
    '''
    Base package manager handling class
    it contains a cache for Package based objects, so we don't have
    to get the twice from the package manager.

    must be implemented in a sub class
    '''

    def __init__(self, frontend):
        self.cache = PackageCache()
        self.frontend = frontend


    def exception_handler(self, e):
        """
        send exceptions to the frontend
        """
        self.frontend.exception_handler(e)

    def get_packages(self, pkg_filter):
        '''
        Get a list of Package objects based on a filter ('installed', 'available'...)
        :param pkg_filter:
        '''
        pkgs = self.cache._get_packages(pkg_filter)
        return pkgs


    def get_history_dates(self):
        '''
        Get a list for dates for the system change history
        '''
        raise NotImplementedError()


    def get_history(self, date):
        '''
        Get the system changes for a given date
        :param date:
        '''
        raise NotImplementedError()

    def get_categories(self):
        '''
        Get categorties for available packages
        '''
        raise NotImplementedError()

    def get_sub_categories(self, category):
        '''
        Get sub categorties for a give category
        :param category:
        '''
        raise NotImplementedError()

    def get_packages_by_category(self, category):
        '''
        Get a list of Package objects for a given category
        :param category:
        '''
        raise NotImplementedError()


class PackageCache:
    '''
    Package cache to contain packages from backend, so we dont have get them more
    than once.
    '''

    def __init__(self):
        '''
        setup the cache
        '''
        for flt in ACTIONS_FILTER.values():
            setattr(self, flt, set())
        self._populated = []
        self._index = {}

    def reset(self):
        '''
        reset the cache
        '''
        for flt in ACTIONS_FILTER.values():
            setattr(self, flt, set())
        self._populated = []
        self._index = {}

    def _get_packages(self, pkg_filter):
        '''
        get a list of packages from the cache
        @param pkg_filter: the type of packages to get
        '''
        return list(getattr(self, str(pkg_filter)))

    def is_populated(self, pkg_filter):
        return str(pkg_filter) in self._populated

    def populate(self, pkg_filter, pkgs):
        '''
        '''
        self.find_packages(pkgs)
        self._populated.append(str(pkg_filter))


    def _add(self, po):
        if str(po) in self._index:  # package is in cache
            return self._index[str(po)]
        else:
            target = getattr(self, ACTIONS_FILTER[po.action])
            self._index[str(po)] = po
            target.add(po)
            return po

    # @TimeFunction
    def find_packages(self, packages):
        pkgs = []
        i = 0
        for po in packages:
            i += 1
            pkgs.append(self._add(po))
        return pkgs



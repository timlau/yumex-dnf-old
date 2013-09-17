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

from yumdaemon import *

from .backend import Package, Backend
from .const import *
from .misc import format_number, ExceptionHandler, TimeFunction

class YumPackage(Package):
    '''
    This is an abstract package object for a package in the package system
   '''

    def __init__(self, po_tuple, action, backend):
        Package.__init__(self, backend)
        (pkg_id, summary, size) = po_tuple
        self.pkg_id = pkg_id
        self.action = action
        (n, e, v, r, a, repo_id) = self.to_pkg_tuple(self.pkg_id)
        self.name = n
        self.epoch = e
        self.ver = v
        self.rel = r
        self.arch = a
        self.repository = repo_id
        self.visible = True
        self.downgrade_po = None
        self.summary = summary
        self.size = size
        self.sizeM = format_number(size)
        # cache
        self._description = None

    def to_pkg_tuple(self, pkg_id):
        ''' find the real package nevre & repoid from an package pkg_id'''
        (n, e, v, r, a, repo_id)  = str(pkg_id).split(',')
        return (n, e, v, r, a, repo_id)

    def __str__(self):
        '''
        string representation of the package object
        '''
        return self.fullname

    @property
    def fullname(self):
        ''' Package fullname  '''
        if self.epoch and self.epoch != '0':
            return "%s-%s:%s-%s.%s" % (self.name, self.epoch, self.ver, self.rel, self.arch)
        else:
            return "%s-%s-%s.%s" % (self.name, self.ver, self.rel, self.arch)


    def get_attribute(self, attr):
        '''

        @param attr:
        '''
        return self.backend.GetAttribute(self.pkg_id, attr)



    @property
    def version(self):
        '''

        '''
        return self.ver

    @property
    def release(self):
        '''

        '''
        return self.rel


    @property
    def filename(self):
        ''' Package pkg_id (the full package filename) '''
        if self.action == 'li': # the full path for at localinstall is stored in repoid
            return self.repoid
        else:
            return "%s-%s.%s.%s.rpm" % (self.name, self.version, self.release, self.arch)

    @property
    def fullver (self):
        '''
        Package full version-release
        '''
        return "%s-%s" % (self.version, self.release)

    @property
    def installed(self):
        return self.is_installed()

    def is_installed(self):
        return self.repoid[0] == '@' or self.repoid == 'installed'

    @property
    def URL(self):
        return self.get_attribute('url')


    def set_select(self, state):
        '''

        @param state:
        '''
        self.selected = state

    def set_visible(self, state):
        '''

        @param state:
        '''
        self.visible = state

    @property
    def description(self):
        '''

        '''
        return self.get_attribute('description')

    @property
    def changelog(self):
        '''

        '''
        return self.get_attribute('changelog')

    @property
    def filelist(self):
        '''
        get package filelist
        '''
        return self.get_attribute('filelist')


    @property
    def color(self):
        '''
        get package color to show in view
        '''
        return PACKAGE_COLORS[self.action]

    @property
    def downgrades(self):
        '''
        get package color to show in view
        '''
        return self.backend.get_downgrades(self.pkg_id)

    @property
    def updateinfo(self):
        '''
        get update info for package
        '''
        return self.backend.GetUpdateInfo(self.pkg_id)



    @property
    def dependencies(self):
        '''
        get update info for package
        '''
        return self.backend.get_dependencies(self.pkg_id)


    @property
    def is_update(self):
        if self.action == 'o' or self.action == 'u':
            return True
        else:
            return False


class YumBackend(YumDaemonClient):
    """
    Yum Daemon backend (root)
    """

    def __init__(self, base):
        YumDaemonClient.__init__(self)
        self.base = base

    def on_UpdateProgress(self,name,frac,fread,ftime):
        YumDaemonClient.on_UpdateProgress(self,name,frac,fread,ftime)
        #self.base.infobar.set_progress(frac)
        #self.base.infobar.set_subheader(name)

    def on_TransactionEvent(self,event, data):
        #if event == 'start-run':
            #self.base.infobar.show_progress(True)
        #elif event == 'download':
            #self.base.infobar.info(_("Downloading Packages"))
        #elif event == 'pkg-to-download':
            #self._dnl_packages = data
        #elif event == 'signature-check':
            #self.base.infobar.show_progress(False)
            #self.base.infobar.info(_("Checking Packages Signatures"))
        #elif event == 'run-test-transaction':
            #self.base.infobar.info(_("Testing Package Transactions"))
        #elif event == 'run-transaction':
            #self.base.infobar.show_progress(True)
            #self.base.infobar.info(_("Applying Package Transactions"))
        ##elif event == '':
        #elif event == 'fail':
            #self.base.infobar.show_progress(False)
        #elif event == 'end-run':
            #self.base.infobar.show_progress(False)
        #else:
            #print("TransactionEvent : %s" % event)
        YumDaemonClient.on_TransactionEvent(self,event, data)

    def on_RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        #num = " ( %i/%i ) : " % (ts_current, ts_total)
        #self.base.infobar.set_subheader(num + (RPM_ACTIONS[action] % str(package)))
        #frac = te_total / te_current
        #self.base.infobar.set_progress(frac)
        YumDaemonClient.on_RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total)

class YumReadOnlyBackend(Backend, YumDaemonReadOnlyClient):
    """
    Yumex Package Backend including Yum Daemon backend (ReadOnly, Running as current user)
    """

    def __init__(self, frontend):
        Backend.__init__(self, frontend)
        YumDaemonReadOnlyClient.__init__(self)

    @ExceptionHandler
    def setup(self):
        self.Lock()
        self.SetWatchdogState(False)
        return True

    @ExceptionHandler
    def quit(self):
        '''
        quit the application by unlocking yum and stop the mainloop
        '''
        self.Unlock()
        self.Exit()

    @ExceptionHandler
    def reload(self):
        '''
        Reload the yumdaemon service
        '''
        self.Unlock() # Release the lock
        #time.sleep(5)
        self.Lock() # Load & Lock the daemon
        self.SetWatchdogState(False)
        self.cache.reset() # Reset the cache


    def show_package_list(self, pkgs):
        '''
        show a list of packages
        @param pkgs:
        '''
        for pkg_id in pkgs:
            (n, e, v, r, a, repo_id) = self.to_pkg_tuple(pkg_id)
            print( " --> %s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id))

    def to_pkg_tuple(self, pkg_id):
        ''' find the real package nevre & repoid from an package pkg_id'''
        (n, e, v, r, a, repo_id)  = str(pkg_id).split(',')
        return (n, e, v, r, a, repo_id)

    def _make_pkg_object(self, pkgs, flt):
        '''
        Make list of po_dict to Package objects
        :param pkgs:
        :param flt:
        '''
        po_list = []
        action = FILTER_ACTIONS[flt]
        for pkg_values in pkgs:
            po_list.append(YumPackage(pkg_values, action, self))
        return self.cache.find_packages(po_list)

    def _build_package_list(self,pkg_ids):
        '''
        Build a list of package object, take existing ones from the cache.
        :param pkg_ids:
        :type pkg_ids:
        '''
        po_list = []
        for pkg_id in pkg_ids:
            summary = self.GetAttribute(pkg_id, "summary")
            size = self.GetAttribute(pkg_id, "size")
            pkg_values = (pkg_id,summary,size)
            action = BACKEND_ACTIONS[self.GetAttribute(pkg_id, "action")]
            po_list.append(YumPackage(pkg_values, action, self))
        return self.cache.find_packages(po_list)

    @ExceptionHandler
    @TimeFunction
    def get_packages(self,flt):
        if not self.cache.is_populated(flt): # is this type of packages is already cached ?
            fields = ['summary','size'] # fields to get
            po_list = self.GetPackageWithAttributes(flt, fields)
            pkgs = self._make_pkg_object(po_list,flt)
            self.cache.populate(flt, pkgs)
        return Backend.get_packages(self, flt)

    @ExceptionHandler
    def get_downgrades(self, pkg_id):
        pkgs = self.GetAttribute(pkg_id,"downgrades")
        return self._build_package_list(pkgs)

    @ExceptionHandler
    def get_packages_by_name(self, prefix, newest_only):
        '''

        :param prefix:
        :type prefix:
        :param newest_only:
        :type newest_only:
        '''
        pkgs = self.GetPackagesByName(prefix, newest_only)
        return self._build_package_list(pkgs)

    @ExceptionHandler
    def search(self, fields, keys, match_all, newest_only):
        '''

        :param fields:
        :type fields:
        :param keys:
        :type keys:
        :param match_all:
        :type match_all:
        '''
        pkgs = self.Search(fields, keys, match_all, newest_only)
        return self._build_package_list(pkgs)

    def show_transaction_result(self, output):
        for action, pkgs in output:
            print( "  %s" % action)
            for pkg_list in pkgs:
                pkg_id, size, obs_list = pkg_list  # (pkg_id, size, list with pkg_id's obsoleted by this pkg)
                print ("    --> %-50s : %s" % (self._fullname(pkg_id),size))

    def format_transaction_result(self, output):
        result = []
        for action, pkgs in output:
            result.append( "  %s" % action)
            for pkg_list in pkgs:
                pkg_id, size, obs_list = pkg_list  # (pkg_id, size, list with pkg_id's obsoleted by this pkg)
                result.append("    --> %-50s : %s" % (self._fullname(pkg_id),size))
        return "\n".join(result)

    def _fullname(self,pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id)  = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)
        else:
            return "%s-%s-%s.%s (%s)" % (n, v, r, a, repo_id)


class YumRootBackend(Backend, YumDaemonClient):
    """
    Yumex Package Backend including Yum Daemon backend (ReadOnly, Running as current user)
    """

    def __init__(self, frontend):
        Backend.__init__(self, frontend)
        YumDaemonClient.__init__(self)

    @ExceptionHandler
    def setup(self):
        self.Lock()
        self.SetWatchdogState(False)
        return True

    @ExceptionHandler
    def quit(self):
        '''
        quit the application by unlocking yum and stop the mainloop
        '''
        self.Unlock()
        self.Exit()

    @ExceptionHandler
    def reload(self):
        '''
        Reload the yumdaemon service
        '''
        self.Unlock() # Release the lock
        #time.sleep(5)
        self.Lock() # Load & Lock the daemon
        self.SetWatchdogState(False)
        self.cache.reset() # Reset the cache


    def to_pkg_tuple(self, pkg_id):
        ''' find the real package nevre & repoid from an package pkg_id'''
        (n, e, v, r, a, repo_id)  = str(pkg_id).split(',')
        return (n, e, v, r, a, repo_id)

    def _make_pkg_object(self, pkgs, flt):
        '''
        Make list of po_dict to Package objects
        :param pkgs:
        :param flt:
        '''
        po_list = []
        action = FILTER_ACTIONS[flt]
        for pkg_values in pkgs:
            po_list.append(YumPackage(pkg_values, action, self))
        return self.cache.find_packages(po_list)

    def _build_package_list(self,pkg_ids):
        '''
        Build a list of package object, take existing ones from the cache.
        :param pkg_ids:
        :type pkg_ids:
        '''
        po_list = []
        for pkg_id in pkg_ids:
            summary = self.GetAttribute(pkg_id, "summary")
            size = self.GetAttribute(pkg_id, "size")
            pkg_values = (pkg_id,summary,size)
            action = BACKEND_ACTIONS[self.GetAttribute(pkg_id, "action")]
            po_list.append(YumPackage(pkg_values, action, self))
        return self.cache.find_packages(po_list)


    def show_transaction_result(self, output):
        for action, pkgs in output:
            print( "  %s" % action)
            for pkg_list in pkgs:
                pkg_id, size, obs_list = pkg_list  # (pkg_id, size, list with pkg_id's obsoleted by this pkg)
                print ("    --> %-50s : %s" % (self._fullname(pkg_id),size))

    def format_transaction_result(self, output):
        result = []
        for action, pkgs in output:
            result.append( "  %s" % action)
            for pkg_list in pkgs:
                pkg_id, size, obs_list = pkg_list  # (pkg_id, size, list with pkg_id's obsoleted by this pkg)
                result.append("    --> %-50s : %s" % (self._fullname(pkg_id),size))
        return "\n".join(result)

    def _fullname(self,pkg_id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id)  = str(pkg_id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)
        else:
            return "%s-%s-%s.%s (%s)" % (n, v, r, a, repo_id)

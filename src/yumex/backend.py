import time
from yumdaemon import YumDaemonError

# Constants

ACTIONS_FILTER = { 'u' : 'updates', 'i' : 'available', \
                   'r' : 'installed' , 'o' : 'obsoletes', \
                    'do' : 'downgrade', 'ri' : 'reinstall', 'li' : 'localinstall' }

FILTER_ACTIONS = {'updates' : 'u', 'available': 'i', 'installed' : 'r', \
                   'obsoletes' : 'o', 'downgrade'  : 'do', 'reinstall' : 'ri', 'localinstall' : 'li'}


PACKAGE_COLORS = {
'i' : 'black',
'u' : 'red',
'r' : 'darkgreen',
'o' : 'blue',
'ri' : 'red',
'do' : 'goldenrod',
'li' : 'black'

}

BACKEND_ACTIONS = {'update' : 'u', 'install': 'i', 'remove' : 'r', \
                   'obsoletes' : 'o', 'downgrade'  : 'do'}


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
        print("%s took %.2f sec" % (name, t_end - t_start))
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
        format = '%i%s%s'
    elif number < 9.95:
        # must use 9.95 for proper sizing.  For example, 9.99 will be
        # rounded to 10.0 with the .1f format string (which is too long)
        format = '%.1f%s%s'
    else:
        format = '%.0f%s%s'

    return(format % (float(number or 0), space, symbols[depth]))

class Package:
    '''
    Base class for a package, must be implemented in a sub class
    '''

    def __init__(self,backend):
        self.backend = backend
        self.name = None
        #self.version = None
        self.arch = None
        self.repository = None
        self.summary = None
        #self.description = None
        self.size = None
        self.action = None
        #self.color = 'black'
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
        if hasattr(self,attr):
            return getattr(self,attr)
        else:
            return self.do_get_atributes(attr)

    def do_get_atributes(self,attr):
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
        

    def exception_handler(self,e):
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
        if str(po) in self._index: # package is in cache
            return self._index[str(po)]
        else:
            target = getattr(self, ACTIONS_FILTER[po.action])
            self._index[str(po)] = po
            target.add(po)
            return po

    #@TimeFunction
    def find_packages(self, packages):
        pkgs = []
        i = 0
        for po in packages:
            i += 1
            pkgs.append(self._add(po))
        return pkgs



from backend import *
import json

class TestPackage(Package):

    def __init__(self, backend, pkg, action):
        Package.__init__(self, backend)
        (n, ver, a, repoid, size, summary, description) = pkg
        self.name = n
        self.version = ver
        self.arch = a
        self.repository = repoid
        self.summary = summary
        self.description = description
        self.size = size
        self.sizeM = format_number(size)
        self.action = action
        self.color = PACKAGE_COLORS[action]
        self.queued = False
        self.recent = False
        self.selected = False

    def do_get_atributes(self, attr):
        return None


class TestBackend(Backend):

    def __init__(self):
        Backend.__init__(self)
        self._load_packages()


    def get_packages(self, pkg_filter):
        return Backend.get_packages(self, pkg_filter)

    def _load_packages(self):
        fh = open('pkg_installed.txt',"r")
        lines = fh.readlines()
        fh.close
        action = FILTER_ACTIONS['installed']
        pkgs = [TestPackage(self,json.loads(line),action) for line in lines]
        self.cache.populate('installed', pkgs)
        fh = open('pkg_available.txt',"r")
        lines = fh.readlines()
        fh.close
        action = FILTER_ACTIONS['available']
        pkgs = [TestPackage(self,json.loads(line),action) for line in lines]
        self.cache.populate('available', pkgs)
        fh = open('pkg_updates.txt',"r")
        lines = fh.readlines()
        fh.close
        action = FILTER_ACTIONS['updates']
        pkgs = [TestPackage(self,json.loads(line),action) for line in lines]
        self.cache.populate('updates', pkgs)


    def get_history_dates(self):
        return Backend.get_history_dates(self)


    def get_history_packages(self, date):
        return Backend.get_history_packages(self, date)


    def get_categories(self):
        return Backend.get_categories(self)


if __name__ == "__main__":
    backend = TestBackend()
    for po in backend.get_packages('installed'):
        print (str(po))
    for po in backend.get_packages('available'):
        print (str(po))


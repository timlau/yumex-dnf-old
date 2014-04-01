#!/usr/bin/python

from distutils.core import setup, Command
from distutils.util import convert_path
from distutils.command.build_scripts import build_scripts
from distutils import log

import os
from os.path import join, basename, split

class BuildScripts(build_scripts):
    def run(self):
        build_scripts.run(self)
        for script in self.scripts:
            script = convert_path(script)
            outfile = join(self.build_dir, basename(script))
            if os.path.exists(outfile) and outfile.endswith(".py"):
                if basename(outfile) == "main.py":
                    dn, fn = split(outfile)
                    newfile = join(dn,"yumex-dnf")
                    log.info("renaming %s -> %s", outfile, basename(newfile))
                    os.rename(outfile, newfile)

setup(name="yumex-dnf",
      version="4.0.2",
      description="Graphical package management tool",
      long_description="",
      author="Tim Lauridsen",
      author_email="timlau@fedoraproject.org",
      url='http://yumex.dk',
      packages=['yumex'],
      package_dir = {'': 'src'},
      scripts=['src/main.py'],
      data_files=[('', ['src/yumex.ui'])],     
      cmdclass={
        'build_scripts': BuildScripts,
      })

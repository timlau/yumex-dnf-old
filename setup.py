#!/usr/bin/python3

import os
from os.path import join, basename, split
from distutils.core import setup
from distutils.util import convert_path
from distutils.command.build_scripts import build_scripts
from distutils import log


RENAME_SCRIPTS = {'main.py': 'yumex-dnf',
                  'update.py': 'yumex-dnf-updatechecker'}

class BuildScripts(build_scripts):
    def run(self):
        build_scripts.run(self)
        for script in self.scripts:
            script = convert_path(script)
            outfile = join(self.build_dir, basename(script))
            if os.path.exists(outfile) and outfile.endswith(".py"):
                if basename(outfile) in RENAME_SCRIPTS:
                    dn, fn = split(outfile)
                    newfile = join(dn, RENAME_SCRIPTS[fn])
                    log.info("renaming %s -> %s", outfile, basename(newfile))
                    os.rename(outfile, newfile)

setup(name="yumex-dnf",
      version="4.3.3",
      description="Graphical package management tool",
      long_description="",
      author="Tim Lauridsen",
      author_email="timlau@fedoraproject.org",
      url='http://yumex.dk',
      packages=['yumex', 'yumex.gui'],
      package_dir={'': 'src'},
      scripts=['src/main.py', 'src/update.py'],
      data_files=[('', ['src/yumex.ui'])],
      cmdclass={
        'build_scripts': BuildScripts,
      })

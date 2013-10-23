#!/usr/bin/python3

import os.path
import os
import sys
import shutil
import glob
import argparse

from subprocess import call

RELEASES = ['19','20','21']
RAWHIDE = '21'
ARCHS = ['i386','x86_64']
BUILD_ROOT = "/home/tim/udv/repos"

class RepoBuild:
    
    def __init__(self, args):
        self.args = args
                    
    def copy_rpm(self, fn, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        shutil.copy(fn,target_dir )
    
    def clean_tree(self):
        for rel in RELEASES:
            for arch in ARCHS:
                target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, arch)
                print("cleaning : %s" % target_dir)
                shutil.rmtree(target_dir, True)
            target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, 'SRPMS')
            print("cleaning : %s" % target_dir)
            shutil.rmtree(target_dir, True)
            
            
    def _clean_dir(self, target_dir, pkgname):            
        print("cleaning : %s" % target_dir)
        files = glob.glob(target_dir+"/*.rpm")
        for fn in files:
            if pkgname in fn:
                print("   --> Removing : %s " % os.path.basename(fn))
                os.unlink(fn)
                
    def clean_rpms(self, pkgname):
        for rel in RELEASES:
            for arch in ARCHS:
                target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, arch)
                self._clean_dir(target_dir, pkgname)
            target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, 'SRPMS')
            self._clean_dir(target_dir, pkgname)

    def build(self):
        for rel in RELEASES:
            build_dir = BUILD_ROOT+"/fedora-%s/mock-build/%s" % (rel,self.args.pkgname)
            print("cleaning : %s" % build_dir)
            shutil.rmtree(build_dir, True)
            print("Mock Building for fedora-%s " % rel)
            if not os.path.exists(build_dir):
                os.makedirs(build_dir)
            if rel != RAWHIDE:
                mock_cmd = "mock -r fedora-%s-i386  %s --resultdir=%s &>/dev/null" % (rel,self.args.srpm, build_dir)
            else:
                mock_cmd = "mock -r fedora-%s-i386  %s --resultdir=%s &>/dev/null" % ("devel", self.args.srpm, build_dir)
            call(mock_cmd, shell=True)
           
    def populate_repo(self):
        for rel in RELEASES:
            build_dir = BUILD_ROOT+"/fedora-%s/mock-build/%s" % (rel,self.args.pkgname)
            for fn in glob.glob(build_dir+"/*.rpm"):
                if not fn.endswith(".src.rpm"):
                    for arch in ARCHS:
                        target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, arch)
                        self.copy_rpm(fn,target_dir )
                else:
                    target_dir = BUILD_ROOT+"/fedora-%s/%s/" % (rel, "SRPMS")
                    self.copy_rpm(fn,target_dir )

def main():
    parser = argparse.ArgumentParser(description='Yumex Test Repo helper')
    parser.add_argument( 'pkgname', help="package name to build")
    parser.add_argument( 'srpm', help="self.args.srpm filename to build ")
    parser.add_argument( '--clean', action='store_true', help="clean repo tree from rpms")
    parser.add_argument( '--build', action='store_true', help="mock build rpms for all fedora releases (F19, F20, F21)")
    parser.add_argument( '--copy', action='store_true', help="copy build rpms into repo tree")
    args = parser.parse_args()
    rb = RepoBuild(args)
    if args.clean:
        rb.clean_tree()
    if args.build:
        rb.build()
    if args.copy:
        rb.clean_rpms(args.pkgname)
        rb.populate_repo()
        
    
if __name__ == '__main__':
    main()


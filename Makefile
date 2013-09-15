SUBDIRS = src src/yumex
PYFILES = $(wildcard *.py)
PKGNAME = yumex
APPNAME = yumex-nextgen
VERSION=$(shell awk '/Version:/ { print $$2 }' ${APPNAME}.spec)
SRCDIR=src
MISCDIR=misc
PIXDIR=gfx
ALLDIRS=$(SUBDIRS) gfx misc tools
GITDATE=git$(shell date +%Y%m%d)
VER_REGEX=\(^Version:\s*[0-9]*\.[0-9]*\.\)\(.*\)
BUMPED_MINOR=${shell VN=`cat ${APPNAME}.spec | grep Version| sed  's/${VER_REGEX}/\2/'`; echo $$(($$VN + 1))}
NEW_VER=${shell cat ${APPNAME}.spec | grep Version| sed  's/\(^Version:\s*\)\([0-9]*\.[0-9]*\.\)\(.*\)/\2${BUMPED_MINOR}/'}
NEW_REL=0.1.${GITDATE}
all: subdirs
	
subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1 ; done

clean:
	@rm -fv *~ *.tar.gz *.list *.lang 
	for d in $(SUBDIRS); do make -C $$d clean ; done

install:
	mkdir -p $(DESTDIR)/usr/share/$(APPNAME)
	mkdir -p $(DESTDIR)/usr/share/applications
	mkdir -p $(DESTDIR)/usr/share/icons/hicolor/scalable/apps
	mkdir -p $(DESTDIR)/usr/share/icons/hicolor/48x48/apps	
	mkdir -p $(DESTDIR)/usr/bin
	install -m644 $(PIXDIR)/yumex-icon.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/$(APPNAME).svg
	install -m644 $(PIXDIR)/yumex-icon.png $(DESTDIR)/usr/share/icons/hicolor/48x48/apps/$(APPNAME).png
	# build & install desktop file with translations
	@rm -f $(MISCDIR)/$(APPNAME).desktop
	intltool-merge -d -u $(PODIR) $(MISCDIR)/$(APPNAME).desktop.in $(MISCDIR)/$(APPNAME).desktop
	install -m644 $(MISCDIR)/$(APPNAME).desktop $(DESTDIR)/usr/share/applications/.
	
	for d in $(SUBDIRS); do make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; [ $$? = 0 ] || exit 1; done

get-builddeps:
	yum install perl-TimeDate python3-devel gettext intltool rpmdevtools python3-gobject

archive:
	@rm -rf ${PKGNAME}-${VERSION}.tar.gz
	@git archive --format=tar --prefix=$(PKGNAME)-$(VERSION)/ HEAD | gzip -9v >${PKGNAME}-$(VERSION).tar.gz
	@cp ${PKGNAME}-$(VERSION).tar.gz $(shell rpm -E '%_sourcedir')
	@rm -rf ${PKGNAME}-${VERSION}.tar.gz
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"
	
# needs perl-TimeDate for git2cl
changelog:
	@git log --pretty --numstat --summary | tools/git2cl > ChangeLog
	
upload: FORCE
	@scp ~/rpmbuild/SOURCES/${PKGNAME}-${VERSION}.tar.gz yum-extender.org:public_html/dnl/yumex/source/.
    
release:
	@git commit -a -m "bumped version to $(VERSION)"
	@$(MAKE) changelog
	@git commit -a -m "updated ChangeLog"
	@git push
	@git tag -f -m "Added ${PKGNAME}-${VERSION} release tag" ${PKGNAME}-${VERSION}
	@git push --tags origin
	@$(MAKE) archive
	@$(MAKE) upload

test-cleanup:	
	@rm -rf ${PKGNAME}-${VERSION}.test.tar.gz
	@echo "Cleanup the git release-test local branch"
	@git checkout -f
	@git checkout future
	@git branch -D release-test

show-vars:
	@echo ${GITDATE}
	@echo ${BUMPED_MINOR}
	@echo ${NEW_VER}-${NEW_REL}
	
test-release:
	@git checkout -b release-test
	# +1 Minor version and add 0.1-gitYYYYMMDD release
	@cat ${APPNAME}.spec | sed  -e 's/${VER_REGEX}/\1${BUMPED_MINOR}/' -e 's/\(^Release:\s*\)\([0-9]*\)\(.*\)./\10.1.${GITDATE}%{?dist}/' > ${APPNAME}-test.spec ; mv ${APPNAME}-test.spec ${APPNAME}.spec
	@git commit -a -m "bumped ${PKGNAME} version ${NEW_VER}-${NEW_REL}"
	# Make Changelog
	@git log --pretty --numstat --summary | ./tools/git2cl > ChangeLog
	@git commit -a -m "updated ChangeLog"
    # Make archive
	@rm -rf ${APPNAME}-${NEW_VER}.tar.gz
	@git archive --format=tar --prefix=$(APPNAME)-$(NEW_VER)/ HEAD | gzip -9v >${APPNAME}-$(NEW_VER).tar.gz
	# Build RPMS
	@rpmdev-wipetree
	@rpmbuild -ta ${APPNAME}-${NEW_VER}.tar.gz
	@$(MAKE) test-cleanup
	
rpm:
	@$(MAKE) archive
	@rpmbuild -ba $(APPNAME).spec
	
test-builds:
	@$(MAKE) test-release
	@ssh timlau.fedorapeople.org rm public_html/files/yumex/*
	@scp ${PKGNAME}-${NEW_VER}.tar.gz timlau.fedorapeople.org:public_html/files/yumex/${PKGNAME}-${NEW_VER}-${GITDATE}.tar.gz
	@scp ~/rpmbuild/RPMS/noarch/${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.
	@scp ~/rpmbuild/SRPMS/${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.

		
FORCE:
    

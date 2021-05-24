APPNAME = yumex-dnf
DATADIR = /usr/share
PYTHON = python3 
SUBDIRS = gfx misc po
VERSION=$(shell awk '/Version:/ { print $$2 }' ${APPNAME}.spec)
GITDATE=git$(shell date +%Y%m%d)
VER_REGEX=\(^Version:\s*[0-9]*\.[0-9]*\.\)\(.*\)
BUMPED_MINOR=${shell VN=`cat ${APPNAME}.spec | grep Version| sed  's/${VER_REGEX}/\2/'`; echo $$(($$VN + 1))}
NEW_VER=${shell cat ${APPNAME}.spec | grep Version| sed  's/\(^Version:\s*\)\([0-9]*\.[0-9]*\.\)\(.*\)/\2${BUMPED_MINOR}/'}
NEW_REL=0.1.${GITDATE}
DIST=${shell rpm --eval "%{dist}"}
GIT_MASTER=develop
CURDIR = ${shell pwd}
BUILDDIR= $(CURDIR)/build

all: build

$(SUBDIRS):
	$(MAKE) -C $@ 

INSTALL_TARGETS = $(SUBDIRS:%=install-%)
$(INSTALL_TARGETS):
	$(MAKE) -C $(@:install-%=%) install DESTDIR=$(DESTDIR) DATADIR=$(DATADIR)

CLEAN_TARGETS = $(SUBDIRS:%=clean-%)
$(CLEAN_TARGETS):
	$(MAKE) -C $(@:clean-%=%) clean

build: $(SUBDIRS)
	$(PYTHON) setup.py build

install: all $(INSTALL_TARGETS)
	$(PYTHON) setup.py install --skip-build --root $(DESTDIR) --install-data=$(DATADIR)/$(APPNAME)

clean: $(CLEAN_TARGETS)
	$(PYTHON) setup.py clean
	-rm -f *.tar.gz
	-rm -rf build
	-rm -rf dist
	

get-builddeps:
	@sudo dnf install python3-devel python3-gobject gettext intltool transifex-client

archive:
	@rm -rf ${APPNAME}-${VERSION}.tar.gz
	@git archive --format=tar --prefix=$(APPNAME)-$(VERSION)/ HEAD | gzip -9v >${APPNAME}-$(VERSION).tar.gz
	@mkdir -p ${BUILDDIR}/SOURCES
	@cp ${APPNAME}-$(VERSION).tar.gz ${BUILDDIR}/SOURCES
	@rm -rf ${APPNAME}-${VERSION}.tar.gz
	@echo "The archive is in ${BUILDDIR}/SOURCES/${APPNAME}-$(VERSION).tar.gz"
	
changelog:
	$(PYTHON) tools/git2cl.py
	
upload: 
	@scp $(BUILDDIR)/SOURCES/${APPNAME}-${VERSION}.tar.gz yum-extender.org:public_html/dnl/yumex/source/.
	
release-branch:
	@git branch -m ${GIT_MASTER} release-${VERSION}

release-publish:
	@git checkout release-${VERSION}
	@git commit -a -m "bumped version to $(VERSION)"
	@$(MAKE) changelog
	@git commit -a -m "updated ChangeLog"
	@git checkout release-devel
	@git merge --no-ff release-${VERSION} -m "merge ${APPNAME}-${VERSION} release"
	@git tag -f -m "Added ${APPNAME}-${VERSION} release tag" ${APPNAME}-${VERSION}
	@git push --tags origin
	@$(MAKE) archive
	@$(MAKE) rpm

release-cleanup:	
	@git checkout develop
	@git merge --no-ff release-${VERSION} -m "merge ${APPNAME}-${VERSION} release"
	@git push origin
	@git branch -D release-${VERSION}

test-cleanup:	
	@rm -rf ${APPNAME}-${VERSION}.test.tar.gz
	@echo "Cleanup the git release-test local branch"
	@git checkout -f
	@git checkout ${GIT_MASTER}
	@git branch -D release-test

show-vars:
	@echo ${GITDATE}
	@echo ${BUMPED_MINOR}
	@echo ${NEW_VER}-${NEW_REL}
	
test-release:
	@git checkout -b release-test
	# +1 Minor version and add 0.1-gitYYYYMMDD release
	@cat ${APPNAME}.spec | sed  -e 's/${VER_REGEX}/\1${BUMPED_MINOR}/' -e 's/\(^Release:\s*\)\([0-9]*\)\(.*\)./\10.1.${GITDATE}%{?dist}/' > ${APPNAME}-test.spec ; mv ${APPNAME}-test.spec ${APPNAME}.spec
	@git commit -a -m "bumped ${APPNAME} version ${NEW_VER}-${NEW_REL}"
	# Make Changelog
	$(PYTHON) tools/git2cl.py
	@git commit -a -m "updated ChangeLog"
	# Make archive
	@rm -rf ${APPNAME}-${NEW_VER}.tar.gz
	@git archive --format=tar --prefix=$(APPNAME)-$(NEW_VER)/ HEAD | gzip -9v >${APPNAME}-$(NEW_VER).tar.gz
	# Build RPMS
	@-rpmbuild --define '_topdir $(BUILDDIR)' -ta ${APPNAME}-${NEW_VER}.tar.gz
	@$(MAKE) test-cleanup
	
rpm:
	@$(MAKE) archive
	@rpmbuild --define '_topdir $(BUILDDIR)' -ta ${BUILDDIR}/SOURCES/${APPNAME}-$(VERSION).tar.gz

test-builds:
	@$(MAKE) test-release
	@ssh timlau.fedorapeople.org rm public_html/files/yumex/*
	@scp ${APPNAME}-${NEW_VER}.tar.gz timlau.fedorapeople.org:public_html/files/yumex/${APPNAME}-${NEW_VER}-${GITDATE}.tar.gz
	@scp $(BUILDDIR)/RPMS/noarch/${APPNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.
	@scp $(BUILDDIR)/SRPMS/${APPNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.

test-upd:
	@$(MAKE) test-release
	sudo dnf update $(BUILDDIR)/RPMS/noarch/${APPNAME}-${NEW_VER}-${NEW_REL}*.rpm

test-inst:
	@$(MAKE) test-release
	sudo dnf install $(BUILDDIR)/RPMS/noarch/${APPNAME}-${NEW_VER}-${NEW_REL}*.rpm
	
test-reinst:
	@$(MAKE) test-release
	sudo dnf reinstall $(BUILDDIR)/RPMS/noarch/${APPNAME}-${NEW_VER}-${NEW_REL}*.rpm

test-copr:
	@$(MAKE) test-release
	copr-cli build yumex-dnf $(BUILDDIR)/RPMS/noarch/${APPNAME}-${NEW_VER}-${NEW_REL}*.rpm

	
transifex-setup:
	tx init
	tx set --auto-remote https://www.transifex.com/projects/p/yumex/
	tx set --auto-local  -r yumex.${APPNAME} 'po/<lang>.po' --source-lang en --source-file po/${APPNAME}.pot --execute


transifex-pull:
	tx pull -a -f
	@echo "You can now git commit -a -m 'Transfix pull, *.po update'"

transifex-push:
	make -C po ${APPNAME}.pot
	tx push -s
	@echo "You can now git commit -a -m 'Transfix push, ${APPNAME}.pot update'"
	

status-exit:
	/usr/bin/dbus-send --session --print-reply --dest=dk.yumex.StatusIcon / dk.yumex.StatusIcon.Exit
	
status-checkupdates:
	/usr/bin/dbus-send --session --print-reply --dest=dk.yumex.StatusIcon / dk.yumex.StatusIcon.Start
	/usr/bin/dbus-send --session --print-reply --dest=dk.yumex.StatusIcon / dk.yumex.StatusIcon.CheckUpdates
	
status-run:
	cd dbus && ./dbus_status.py -v -d

.PHONY: all archive install clean build
.PHONY: $(SUBDIRS) $(INSTALL_TARGETS) $(CLEAN_TARGETS)
.PHONY: test-reinst test-inst mock-build rpm test-release test-cleanup show-vars release upload	get-builddeps changelog
.PHONY: test-copr	
	

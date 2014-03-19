APPNAME = yumex-dnf
DATADIR = /usr/share
PYTHON = python3 
SUBDIRS = gfx misc dbus po
VERSION=$(shell awk '/Version:/ { print $$2 }' ${APPNAME}.spec)
GITDATE=git$(shell date +%Y%m%d)
VER_REGEX=\(^Version:\s*[0-9]*\.[0-9]*\.\)\(.*\)
BUMPED_MINOR=${shell VN=`cat ${APPNAME}.spec | grep Version| sed  's/${VER_REGEX}/\2/'`; echo $$(($$VN + 1))}
NEW_VER=${shell cat ${APPNAME}.spec | grep Version| sed  's/\(^Version:\s*\)\([0-9]*\.[0-9]*\.\)\(.*\)/\2${BUMPED_MINOR}/'}
NEW_REL=0.1.${GITDATE}
DIST=${shell rpm --eval "%{dist}"}
GIT_MASTER=master

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
	@sudo dnf install python3-devel python3-gobject perl-TimeDate gettext intltool transifex-client

archive:
	@rm -rf ${APPNAME}-${VERSION}.tar.gz
	@git archive --format=tar --prefix=$(APPNAME)-$(VERSION)/ HEAD | gzip -9v >${APPNAME}-$(VERSION).tar.gz
	@cp ${APPNAME}-$(VERSION).tar.gz $(shell rpm -E '%_sourcedir')
	@rm -rf ${APPNAME}-${VERSION}.tar.gz
	@echo "The archive is in ${APPNAME}-$(VERSION).tar.gz"
	
# needs perl-TimeDate for git2cl
changelog:
	@git log --pretty --numstat --summary | tools/git2cl > ChangeLog
	
upload: 
	@scp ~/rpmbuild/SOURCES/${APPNAME}-${VERSION}.tar.gz yum-extender.org:public_html/dnl/yumex/source/.
	
release:
	@git commit -a -m "bumped version to $(VERSION)"
	@$(MAKE) changelog
	@git commit -a -m "updated ChangeLog"
	@git push
	@git tag -f -m "Added ${APPNAME}-${VERSION} release tag" ${APPNAME}-${VERSION}
	@git push --tags origin
	@$(MAKE) archive
	@$(MAKE) upload

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
	@git log --pretty --numstat --summary | ./tools/git2cl > ChangeLog
	@git commit -a -m "updated ChangeLog"
	# Make archive
	@rm -rf ${APPNAME}-${NEW_VER}.tar.gz
	@git archive --format=tar --prefix=$(APPNAME)-$(NEW_VER)/ HEAD | gzip -9v >${APPNAME}-$(NEW_VER).tar.gz
	# Build RPMS
	@-rpmbuild -ta ${APPNAME}-${NEW_VER}.tar.gz
	@$(MAKE) test-cleanup
	
rpm:
	@$(MAKE) archive
	@rpmbuild -ba $(APPNAME).spec

test-builds:
	@$(MAKE) test-release
	@ssh timlau.fedorapeople.org rm public_html/files/yumex/*
	@scp ${APPNAME}-${NEW_VER}.tar.gz timlau.fedorapeople.org:public_html/files/yumex/${APPNAME}-${NEW_VER}-${GITDATE}.tar.gz
	@scp ~/rpmbuild/RPMS/noarch/${APPNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.
	@scp ~/rpmbuild/SRPMS/${APPNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/yumex/.

test-inst:
	@$(MAKE) test-release
	sudo dnf install ~/rpmbuild/RPMS/noarch/${APPNAME}-${NEW_VER}-${NEW_REL}*.rpm
	
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
	

.PHONY: all archive install clean build
.PHONY: $(SUBDIRS) $(INSTALL_TARGETS) $(CLEAN_TARGETS)
.PHONY: test-reinst test-inst mock-build rpm test-release test-cleanup show-vars release upload	get-builddeps changelog	
	

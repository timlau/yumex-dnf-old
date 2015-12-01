APPNAME = yumex-dnf
DATADIR = /usr/share
PODIR=../po

all: build

clean: 
	@rm -f $(APPNAME).desktop
	@rm -f $(APPNAME)-local.desktop
	@rm -f $(APPNAME).appdata.xml
	
build: clean
	intltool-merge -d -u $(PODIR) $(APPNAME).desktop.in $(APPNAME).desktop
	intltool-merge -d -u $(PODIR) $(APPNAME)-local.desktop.in $(APPNAME)-local.desktop
	intltool-merge -x -u $(PODIR) $(APPNAME).appdata.xml.in $(APPNAME).appdata.xml

install: build
	install -d $(DESTDIR)$(DATADIR)/applications
	install -d $(DESTDIR)$(DATADIR)/$(APPNAME)
	install -d $(DESTDIR)$(DATADIR)/appdata
	install -m644 $(APPNAME).desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-local.desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-updater.desktop $(DESTDIR)$(DATADIR)/$(APPNAME)/.
	install -m644 $(APPNAME).appdata.xml $(DESTDIR)$(DATADIR)/appdata/.

.PHONY: all install clean build

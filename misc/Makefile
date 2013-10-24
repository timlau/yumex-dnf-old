APPNAME = yumex-nextgen
DATADIR = /usr/share
PODIR=../po

all: build

clean: 
	@rm -f $(APPNAME).desktop
	@rm -f $(APPNAME)-local.desktop
	
build: clean
	intltool-merge -d -u $(PODIR) $(APPNAME).desktop.in $(APPNAME).desktop
	intltool-merge -d -u $(PODIR) $(APPNAME)-local.desktop.in $(APPNAME)-local.desktop

install: build
	install -d $(DESTDIR)$(DATADIR)/applications
	install -d $(DESTDIR)$(DATADIR)/$(APPNAME)
	install -m644 $(APPNAME).desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-local.desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-autostart.desktop $(DESTDIR)$(DATADIR)/$(APPNAME)/.

.PHONY: all install clean build

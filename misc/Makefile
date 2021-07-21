APPNAME = yumex-dnf
DATADIR = /usr/share
PODIR=../po

all: build

clean: 
	@rm -f $(APPNAME).desktop
	@rm -f $(APPNAME)-local.desktop
	@rm -f $(APPNAME).appdata.xml

sass:	
	pysassc -t expanded scss/Dracula.scss themes/Dracula.theme
	pysassc -t expanded scss/One-Dark.scss themes/One-Dark.theme
	pysassc -t expanded scss/System-Dark.scss themes/System-Dark.theme
	pysassc -t expanded scss/System-Light.scss themes/System-Light.theme
	
build: clean sass
	intltool-merge -d -u $(PODIR) $(APPNAME).desktop.in $(APPNAME).desktop
	intltool-merge -d -u $(PODIR) $(APPNAME)-local.desktop.in $(APPNAME)-local.desktop
	intltool-merge -x -u $(PODIR) $(APPNAME).appdata.xml.in $(APPNAME).appdata.xml

install: build
	install -d $(DESTDIR)$(DATADIR)/applications
	install -d $(DESTDIR)$(DATADIR)/$(APPNAME)
	install -d $(DESTDIR)$(DATADIR)/$(APPNAME)/themes
	install -d $(DESTDIR)$(DATADIR)/appdata
	install -m644 $(APPNAME).desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-local.desktop $(DESTDIR)$(DATADIR)/applications/.
	install -m644 $(APPNAME)-updater.desktop $(DESTDIR)$(DATADIR)/$(APPNAME)/.
	install -m644 $(APPNAME).appdata.xml $(DESTDIR)$(DATADIR)/appdata/.
	install -m644 themes/* $(DESTDIR)$(DATADIR)/$(APPNAME)/themes/.

.PHONY: all install clean build sass

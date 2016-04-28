APPNAME = yumex-dnf
DATADIR = /usr/share

all: 
	echo "Nothing to do"

clean:
	echo "Nothing to do"

install:
	mkdir -p $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps
	mkdir -p $(DESTDIR)$(DATADIR)/icons/hicolor/48x48/apps	
	install -m644 yumex-icon.svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APPNAME).svg
	install -m644 yumex-icon.png $(DESTDIR)$(DATADIR)/icons/hicolor/48x48/apps/$(APPNAME).png

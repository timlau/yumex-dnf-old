ORG_NAME = dk.yumex.StatusIcon
DATADIR = /usr/share
APPNAME = yumex-dnf

all:
	@echo notthing to do
	
clean:
	@echo notthing to do

install:
	mkdir -p $(DESTDIR)/usr/share/dbus-1/services
	install -m644 $(ORG_NAME).service $(DESTDIR)$(DATADIR)/dbus-1/services/.
	install -m755 dbus_status.py $(DESTDIR)$(DATADIR)/$(APPNAME)/.


.PHONY: all install clean

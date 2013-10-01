PKGNAME = yumex
APPNAME = yumex-nextgen
PKGDIR = /usr/share/$(APPNAME)

all: 
	echo "Nothing to do"

clean:
	rm -fv *.pyc *.pyo *~ *.bak *.gladep

install:
	mkdir -p $(DESTDIR)/$(PKGDIR)
	mkdir -p $(DESTDIR)/usr/bin
	install -m755 main.py $(DESTDIR)/usr/bin/$(APPNAME)
	install -m644 yumex.ui $(DESTDIR)/$(PKGDIR)/.
	install -m755 dbus_status.py $(DESTDIR)/$(PKGDIR)/.

kill:
	@-killall -9 -r "main\.py" &> /dev/null 
	@/usr/bin/dbus-send --session --print-reply --dest="org.baseurl.YumSession" / org.baseurl.YumSession.Exit &> /dev/null 

status-load:
	@./dbus_status.py -v -d
	
status-exit:
	@/usr/bin/dbus-send --session --print-reply --dest="dk.yumex.StatusIcon" / dk.yumex.StatusIcon.Exit
	
status-start:
	@/usr/bin/dbus-send --session --print-reply --dest="dk.yumex.StatusIcon" / dk.yumex.StatusIcon.Start

status-checkupdates:
	@/usr/bin/dbus-send --session --print-reply --dest="dk.yumex.StatusIcon" / dk.yumex.StatusIcon.CheckUpdates
	
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

kill:
	@-killall -9 -r "main\.py" &> /dev/null 
	@/usr/bin/dbus-send --session --print-reply --dest="org.baseurl.YumSession" / org.baseurl.YumSession.Exit &> /dev/null 


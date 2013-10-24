all: 
	echo "Nothing to do"

clean:
	rm -fv *.pyc *.pyo *~ *.bak *.gladep

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
	
error-cleanup:
	@/usr/bin/dbus-send --session --print-reply --dest="dk.yumex.StatusIcon" / dk.yumex.StatusIcon.Exit
	@/usr/bin/dbus-send --session --print-reply --dest="org.baseurl.YumSession" / org.baseurl.YumSession.Exit
	@sudo /usr/bin/dbus-send --system --print-reply --dest="org.baseurl.YumSystem" / org.baseurl.YumSystem.Exit

	

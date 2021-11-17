NLSPACKAGE = yumex-dnf
CATALOGS = $(shell ls *.po)

LINGUAS:
	@for file in $(CATALOGS); do \
		lang=`basename $$file .po`; \
		echo "$${lang#../}" ; \
	done > $@
   
distclean: 
	rm -f $(NLSPACKAGE).pot POTFILES.in LINGUAS


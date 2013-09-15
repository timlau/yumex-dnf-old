PYTHON=python3
PACKAGE = $(shell basename `pwd`)
PYFILES = $(wildcard *.py)
PYVER := $(shell $(PYTHON) -c 'import sys; print( "%.3s" %(sys.version))')
PYSYSDIR := $(shell $(PYTHON) -c 'import sys; print(sys.prefix)')
PYLIBDIR = $(PYSYSDIR)/lib/python$(PYVER)
PKGDIR = $(PYLIBDIR)/site-packages/$(PACKAGE)

all: 
	echo "Nothing to do"

clean:
	rm -rf *.pyc *.pyo *~ __pycache__

install:
	mkdir -p $(DESTDIR)/$(PKGDIR)
	for p in $(PYFILES) ; do \
		install -m 755 $$p $(DESTDIR)/$(PKGDIR)/$$p; \
	done

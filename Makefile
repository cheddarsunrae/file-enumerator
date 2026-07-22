SHELL := /bin/sh

PREFIX ?= /usr/local
DESTDIR ?=
BINDIR := $(DESTDIR)$(PREFIX)/bin
MANDIR := $(DESTDIR)$(PREFIX)/share/man/man1
BASHCOMPDIR := $(DESTDIR)$(PREFIX)/share/bash-completion/completions

PROGRAM := file-enumerator
VERSION := $(shell cat VERSION)
DIST_NAME := $(PROGRAM)-$(VERSION)

.PHONY: all help test install uninstall dist bundle release clean verify

all: test

help:
	@printf '%s\n' \
	  'make test                 Run the test suite' \
	  'make install              Install under PREFIX (default /usr/local)' \
	  'make uninstall            Remove files installed by make install' \
	  'make dist                 Build source tar.gz and zip archives' \
	  'make bundle               Build archives plus a complete Git bundle' \
	  'make release              Run validation and build all release artifacts' \
	  'make verify               Syntax, tests, man-page, and archive checks' \
	  'make clean                Remove generated build artifacts' \
	  '' \
	  'Examples:' \
	  '  sudo make install' \
	  '  sudo make uninstall' \
	  '  make install PREFIX=$$HOME/.local'

test:
	python3 -m unittest discover -s tests -v

install:
	install -d "$(BINDIR)" "$(MANDIR)" "$(BASHCOMPDIR)"
	install -m 0755 src/$(PROGRAM) "$(BINDIR)/$(PROGRAM)"
	install -m 0644 man/$(PROGRAM).1 "$(MANDIR)/$(PROGRAM).1"
	install -m 0644 completions/$(PROGRAM).bash "$(BASHCOMPDIR)/$(PROGRAM)"
	@printf '%s\n' "Installed $(PROGRAM) $(VERSION) under $(DESTDIR)$(PREFIX)"
	@if [ -z "$(DESTDIR)" ] && command -v mandb >/dev/null 2>&1; then mandb -q "$(PREFIX)/share/man" 2>/dev/null || true; fi

uninstall:
	rm -f "$(BINDIR)/$(PROGRAM)"
	rm -f "$(MANDIR)/$(PROGRAM).1" "$(MANDIR)/$(PROGRAM).1.gz"
	rm -f "$(BASHCOMPDIR)/$(PROGRAM)"
	@printf '%s\n' "Removed $(PROGRAM) from $(DESTDIR)$(PREFIX)"
	@if [ -z "$(DESTDIR)" ] && command -v mandb >/dev/null 2>&1; then mandb -q "$(PREFIX)/share/man" 2>/dev/null || true; fi

dist: clean
	mkdir -p build/$(DIST_NAME) dist
	cp -a README.md CHANGELOG.md LICENSE VERSION Makefile src man completions packaging scripts tests contrib docs .github build/$(DIST_NAME)/
	find build/$(DIST_NAME) -type d -name __pycache__ -prune -exec rm -rf {} +
	tar -C build -czf dist/$(DIST_NAME).tar.gz $(DIST_NAME)
	cd build && zip -qr ../dist/$(DIST_NAME).zip $(DIST_NAME)
	cd dist && sha256sum $(DIST_NAME).tar.gz $(DIST_NAME).zip > SHA256SUMS.txt

bundle: dist
	git bundle create dist/$(PROGRAM).git.bundle --all
	cd dist && sha256sum $(DIST_NAME).tar.gz $(DIST_NAME).zip $(PROGRAM).git.bundle > SHA256SUMS.txt

release: verify bundle
	cd dist && sha256sum -c SHA256SUMS.txt

verify:
	python3 -m py_compile src/$(PROGRAM)
	bash -n scripts/*.sh
	$(MAKE) test
	@if command -v groff >/dev/null 2>&1; then groff -man -Tutf8 man/$(PROGRAM).1 >/dev/null; else echo 'groff not installed; skipped man-page render check'; fi
	$(MAKE) dist
	cd dist && sha256sum -c SHA256SUMS.txt

clean:
	rm -rf build
	rm -f dist/$(DIST_NAME).tar.gz dist/$(DIST_NAME).zip dist/$(PROGRAM).git.bundle dist/SHA256SUMS.txt
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete

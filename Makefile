ROOT = /var/www/oaza.woju.eu/html
RM ?= rm -f

all:
	lektor build --output-path $(ROOT) --buildstate-path . $(LEKTOROPTS)
.PHONY: all

rebuild:
	$(RM) buildstate
	$(MAKE) all
.PHONY: rebuild

check:
	./bin/check.py
.PHONY: rebuild check

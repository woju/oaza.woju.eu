LEKTOR_OUTPUT_PATH = /var/www/oaza.woju.eu/html
export LEKTOR_OUTPUT_PATH
RM ?= rm -f

all:
	lektor build --buildstate-path . $(LEKTOROPTS)
.PHONY: all

rebuild:
	$(RM) buildstate
	$(MAKE) all
.PHONY: rebuild

check:
	./bin/check.py
.PHONY: rebuild check

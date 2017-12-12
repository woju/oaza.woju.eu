ROOT = /var/www/oaza.woju.eu/html
RM ?= rm -f

all:
	lektor build --output-path $(ROOT) --buildstate-path . $(LEKTOROPTS)

rebuild:
	$(RM) buildstate
	$(MAKE) all
.PHONY: all rebuild

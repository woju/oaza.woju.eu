ROOT = /var/www/oaza.woju.eu/html

all:
	lektor build -O $(ROOT) $(LEKTOROPTS)
.PHONY: all

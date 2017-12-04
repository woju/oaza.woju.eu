ROOT = /var/www/oaza.woju.eu/html

all:
	lektor build -O $(ROOT)
.PHONY: all

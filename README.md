# pinolo: The naughty IRC bot

pinolo is an IRC bot written for fun; it has support for multiple
connections, SSL servers, plugins and some other nice features.

## Requirements

It has been written and tested with Python 2.6 and 2.7.

- python >= 2.6, untested with 3.x
- SQLAlchemy 0.7.x (only needed by plugins)

- requests 1.2.x (for http based plugins)
- beautifulsoup4 4.1.x (for http and html based plugins)
- Whoosh 2.4.x (for quotes plugins)
- PyStemmer 1.3.x (for quotes plugin)

## Getting started

See `sample.cfg` for an example of the configuration file, then create
one and remember to create the `datadir` directory.

### From source

 - Check out the pinolo source code using git:

	git clone http://git.spatof.org/pinolo.git

 - Install pinolo (better in a virtualenv):

	python setup.py install

### Development mode

- Install pinolo in development mode:

	cd pinolo/
	python setup.py develop

## Notes

Pinolo has been recently rewritten to avoid `gevent` so some part of
the codes still need to be polished.

## License

BSD, see included *LICENSE* file.

Author(s):

- Daniel Kertesz <daniel@spatof.org>

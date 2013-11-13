# pinolo: The naughty IRC bot

pinolo is an IRC bot written for fun; it has support for multiple connections, SSL servers, plugins and some other nice features.

PLEASE NOTE: This was my pet project when some years ago I wanted to learn Python and it has been rewritten many times; the code is highly unorganized, full of mixed language comments and various experiments. In the end I think that you could be able to run Pinolo only if you are me :) Nevertheless some pieces of code might be interesting for other people, so I decided to release the code "as is", even if I can't offer active support.

## Requirements

It has been written and tested with Python 2.6 and 2.7.

- python >= 2.6, untested with 3.x
- SQLAlchemy 0.7.x (only needed by plugins; maybe 0.8.x and 0.9.x are ok too)

- requests 1.2.x (for http based plugins)
- beautifulsoup4 4.1.x (for http and html based plugins)
- Whoosh 2.4.x (for quotes plugins)
- PyStemmer 1.3.x (for quotes plugin)

## Getting started

You can download the source code from the GitHub repository; to install Pinolo you have to follow the usual `python setup.py install`.

Check out `sample_config.coil` for an example configuration and remember to create the `datadir` directory.

## Notes

Pinolo has been recently rewritten to avoid `gevent` so some part of the codes still need to be polished.

## License

BSD, see included *LICENSE* file.

Author(s):

- Daniel Kertesz <daniel@spatof.org>

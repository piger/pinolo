#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration handling
"""

import sys
import os
from pprint import pprint
from ConfigParser import SafeConfigParser, NoOptionError

from twisted.python import log
from twisted.internet import reactor, ssl

from pinolo.irc import PinoloFactory


def run_foreground(servers):
    """Run pinolo in foreground.
    """

    log.startLogging(sys.stdout)

    f = PinoloFactory(servers)

    for address, port in servers:
        if port == 9999:
            # ispirato da:
            # http://books.google.it/books?id=Fm5kw3lZ7zEC&pg=PA112&lpg=PA112&dq=ClientContextFactory&source=bl&ots=mlx8EdNiTS&sig=WfqDy9SztfB9xx1JQnxicdouhW0&hl=en&ei=OjF8S7_XBsyh_AayiuH5BQ&sa=X&oi=book_result&ct=result&resnum=7&ved=0CB4Q6AEwBg#v=onepage&q=ClientContextFactory&f=false
            # uso un ClientContextFactory() per ogni connessione.
            moo = reactor.connectSSL(address, port, f, ssl.ClientContextFactory())
        else:
            moo = reactor.connectTCP(address, port, f)

        # moo.name = "%s:%i" % (address, port)
        moo.name = servers[(address, port)]['name']

    reactor.run()


def parse_config_file(filename):
    """Parse a configuration file, exit on errors."""

    if not os.access(filename, os.R_OK):
        print _("[ERROR] Cannot read config file [%s], check existence and "
                "permissions." % filename)
        sys.exit(1)

    config = SafeConfigParser()
    config.read(filename)
    servers = {}

    try:
        for section in [s for s in config.sections() if s.startswith('Server')]:
            server = _parse_server_config(config, section)
            key = (server['address'], server['port'])
            servers[key] = server

    except NoOptionError, e:
        print _('[ERROR] Missing configuration parameter: "%s" in section "%s"' %
                (e.option, section))
        sys.exit(1)

    pprint(servers)

    return servers


def _parse_server_config(config, section):
    """Parse a single server configuration.

    Returns:
        a dict with the server configuration.

    Raises:
        NoOptionError if a mandatory parameter is not found.
    """

    server = {}

    address = config.get(section, 'address')
    port = int(config.get(section, 'port'))

    server['address'] = address
    server['port'] = port

    server['channels'] = [s.strip() for s in config.get(section,
                                                        'channels').split(',')]
    server['name'] = config.get(section, 'name')
    server['nickname'] = config.get(section, 'nickname')

    if config.has_option(section, 'password'):
        server['password'] = config.get(section, 'password')
    else:
        server['password'] = None

    return server

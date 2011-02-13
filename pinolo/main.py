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

from irc2 import IRCServer, PinoloFactory


def run_foreground(servers):
    """Run pinolo in foreground.
    """

    log.startLogging(sys.stdout)

    f = PinoloFactory(*servers)

    for server in f.servers:
        if server.ssl:
            # ispirato da:
            # http://books.google.it/books?id=Fm5kw3lZ7zEC&pg=PA112&lpg=PA112&dq=ClientContextFactory&source=bl&ots=mlx8EdNiTS&sig=WfqDy9SztfB9xx1JQnxicdouhW0&hl=en&ei=OjF8S7_XBsyh_AayiuH5BQ&sa=X&oi=book_result&ct=result&resnum=7&ved=0CB4Q6AEwBg#v=onepage&q=ClientContextFactory&f=false
            # uso un ClientContextFactory() per ogni connessione.
            moo = reactor.connectSSL(server.address, server.port, f, ssl.ClientContextFactory())
        else:
            moo = reactor.connectTCP(server.address, server.port, f)

        server.connector = moo

    reactor.run()


def parse_config_file(filename):
    """Parse a configuration file, exit on errors."""

    if not os.access(filename, os.R_OK):
        print _("[ERROR] Cannot read config file [%s], check existence and "
                "permissions." % filename)
        sys.exit(1)

    config = SafeConfigParser()
    config.read(filename)
    servers = []

    try:
        for section in [s for s in config.sections() if s.startswith('Server')]:
            server = _parse_server_config(config, section)
            servers.append(server)

    except NoOptionError, e:
        print _('[ERROR] Missing configuration parameter: "%s" in section "%s"' %
                (e.option, section))
        sys.exit(1)

    return servers


def _parse_server_config(config, section):
    """Parse a single server configuration.

    Returns:
        a dict with the server configuration.

    Raises:
        NoOptionError if a mandatory parameter is not found.
    """

    hostname = config.get(section, 'address')
    port = int(config.get(section, 'port'))

    channels = [s.strip() for s in config.get(section, 'channels').split(',')]
    name = config.get(section, 'name')
    nickname = config.get(section, 'nickname')
    altnickname = nickname + "_"

    if config.has_option(section, 'password'):
        password = config.get(section, 'password')
    else:
        password = None

    if port == 9999:
        ssl = True
    else:
        ssl = False

    server = IRCServer(name, hostname, port, ssl, nickname,
                       altnickname, channels=channels)

    return server

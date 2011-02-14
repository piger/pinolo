#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration handling
"""

import sys
import os
import logging
# from pprint import pprint
from ConfigParser import SafeConfigParser, NoOptionError

from twisted.python import log
from twisted.internet import reactor, ssl

from yapsy.PluginManager import PluginManager
from yapsy.IPlugin import IPlugin

from irc2 import IRCServer, PinoloFactory


class BasePlugin(IPlugin): pass
class CommandPlugin(IPlugin): pass

class PluginActivationError(Exception): pass


def run_foreground(servers):
    """Run pinolo in foreground.
    """

    # To use both logging and twisted.log we should use this formula:
    # http://twistedmatrix.com/documents/current/core/howto/logging.html
    #log.startLogging(sys.stdout)
    observer = log.PythonLoggingObserver()
    observer.start()
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%a, %d %b %Y %H:%M:%S")

    pm = init_plugins()

    f = PinoloFactory(pm, *servers)

    for server in f.servers:
        if server.ssl:
            # ispirato da:
            # http://books.google.it/books?id=Fm5kw3lZ7zEC&pg=PA112&lpg=PA112&dq=ClientContextFactory&source=bl&ots=mlx8EdNiTS&sig=WfqDy9SztfB9xx1JQnxicdouhW0&hl=en&ei=OjF8S7_XBsyh_AayiuH5BQ&sa=X&oi=book_result&ct=result&resnum=7&ved=0CB4Q6AEwBg#v=onepage&q=ClientContextFactory&f=false
            # uso un ClientContextFactory() per ogni connessione.
            conn = reactor.connectSSL(server.address, server.port, f, ssl.ClientContextFactory())
        else:
            conn = reactor.connectTCP(server.address, server.port, f)

        server.connector = conn

    reactor.run()

def init_plugins(plugin_dir='plugins'):
    """Initialize Yapsy plugin system."""

    pm = PluginManager(categories_filter={"Default": BasePlugin,
                                          "Commands": CommandPlugin,
                                         })
    pm.setPluginPlaces([plugin_dir])
    pm.collectPlugins()

    for category in pm.getCategories():
        for plugin in pm.getPluginsOfCategory(category):
            try:
                pm.activatePluginByName(plugin.name, category)
                log.msg("Activating plugin %s" % plugin.name)
            except PluginActivationError, e:
                log.msg("Deactivating faulty plugin: %s (%r)" % (plugin.name, e))
                pm.deactivatePluginByName(plugin.name, category)

    return pm

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

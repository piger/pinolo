#!/usr/bin/env python

"""Pinolo"""

import sys

# verify python version is high enough
if sys.version_info[0] * 10 + sys.version_info[1] < 25:
    error = RuntimeError('pinolo requires python 2.5 or higher')
    if __name__ == '__main__':
        print >> sys.stderr, error
        sys.exit(1)
    else:
        raise error

import os
from twisted.python import log
from twisted.internet import ssl

from irc import *
import db
#import mh_python

__version__ = '0.2.1a'
__author__  = 'sand <daniel@spatof.org>'
#__all__            = ['Pinolo']
# http://effbot.org/pyref/__all__.htm

CHARSET     = 'utf-8'
DEFAULT_CONFIG_FILE = 'pinolo.cfg'
QUOTESDB    = 'quotes.db'
BRAINFILE   = 'brain.b'

class ConnManager():
    """Questa classe e' un Connection Manager, si occupa
    di tenere traccia delle varie Factory e quindi delle
    loro connessioni.
    """

    def __init__(self):
        """Inizializza lo "storage" delle Factory"""
        self.figli = []
        self.dbh = db.DbHelper("quotes.db")

    def aggiungi(self, f):
        """Aggiunge una factory alla lista, e imposta l'attributo
        "padre" a se stesso; in questo modo ogni factory puo'
        chiamare il connection manager."""
        self.figli.append(f)
        f.padre = self

    def spegni_tutto(self):
        """Per ogni figlio (Factory) e per ogni sua connessione
        (Protocol) chiama il metodo spegni().
        E' lo shutdown globale chiamato da un protocol."""
        for f in self.figli:
            f.quitting = True
            for c in f.clienti:
                c.quit("HO DISOBBEDITO E QUINDI SCHIATTO!")

    def spegnimi(self, figlio):
        """Questo viene chiamato da una Factory quando tutte le sue
        connessioni sono terminate. Elimina la Factory dalla lista,
        e se questa e' l'ultima, stoppa il reactor."""
        self.figli.remove(figlio)
        if len(self.figli) == 0:
            # salvo il brain megahal
            #mh_python.cleanup()
            reactor.stop()

def parse_options():
    from optparse import OptionParser

    usage = "Usage: %prog [-c config.cfg]"
    description = 'A stupid and blasphemous IRC bot'
    prog = 'pynolo'
    op = OptionParser(usage=usage, description=description,
                      version="%prog " + __version__, prog=prog)
    op.add_option('-c', '--config', action='store', dest='config_file',
                  type='string', help='Custom configuration file.',
                  default=DEFAULT_CONFIG_FILE, metavar='FILE')

    options, args = op.parse_args()
    return options, args

def main():
    from ConfigParser import ConfigParser, NoOptionError
    from re import split

    options, args = parse_options()

    # log.startLogging(sys.stdout)

    config = ConfigParser()
    config.read(options.config_file)

    servers = []

    for section in config.sections():
        if section.startswith("Server"):
            server = {
                    'name':     config.get(section, 'name'),
                    'address':  config.get(section, 'server'),
                    'port':     int(config.get(section, 'port')),
                    'nickname': config.get(section, 'nickname'),
                    'channels': re.split("\s*,\s*", config.get(section, 'channels'))
            }
            try:
                server['password'] = config.get(section, 'password')
            except NoOptionError:
                server['password'] = None

            servers.append(server)

    # Starto MegaHAL
    #mh_python.initbrain()

    c = ConnManager()

    for server in servers:
        f = PinoloFactory(server)
        c.aggiungi(f)

        # SSL
        if server['port'] == 9999:
            # ispirato da:
            # http://books.google.it/books?id=Fm5kw3lZ7zEC&pg=PA112&lpg=PA112&dq=ClientContextFactory&source=bl&ots=mlx8EdNiTS&sig=WfqDy9SztfB9xx1JQnxicdouhW0&hl=en&ei=OjF8S7_XBsyh_AayiuH5BQ&sa=X&oi=book_result&ct=result&resnum=7&ved=0CB4Q6AEwBg#v=onepage&q=ClientContextFactory&f=false
            # uso un ClientContextFactory() per ogni connessione.
            reactor.connectSSL(server['address'],
                               server['port'],
                               f,
                               ssl.ClientContextFactory())
        else:
            reactor.connectTCP(server['address'],
                               server['port'],
                               f)
    reactor.run()

# start
if __name__ == '__main__':
    sys.exit(main())

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
#__all__	    = ['Pinolo']
# http://effbot.org/pyref/__all__.htm

CHARSET	    = 'utf-8'
CONFIG	    = 'pinolo.cfg'
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

def main():
    import ConfigParser
    from re import split

    # start logging
    log.startLogging(sys.stdout)

    defaultConfigFile = 'pinolo.cfg'
    config = ConfigParser.ConfigParser()
    config.read(defaultConfigFile)

    servers = []

    for section in config.sections():
	if section.startswith("Server"):
	    server = {
		    'name':	config.get(section, 'name'),
		    'address':	config.get(section, 'server'),
		    'port':	int(config.get(section, 'port')),
		    'nickname':	config.get(section, 'nickname'),
		    'channels':	re.split("\s*,\s*", config.get(section, 'channels'))
	    }
	    try:
		server['password'] = config.get(section, 'password')
	    except:
		server['password'] = None

	    servers.append(server)

    # Starto MegaHAL
    #mh_python.initbrain()

    c = ConnManager()

    # SSL
    contextFactory = ssl.ClientContextFactory()
    for server in servers:
	f = PinoloFactory(server)
	c.aggiungi(f)
	if server['port'] == 9999:
	    reactor.connectSSL(server['address'], server['port'], f, contextFactory)
	else:
	    reactor.connectTCP(server['address'], server['port'], f)

    reactor.run()

# start
if __name__ == '__main__':
    sys.exit(main())

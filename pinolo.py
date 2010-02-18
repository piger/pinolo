#!/usr/bin/env python

"""Pinolo"""

import sys

# verify python version is high enough
if sys.version_info[0] * 10 + sys.version_info[1] < 25:
    error = RuntimeError(u'pinolo requires python 2.5 or higher')
    if __name__ == '__main__':
        print >> sys.stderr, error
        sys.exit(1)
    else:
        raise error

import os
from twisted.python import log
from irc import *
import db
from markov import Markov

__version__ = u'0.2'
__author__  = u'sand <daniel@spatof.org>'
#__all__	    = [u'Pinolo']
# http://effbot.org/pyref/__all__.htm

CHARSET	    = u'utf-8'
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
	self.brain = Markov(brain_file=BRAINFILE)

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
		c.quit("ME LO HAN DETTO!")

    def spegnimi(self, figlio):
	"""Questo viene chiamato da una Factory quando tutte le sue
	connessioni sono terminate. Elimina la Factory dalla lista,
	e se questa e' l'ultima, stoppa il reactor."""
	self.figli.remove(figlio)
	if len(self.figli) == 0:
	    self.brain.dump_brain()
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
		    'name': config.get(section, 'name'),
		    'address':	config.get(section, 'server'),
		    'port':	int(config.get(section, 'port')),
		    'nickname':	config.get(section, 'nickname'),
		    'channels':	config.get(section, 'channels').split(", ")
	    }
	    servers.append(server)

    c = ConnManager()

    for server in servers:
	f = PinoloFactory(server)
	c.aggiungi(f)
	reactor.connectTCP(server['address'], server['port'], f)

    reactor.run()

# start
if __name__ == u'__main__':
    sys.exit(main())

#!/usr/bin/env python

import sys
import os
from twisted.python import log
from irc import *
import db
from markov import Markov

class ConnManager():
    """Questa classe e' un Connection Manager, si occupa
    di tenere traccia delle varie Factory e quindi delle
    loro connessioni.
    """

    def __init__(self):
	"""Inizializza lo "storage" delle Factory"""
	self.figli = []
	self.dbh = db.DbHelper("quotes.db")
	self.brain = Markov()

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
    #import ConfigParser
    from re import split

    # start logging
    log.startLogging(sys.stdout)

    #defaultConfigFile = "./pinolo.cfg"
    #config = ConfigParser.ConfigParser()
    #config.read(defaultConfigFile)

    #channels = re.split("\s*,\s*", config.get("General", "channels"))

    #bot = Pinolo( channels,
    #        config.get("General", "nickname"),
    #        config.get("General", "server"),
    #        int(config.get("General", "port")),	    # int !
    #        config.get("NickServ", "password") )

    #bot.start()

    # quick conf
    servers = [
	{
	    'name' : "AZZURRA",
	    'address' : 'irc.azzurra.org',
	    'port' : 6667,
	    'nickname': 'p1nol0',
	    'channels' : ['#mortodentro', '#retrocomputing']
	},
	{
	    'name' : "FREAKNET",
	    'address' : 'irc.hinezumilabs.org',
	    'port' : 6667,
	    'nickname': 'p1nol0',
	    'channels' : ['#test123']
	}
    ]

    chain_length = 3

    c = ConnManager()

    # markov
    #if os.path.exists('training.txt'):
    #    f = open('training.txt', 'r')
    #    for line in f:
    #        c.brain.add_to_brain(line, chain_length)
    #    f.close()

    for server in servers:
	f = PinoloFactory(server)
	c.aggiungi(f)
	reactor.connectTCP(server['address'], server['port'], f)

    reactor.run()

# start
if __name__ == "__main__":
    main()

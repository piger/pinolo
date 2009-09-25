#!/usr/bin/env python

from twisted.internet.protocol import Protocol, ClientFactory
from sys import stdout
import re

class Cliente(Protocol):
    def dataReceived(self, data):
	stdout.write(data)
	if re.match("quit", data):
	    self.factory.padre.spegni_tutto()

    def spegni(self):
	print "dovrei stopparmi"
	self.transport.loseConnection()

class ClienteFactory(ClientFactory):
    """ ha .padre !"""

    def __init__(self, conn):
	self.clienti = []
	self.host, self.port = conn

    def buildProtocol(self, addr):
	print "Connected to %s %s" % (addr.host, addr.port)
	c = Cliente()
	c.factory = self
	self.clienti.append(c)
	return c

    def startedConnecting(self, connector):
	print "started to connect"

    def clientConnectionLost(self, connector, reason):
	"""Se e' l'ultima connessione di questa Factory, eliminala
	dal connection manager."""
	if len(self.clienti) == 0:
	    self.padre.spegnimi(self)


from twisted.internet import reactor

class ConnManager():
    """Questa classe e' un Connection Manager, si occupa
    di tenere traccia delle varie Factory e quindi delle
    loro connessioni.
    """

    def __init__(self):
	"""Inizializza lo "storage" delle Factory"""
	self.figli = []

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
	    for c in f.clienti:
		c.spegni()

    def spegnimi(self, figlio):
	"""Questo viene chiamato da una Factory quando tutte le sue
	connessioni sono terminate. Elimina la Factory dalla lista,
	e se questa e' l'ultima, stoppa il reactor."""
	self.figli.remove(figlio)
	if len(self.figli) == 0:
	    reactor.stop()

connections = [
	('localhost', 2022),
	('127.0.0.1', 2023)
	]

c = ConnManager()
for conn in connections:
    f = ClienteFactory(conn)
    c.aggiungi(f)
    host, port = conn
    reactor.connectTCP(host, port, f)

reactor.run()

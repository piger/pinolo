#!/usr/bin/env python

from twisted.internet.protocol import Protocol, ClientFactory
from sys import stdout

class Cliente(Protocol):
    def dataReceived(self, data):
	stdout.write(data)

class ClienteFactory(ClientFactory):
    def buildProtocol(self, addr):
	print "Connected to %s %s" % (addr.host, addr.port)
	return Cliente()

    def startedConnecting(self, connector):
	print "started to connect"


from twisted.internet import reactor

f = ClienteFactory()
# il risultato di questo esperimento e' che il parametro addr.host
# sara' sempre '127.0.0.1':
## Connected to 127.0.0.1 2023
## Connected to 127.0.0.1 2022

reactor.connectTCP('localhost', 2022, f)
reactor.connectTCP('127.0.0.1', 2023, f)
reactor.run()

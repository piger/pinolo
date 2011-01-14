#!/usr/bin/env python
"""
Interfacciamento con il mondo dello IRC.

La classe `IRCServer` gestisce la configurazione dei server IRC a cui Pinolo si
colleghera'.
La classe Pinolo e' il core delle azioni effettuate su IRC.
La classe PinoloFactory invece gestisce la parte di network del protocollo IRC e
tiene traccia delle configurazioni e dei client (connessioni).
"""

import os
import sys
import re
import socket
from pprint import pprint

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log

STATUS_ALIVE = 1
STATUS_QUIT = 2

class IRCServer(object):
    """
    La classe che gestisce la configurazione e lo stato dei server IRC a cui
    Pinolo si collega.

    Parametri di configurazione:
        `name`: il nome assegnato a questo server
        `hostname`: hostname o IPv4 del server
        `port`: la porta (int) a cui collegarsi
        `ssl`: (bool) se utilizzare SSL per collegarsi
        `nickname`: il nickname da utilizzare
        `altnickname`: il nickname da utilizzare se `nickname` e' gia' preso
        `ident`: lo ident o username (appare nel WHOIS come ident@hostname: Real
        Name)
        `realname`: il realname per il WHOIS
        `channels`: una lista di canali a cui collegarsi.

    NOTE:
        - self.address viene determinato runtime con socket.gethostbyname()
        - self.connector e' il connector di questo Protocol ma non lo uso.
        - self.status e' lo stato della connessione, utile per determinare un
        QUIT definitivo.
    """

    def __init__(self, name, hostname, port, ssl, nickname, altnickname,
                 ident='pinolo', realname='pinot di pinolo',
                 channels=None):
        self.name = name
        self.hostname = hostname
        self.address = socket.gethostbyname(self.hostname)
        self.port = int(port)
        self.ssl = ssl
        self.nickname = nickname
        self.altnickname = altnickname
        self.ident = ident
        self.realname = realname
        if channels:
            self.channels = channels[:]
        else:
            self.channels = []
        self.connector = None
        self.status = STATUS_ALIVE


class Pinolo(irc.IRCClient):
    """
    Questa classe gestisce il comportamento globale di Pinolo.

    La configurazione e' accessibile tramite self.config, impostato dalla
    Factory; self.config e' un puntatore alla config della Factory, pertanto e'
    possibile alterarla liberamente.
    """

    # nickname, realname e username vengono gestiti con properties che
    # richiamano self.config
    def _get_nickname(self):
        return self.config.nickname
    nickname = property(_get_nickname)
    def _get_realname(self):
        return self.config.realname
    realname = property(_get_realname)
    def _get_username(self):
        return self.config.ident
    username = property(_get_username)

    def signedOn(self):
        # il server
        peer = self.transport.getPeer()
        # il client
        host = self.transport.getHost()

        info = "%s:%i <--> %s:%i" % (host.host, int(host.port),
                                     peer.host, int(peer.port))
        log.msg("Connection info: " + info)
        self.join('#mortodentro')

    def joined(self, channel):
        print "joined", channel
        self.quit("me ne vado")

    def privmsg(self, user, channel, msg):
        print msg

    def quit(self, message):
        log.msg("Quitting from %s" % self.config.name)
        self.config.status = STATUS_QUIT
        irc.IRCClient.quit(self, message)


class PinoloFactory(protocol.ReconnectingClientFactory):
    """La Factory che gestisce Pinolo.

    Se volessi smettere di riconnettermi ad un singolo server, basta non
    chiamare i metodi di protocol.ReconnectingClientFactory tipo
    clientConnectionLost/Failed.
    Il metodo stopTrying() e' globale, per tutte le connessioni gestite.
    Fare ATTENZIONE a self.connector perche' viene palleggiato.

    Parametri:
        `*servers`: la lista di IRCServer a cui collegarsi.
    """

    protocol = Pinolo

    def __init__(self, *servers):
        self.servers = servers[:]
        self.clients = []


    def buildProtocol(self, addr):
        """La mia versione di BuildProtocol.

        Si comporta come l'originale, ma tiene traccia dei client creati e
        imposta la configurazione del Protocol creato.
        """
        p = self.protocol()
        p.factory = self
        # Trovo la configurazione e la imposto sul Protocol.
        p.config = self.config_from_address(addr.host)
        self.clients.append(p)

        return p


    def quit_all(self, message="Bye bye"):
        """Chiama quit() di tutti i client (Protocol)."""

        for client in self.clients:
            client.quit(message)


    def config_from_address(self, address):
        """Ottiene una configurazione (IRCServer) da un `address`."""

        for server in self.servers:
            if server.address == address:
                return server
        raise RuntimeError("Cannot find config from address: %s" % address)


    def config_from_connector(self, connector):
        """Ottiene una configurazione (IRCServer) da un `connector`."""

        destination = connector.getDestination()
        return self.config_from_address(destination.host)


    def startedConnecting(self, connector):
        config = self.config_from_connector(connector)
        log.msg("Started connecting to: %s" % config.name)
        # Per reconnecting minchia ?
        # "Call me after a successful connection to reset."
        # self.resetDelay()


    def clientConnectionLost(self, connector, reason):
        """Connessione terminata."""

        log.msg("Lost connection: %s" % reason)

        # Se tutti i client sono QUIT, allora posso uscire.
        if self.canIDIEPLZKTHXBYE():
            reactor.stop()

        config = self.config_from_connector(connector)
        if config.status == STATUS_QUIT:
            # NOTA: stopTrying usa self.connector che viene valorizzato dalle
            # originali clientConnectionLost/Failed.
            self.connector = connector
            self.stopTrying()
        else:
            super(PinoloFactory, self).clientConnectionLost(connector, reason)
            #protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


    def clientConnectionFailed(self, connector, reason):
        """Connessione fallita."""

        log.msg("Could not connect: %s" % reason)

        # Se tutti i client sono QUIT, allora posso uscire.
        if self.canIDIEPLZKTHXBYE():
            reactor.stop()

        config = self.config_from_connector(connector)
        if config.status == STATUS_QUIT:
            # NOTA: stopTrying usa self.connector che viene valorizzato dalle
            # originali clientConnectionLost/Failed.
            self.connector = connector
            self.stopTrying()
        else:
            super(PinoloFactory, self).clientConnectionFailed(connector, reason)
            #protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


    def canIDIEPLZKTHXBYE(self):
        """Verifica che tutti i client siano STATUS_QUIT per poter chiamare reactor.stop()."""

        for server in self.servers:
            if server.status != STATUS_QUIT:
                return False
        return True


def main():
    log.startLogging(sys.stdout)

    irc_local = IRCServer('local', 'localhost', 6667, False,
                          'pinolo', 'pinolo_', channels=['#mortodentro'])
    irc_azzurra = IRCServer('azzurra', 'irc.azzurra.org', 9999, True,
                            'pinolo__', 'pyn0l0',
                            channels=['#mortodentro'])

    #irc_servers = [irc_local, irc_azzurra]
    irc_servers = [irc_local]
    f = PinoloFactory(*irc_servers)

    for server in f.servers:

        if server.ssl:
            conn = reactor.connectSSL(server.address, server.port,
                                      f, ssl.ClientContextFactory())
        else:
            conn = reactor.connectTCP(server.address, server.port, f)

        server.connector = conn

    reactor.run()


if __name__ == '__main__':
    import sys
    sys.exit(main())


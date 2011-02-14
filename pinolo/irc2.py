#!/usr/bin/env python
"""
Interfacciamento con il mondo dello IRC.

La classe `IRCServer` gestisce la configurazione dei server IRC a cui Pinolo si
colleghera'.
La classe Pinolo e' il core delle azioni effettuate su IRC.
La classe PinoloFactory invece gestisce la parte di network del protocollo IRC e
tiene traccia delle configurazioni e dei client (connessioni).
"""

# import os
# import sys
import re
import socket
from collections import namedtuple
# from pprint import pprint
# from optparse import OptionParser

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

STATUS_ALIVE = 1
STATUS_QUIT = 2

JOIN_RETRY = 10


IRCUser = namedtuple('IRCUser', 'nickname ident hostname')

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
        self.current_nickname = nickname

class Command(object):
    def __init__(self, client, author, channel, reply_to, command, arguments):
        self.client = client
        self.author = author
        self.channel = channel
        self.reply_to = reply_to
        self.command = command
        self.arguments = arguments

    def reply(self, message):
        self.client.reply(self.reply_to, message)

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

    def _get_current_nickname(self):
        return self.config.current_nickname
    currnickname = property(_get_current_nickname)


    def signedOn(self):
        # il server
        peer = self.transport.getPeer()
        # il client
        host = self.transport.getHost()

        info = "%s:%i <--> %s:%i" % (host.host, int(host.port),
                                     peer.host, int(peer.port))
        log.msg("Connection info: " + info)

        self.join_channels()


    #def joined(self, channel):
    #    print "joined", channel
    #    self.quit("me ne vado")

    def join_channels(self):
        for channel in self.config.channels:
            self.join(channel)

        #reactor.callLater(JOIN_RETRY, self.join_channels)


    def parse_userhost(self, userhost):
        """Parse a userhost mask (user!ident@hostname) and returns a dict"""

        m = re.match(r'(?P<nickname>[^!]+)!(?P<ident>[^@]+)@(?P<hostname>.*)',
                     userhost)

        if m is None:
            log.msg("Invalid userhost: '%s'" % userhost)
            raise RuntimeError("Invalid userhost string: %s" % userhost)

        info = m.groupdict()
        user = IRCUser(info['nickname'], info['ident'], info['hostname'])

        return user


    def privmsg(self, user, channel, msg):
        """Handle public and private privmsg's"""

        log.msg("Message from: user=%s channel=%s msg='%s'" % (user, channel, msg))
        irc_user = self.parse_userhost(user)

        reply_to = irc_user.nickname if channel == self.nickname else channel

        if msg.startswith('!'):
            self.handle_command(irc_user, channel, reply_to, msg[1:])

    def handle_command(self, irc_user, channel, reply_to, msg):
        try:
            command, arguments = msg.split(' ', 1)
        except ValueError:
            command = msg
            arguments = None

        pm = self.factory.plugin_manager

        for plugin in [pm.getPluginByName(p.name, 'Commands') for p in
                       pm.getPluginsOfCategory('Commands')]:

            if plugin.is_activated:
                plugin.plugin_object.handle(self, command, arguments, irc_user, channel, reply_to)


    def reply(self, destination, message):
        self.msg(destination, message.encode('utf-8', 'ignore'))


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

    def __init__(self, plugin_manager, *servers):
        self.plugin_manager = plugin_manager
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
            # XXX non si puo' usare 'super' con questo tipo di classi.
            #super(PinoloFactory, self).clientConnectionLost(connector, reason)
            protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


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
            #super(PinoloFactory, self).clientConnectionFailed(connector, reason)
            protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


    def canIDIEPLZKTHXBYE(self):
        """Verifica che tutti i client siano STATUS_QUIT per poter chiamare reactor.stop()."""

        for server in self.servers:
            if server.status != STATUS_QUIT:
                return False
        return True

#!/usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
import re
import db

class Pinolo(irc.IRCClient):
    """the protocol"""

    def stopConnection(self):
	log.msg("lo muoio in automatico")
	#irc.IRCClient.quit("dice che devo mori'!")
	self.protocol.quit("!")

    def _get_nickname(self):
	return self.factory.nickname

    nickname = property(_get_nickname)
    realname = 'pinot di pinolo'
    username = 'suca'
    sourceURL = 'http://github.com/piger/pinolo'

    versionName = 'pinolo'
    versionNum = '0.1'
    versionEnv = 'gnu\LINUCS'
    # Minimum delay between lines sent to the server. If None, no delay will be
    # imposed. (type: Number of Seconds. )
    # lineRate = 1
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
	self.factory.connection = self
        print "Connected!"
    
    def connectionLost(self, reason):
	irc.IRCClient.connectionLost(self, reason)
	self.factory.connection = None
        print "connection lost!"
    
    def signedOn(self):
        for chan in self.factory.channels:
            self.join(chan)
        print "Signed on as %s." % (self.nickname,)
    
    def joined(self, channel):
        print "Joined %s." % (channel,)
    
    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]
	ircnet = self.factory.config['name']

	log.msg("[%s] <%s> %s" % (ircnet, user, msg))

	if msg.startswith('!'):
	    if msg == '!quit':
		print "quitto"
		self.factory.quitting = True
		self.factory.padre.spegni_tutto()
	    elif msg == '!q':
		id, quote = self.factory.padre.dbh.get_quote()
		self.msg(channel, "%s: %s" % (id, quote))


class PinoloFactory(protocol.ReconnectingClientFactory):
    """the factory
    - ricorda che ha .padre!
    """

    #protocol = Pinolo

    def __init__(self, config):
	self.config = config
	self.clienti = []
        self.channels = self.config['channels'][:]
        self.nickname = self.config['nickname']
	self.quitting = False
	# per ReconnectingClientFactory
	self.resetDelay()

    def buildProtocol(self, addr):
	print "Connected to %s %s" % (addr.host, addr.port)
	c = Pinolo()
	c.factory = self
	self.clienti.append(c)
	return c

    def clientConnectionLost(self, connector, reason):
	print "Lost connection (%s), reconnecting." % (reason,)
	if self.quitting == False:
	    #connector.connect()
	    ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
	else:
	    if len(self.clienti) == 0:
		self.padre.spegnimi(self)

    def clientConnectionFailed(self, connector, reason):
	print "Could not connect: %s" % (reason,)
	ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        #reactor.stop()

if __name__ == "__main__":
    print 'hi!'

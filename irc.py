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
        print "Connected!"
    
    def connectionLost(self, reason):
	irc.IRCClient.connectionLost(self, reason)
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

	log.msg("[%s] <%s> <%s>" % (ircnet, user, msg))

	if msg.startswith('!'):
	    if msg == '!quit':
		print "quitto"
		# come faccio a farlo quittare da tutti i server ?
		self.quit("ADDIO MONDO CLUEDO!")
		reactor.stop()
	    elif msg == '!q':
		id, quote = self.factory.dbh.get_quote()
		self.msg(channel, "%s: %s" % (id, quote))


class PinoloFactory(protocol.ClientFactory):
    """the factory"""

    protocol = Pinolo

    def __init__(self, config):
	self.config = config
        self.channels = self.config['channels'][:]
        self.nickname = self.config['nickname']
	self.dbh = db.DbHelper("quotes.db")
	#reactor.addSystemEventTrigger('before', 'shutdown', self.stopConnection)

    def clientConnectionLost(self, connector, reason):
	print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
	print "Could not connect: %s" % (reason,)
        reactor.stop()

    def stopFactory(self):
	log.msg("STOPPO LA FATTORIA!")

if __name__ == "__main__":
    print 'hi!'

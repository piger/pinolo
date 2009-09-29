#!/usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
import re
import db
import random
import utils

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

	if user == 'pynolo' or re.match("^pynolo[:,]\s+", msg):
	    return

	if msg.startswith('!'):
	    if msg == '!quit':
		print "quitto"
		self.factory.padre.spegni_tutto()
		return

	    elif msg.startswith('!q'):
		quote_id = re.findall("^!q (\d+)", msg)
		if len(quote_id) > 0:
		    log.msg("Dovrei cercare: %s" % (quote_id[0]))
		    (id, quote) = self.factory.padre.dbh.get_quote(quote_id[0])
		else:
		    (id, quote) = self.factory.padre.dbh.get_quote()
		self.msg(channel, "%s: %s" % (id, quote))

	    elif msg.startswith('!addq'):
		if ircnet != 'AZZURRA':
		    self.msg(channel, "%s: qui non posso." % (user))
		    return
		m = re.findall('^!addq (.*)', msg)
		if len(m) > 0:
		    id = self.factory.padre.dbh.add_quote(user, m.pop())
		    self.msg(channel, "%s: aggiunto il quote %s" % (user, id))
		else:
		    self.msg(channel, "%s: ma de che?")

	elif msg.startswith(self.nickname):
	    msg = utils.clean_irc(msg)
	    sentence = self.factory.padre.brain.gen(msg)
	    if sentence:
		sentence = sentence.encode('utf-8')
		log.msg("sentence: %s" % (sentence))
		self.msg(channel, "%s: %s" % (user, sentence))
	    else:
		replies = (
			"pinot di pinolo",
			"sugo di cazzo?",
			"cazzoddio",
			"non ho capito",
			"non voglio capirti",
			"mi stai sul cazzo",
			"odio l'olio",
			"famose na canna",
			"sono nato per deficere",
			"mi sto cagando addosso"
		)
		self.msg(channel, "%s: %s" % (user, random.choice(replies)))
	
	else:
	    if msg.startswith('***') or channel == '#core':
		return
	    msg = utils.clean_irc(msg)
	    msg_words = msg.split()
	    if len(msg_words) > 1:
		log.msg("imparo (da %s): %s" % (channel, msg))
		self.factory.padre.brain.learn(msg_words)


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
	if self.quitting == False:
	    #connector.connect()
	    print "Lost connection (%s), reconnecting." % (reason,)
	    protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
	else:
	    # qui dovrei controllare se ci sono altri "clienti" collegati,
	    # ma per ora evito
	    #if len(self.clienti) == 0:
	    #    self.padre.spegnimi(self)
	    self.padre.spegnimi(self)

    def clientConnectionFailed(self, connector, reason):
	print "Could not connect: %s" % (reason,)
	protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        #reactor.stop()

if __name__ == "__main__":
    print 'hi!'

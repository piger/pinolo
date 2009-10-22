#!/usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
import re
import db
import random
import utils
import mh_python

class Pinolo(irc.IRCClient):
    """the protocol"""

    nickname = property(_get_nickname)
    realname = 'pinot di pinolo'
    username = 'suca'
    sourceURL = 'http://github.com/piger/pinolo'

    versionName = 'pinolo'
    versionNum = '0.1.2'
    versionEnv = 'gnu\LINUCS'
    # Minimum delay between lines sent to the server. If None, no delay will be
    # imposed. (type: Number of Seconds. )
    # lineRate = 1
    # ogni quanti privmsg va salvato il brain ?
    brainSaveLimit = 50

    dumbReplies = (
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


    def stopConnection(self):
	log.msg("lo muoio in automatico")
	#irc.IRCClient.quit("dice che devo mori'!")
	self.protocol.quit("!")


    # XXX non so il perche' di questo magheggio.
    def _get_nickname(self):
	return self.factory.nickname


    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
	self.factory.connection = self
        print "Connected!"
	# inizializzo il counter per salvare il brain
	self.brainCounter = 0
    

    def connectionLost(self, reason):
	irc.IRCClient.connectionLost(self, reason)
	self.factory.connection = None
        print "connection lost!"
    

    def signedOn(self):
        for chan in self.factory.channels:
            self.join(chan)
        print "Signed on as %s." % (self.nickname)
    

    def joined(self, channel):
        print "Joined %s." % (channel)


    # idealmente va chiamata da privmsg(), in modo che ogni
    # Pinolo.brainSaveLimit salvi il brain.
    def brainDamage(self):
	self.brainCounter += 1
	if self.brainCounter > Pinolo.brainSaveLimit:
	    log.msg("Autosaving brain after %i privmsgs" % (self.brainCounter))
	    mh_python.cleanup()
	    self.brainCounter = 0


    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]

	# early maintenance
	self.brainDamage()

	if msg.startswith('!'):
	    self.cmdHandler(user, channel, msg)

	elif msg.startswith(self.nickname):
	    # strippo self.nickname da inizio riga
	    msg = re.sub("^%s" % (self.nickname), '', msg)
	    # ed eventuali [:;,] a eseguire (tipo: "pinolo: ehy")
	    msg = re.sub("^[:;,]\s*", '', msg)

	    msg = utils.clean_irc(msg)
	    sentence = self.fixMegahalReply(mh_python.doreply(msg))
	    log.msg("sentence: %s" % (sentence))
	    self.msg(channel, "%s: %s" % (user, sentence))
	
	else:
	    # impara, ma non i messaggi del server o cio' che appare su #core
	    if msg.startswith('***') or channel == '#core':
		return
	    msg = utils.clean_irc(msg)
	    mh_python.learn(msg)

	    # e in caso PARLA PURE! (15% di possibilita')
	    if random.randint(1, 100) > 85:
		reply = self.fixMegahalReply(mh_python.doreply(msg))
		self.msg(channel, reply)

    def fixMegahalReply(self, reply):
	old_reply = reply
	try:
	    reply = reply.encode('utf-8')
	except:
	    reply = old_reply

	return reply


    def cmdHandler(self, user, channel, msg):
	msg_split = msg.split(" ", 1)
	command = msg_split[0]
	if len(msg_split) > 1:
	    args = msg_split[1]
	else
	    args = None

	if command == '!quit':
	    if user == 'sand':
		log.msg("!quit received!")
		    self.factory.padre.spegni_tutto()

	elif command == '!q' or command == '!quote':
	    (id, quote) = self.factory.padre.dbh.get_quote(args)
	    reply = "%i - %s" % (id, quote)

	elif command == '!salvatutto':
	    mh_python.cleanup()
	    log.msg("Salvo il cervello MegaHAL")

	elif command == '!addq':
	    if self.factory.config['name'] != 'azzurra':
		reply = "%s: qui non posso."
	    else:
		if args == None:
		    reply = "%s: ma de che?"
		else:
		    id = self.factory.padre.dbh.add_quote(user, args)
		    reply = "aggiunto il quote %i!" % (id)

	elif command == '!s':
	    if args == None:
		reply = "Che cosa vorresti cercare?"
	    else:
		res = self.factory.padre.dbh.search_quote(args)
		if len(res) == 0:
		    reply = "Non abbiamo trovato un cazzo! (cit.)"
		else:
		    for r in res:
			self.msg(channel, "%s: %i - %s" % (user, r[0], r[1]))
		    # XXX qui e solo qui uso return...
		    return

	else:
	    reply = random.choice(Pinolo.dumbReplies)

	self.msg(channel, "%s: %s" % (user, reply))
    

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

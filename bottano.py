#!/usr/bin/env python
# sand <daniel@spatof.org> 2009
# PUBLIC DOMAIN

# NOTICE: the code is chaotic, lame and unorganized. It was written just for fun :)
# NOTICE2: many (all?) comments are in italian language.


# WARNING * WARNING * WARNING * WARNING * WARNING * WARNING * WARNING
# THIS SOURCE FILE CONTAINS BLASPHEMOUS LANGUAGE
# WARNING * WARNING * WARNING * WARNING * WARNING * WARNING * WARNING


"""Il nuovo successore di pinolo
"""

import re
from time import sleep, strftime
from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr
from pysqlite2 import dbapi2 as sqlite
from random import randrange

class Pinolo(SingleServerIRCBot):
    public_commands = ("q", "addq")

    def __init__(self, channels, nickname, server, port, ns_pass):
	SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
	self.chans = channels[:]
	self.setup_database()
	self.ns_pass = ns_pass

    def on_welcome(self, c, e):
	self.identify_ns(c)

	for chan in self.chans:
	    c.join(chan)

    def identify_ns(self, c):
	c.privmsg("NickServ", "IDENTIFY %s" % self.ns_pass)

    def on_nicknameinuse(self, c, e):
	c.nick(c.get_nickname() + "_")

# event contiene sia CHI (source) che DOVE (target)
# quindi se TARGET = MYNICK e' query
# fare una funzione "reply" che SA se mettere nick: oppure no?
#    def on_pubmsg(self, conn, event):
#	msg = event.arguments()[0]
#	channel = event.target()
#
#	splitmsg = msg.split(":", 1)
#	if len(splitmsg) > 1 and irc_lower(splitmsg[0]) == irc_lower(self.connection.get_nickname()):
#	    self.do_command(event, splitmsg[1].strip(), channel)
#	elif msg == '!q':
#	    self.say_quote(channel)
#	return

    def on_pubmsg(self, c, e):
	msg = e.arguments()[0].strip()
	myself = self.connection.get_nickname()

	if re.match("%s[:,]\s+" % myself, msg):
	    #msg = msg.split(":", 1)[1]	    # strippa "pynolo:" a inizio msg
	    msg = re.split("[:,]", msg, 1)[1]	# strippa "pynolo:" o "pynolo," a inizio riga
	    self.execute_command(e, msg)
	else:
	    for c in self.public_commands:
		if re.match("^!%s" % c, msg):
		    self.execute_command(e, msg)

    def on_privmsg(self, c, e):
	msg = e.arguments()[0].strip()
	if re.match("^!", msg):
	    self.execute_command(e, msg)

    def tell(self, event, message):
	"""Manda un PRIVMSG distinguendo tra messaggi privati e pubblici.

	L'argomento "event" e' relativo all'evento a cui si sta rispondendo,
	quindi se event.target() corrisponde al nick del bot, si dovra' rispondere
	a un messaggio privato, altrimenti sara' una risposta pubblica e bisognera'
	specificare il nick della persona a cui si sta rispondendo.
	"""
	source = nm_to_n(event.source())
	if irc_lower(event.target()) == irc_lower(self.connection.get_nickname()):
	    # query
	    self.connection.privmsg(source, message)
	else:
	    # public
	    self.connection.privmsg(event.target(), "%s: %s" % (source, message))

    def execute_command(self, event, text):
	conn = self.connection
	pieces = re.findall("\S+", text)
	cmd = pieces.pop(0)
	if pieces:
	    args = ' '.join(pieces)
	else:
	    args = None

	if cmd == "!q":
	    if args:
		try:
		    id = int(args)
		except ValueError:
		    self.tell(event, "L'id non e' numerico, STRONZO")
		    return
		self.say_quote(event, id)
	    else:
		self.say_quote(event)
	# non voglio addq in query
	elif cmd == "!addq" and event.target() != self.connection.get_nickname():
	    if args:
		result = self.add_quote(nm_to_n(event.source()), args)
		if result:
		    self.tell(event, "Ho aggiunto la %i!" % result)
	    else:
		self.tell(event, "mbe'?")
	elif cmd == "!die":
	    if nm_to_n(event.source()) == "sand" and event.target() == self.connection.get_nickname():
		self.die("ATTUO IL DE CESSO GALLICO!")
	elif cmd == "!s":
	    self.search_quote(event, args)
	else:
	    self.tell(event, self.random_reply())

    def setup_database(self):
	self.dbconn = sqlite.connect("quotes.db")
	self.dbconn.text_factory = str	# UTF-8 e cazzi
	self.dbcursor = self.dbconn.cursor()

    def search_quote(self, event, string):
	if string == None:
	    self.tell(event, "NO! !s <stringa da cercare>")
	    return

	pattern = '%' + string.strip() + '%'
	t = (pattern,)
	limit = 5
	i = 0

	self.dbcursor.execute('SELECT quoteid,quote FROM quotes WHERE quote LIKE ? ORDER BY RANDOM()', t)
	results = self.dbcursor.fetchall()
	if len(results) < 1:
	    self.tell(event,  "La tua ricerca non ha dato risultati")
	else:
	    if len(results) > limit:
		self.tell(event, "Calcola ce ne stanno %i, di cui %i sono:" % (len(results), limit))
	    else:
		self.tell(event, "Ho trovato %i risultati" % len(results))

	    less_results = results[:limit]

	    for r in less_results:
		self.tell(event, "%i: %s" % (r[0], r[1]))
		sleep(0.5)

    def say_quote(self, event, id=None):
	c = self.connection

	# I wrap this with try() to avoid problems with invalid id's.
	# example: !q 6666666666666666666666666666666666666666666666666666666666666666666666
	try:
	    if id:
		self.dbcursor.execute("SELECT quote FROM quotes WHERE quoteid = ?", (id,))
	    else:
		self.dbcursor.execute("SELECT quoteid,quote FROM quotes ORDER BY RANDOM() LIMIT 1")
	except OverflowError:
	    self.tell(event, "A stronzo, ma te pare??")
	    return
	
	quote = self.dbcursor.fetchone()
	if quote and id:
	    self.tell(event, quote[0])
	elif quote:
	    self.tell(event, "%i: %s" % (quote[0], quote[1]))
	else:
	    if id:
		self.tell(event, "La quote %i non esiste!" % id)
	    else:
		self.tell(event, "Non ci sono quote nel mio DB :(")

# CREATE TABLE quotes (
#         quoteid INTEGER PRIMARY KEY,
#         quote TEXT NOT NULL,
#         author TEXT,
#         data TEXT NOT NULL
# );
    def add_quote(self, who, text):
	now = strftime("%Y-%m-%d")

	self.dbcursor.execute("INSERT INTO quotes(quote, author, data) VALUES (?, ?, ?)", (text, who, now))
	self.dbconn.commit()
	return self.dbcursor.lastrowid
	#c.privmsg(target, "%s: ho aggiunto la %i!" % (from_nick, self.dbcursor.lastrowid))
	#self.tell(event, "Ho aggiunto la %i!" % self.dbcursor.lastrowid)

    def random_reply(self):
	replies = ( "pinot di pinolo",
		"sugo di cazzo?",
		"cazzoddio",
		"non ho capito",
		"non voglio capirti",
		"mi stai sul cazzo",
		"odio l'olio",
		"famose na canna",
		"sono nato per deficere",
		"mi sto cagando addosso" )
	return replies[randrange(len(replies))]


def main():
    import ConfigParser
    from re import split

    defaultConfigFile = "./pinolo.cfg"

    config = ConfigParser.ConfigParser()
    config.read(defaultConfigFile)

    channels = re.split("\s*,\s*", config.get("General", "channels"))

    bot = Pinolo( channels,
	    config.get("General", "nickname"),
	    config.get("General", "server"),
	    int(config.get("General", "port")),	    # int !
	    config.get("NickServ", "password") )

    bot.start()

if __name__ == "__main__":
    main()

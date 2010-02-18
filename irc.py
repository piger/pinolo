#!/usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
import re
import db
import random
import utils
#import mh_python
from time import sleep
import string

from pprint import pprint

VALID_CMD_CHARS = string.ascii_letters + string.digits + '_'

class Pinolo(irc.IRCClient):
    """the protocol"""

    def _get_nickname(self):
        return self._get_config()['nickname']

    def _get_password(self):
        return self._get_config()['password']

    def _get_config(self):
        return self.factory.config_from_name(self.name)

    nickname = property(_get_nickname)
    password = property(_get_password)
    realname = 'pinot di pinolo'
    username = 'suca'
    sourceURL = 'http://github.com/piger/pinolo'

    versionName = 'pinolo'
    versionNum = '0.2.1a'
    versionEnv = 'gnu\LINUCS'

    # Minimum delay between lines sent to the server. If None, no delay will be
    # imposed. (type: Number of Seconds. )
    lineRate = 1

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

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)

        self.factory.clients.append(self)

        # per ReconnectingClientFactory
        self.factory.resetDelay()

        config = self._get_config()
        log.msg("Connected to %s:%i (Protocol)" % (config['address'],
                                                   config['port']))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        config = self._get_config()
        log.msg("Connection lost from %s:%i (Protocol)" % (config['address'],
                                                   config['port']))
        self.factory.clients.remove(self)

    def clean_quit(self, reason=None):
        if reason is None:
            reason = "ATTUO IL DE CESSO DE BOCCA"

        # dice a ReconnectingClientFactory di non riconnettersi
        self.factory.stopTrying()
        self.quit(reason)
        #self.transport.loseConnection()

    def signedOn(self):
        # IL MALEDETTO NICKSERV
        ns_pass = self._get_config()['password']
        if ns_pass is not None:
            identify_txt = "IDENTIFY " + ns_pass

            if self._get_config()['name'] == 'azzurra':
                self.msg('NickServ', identify_txt)
                # sleep(2)

        log.msg("Signed on as %s." % (self.nickname))
        #self.join_chans()
        reactor.callLater(2, self.join_chans)

    def join_chans(self):
        for chan in self._get_config()['channels']:
            self.join(chan)

    def joined(self, channel):
        log.msg("Joined %s." % (channel))

    def kickedFrom(self, channel, kicker, message):
        self.join(channel)
        self.reply_to(kicker, channel,
                      "6 kattiv0!!1")

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]

        if msg.startswith('!'):
            self.one_cmd(user, channel, msg)

        elif msg.startswith(self.nickname):
            # strippo self.nickname da inizio riga
            msg = msg.replace(self.nickname, '', 1)
            # ed eventuali [:;,] a eseguire (tipo: "pinolo: ehy")
            msg = re.sub("^[:;,]\s*", '', msg)

            if msg.startswith('!'):
                self.reply_to(user, channel,
                              "i comandi vanno dati direttamente in canale, "\
                              "senza il mio nome davanti, perche' sono emo.")
            else:
                self.reply_to(user, channel,
                              random.choice(Pinolo.dumbReplies))

    def reply_to(self, user, channel, reply):
        if channel == self.nickname:
            # private message
            self.msg(user, reply)
        else:
            # public message
            self.msg(channel, "%s: %s" % (user, reply))

    def parse_line(self, line):
        """Parse a line looking for commands.

        Copiato molto da Cmd().
        """

        line = line.strip()
        if not line:
            return None, None, line

        if not line.startswith('!'):
            # not a command
            return None, None, line
        else:
            line = line[1:]

        i, n = 0, len(line)
        while i < n and line[i] in VALID_CMD_CHARS:
            i = i+1

        cmd, arg = line[:i], line[i:].strip()

        # Diciamo che e' meglio arg None che valorizzato a ""
        if arg == '':
            arg = None

        return cmd, arg, line

    def one_cmd(self, user, channel, line):
        cmd, arg, line = self.parse_line(line)

        # cmd alias
        fn_map = {
            'q': 'quote',
            's': 'search',
        }

        # empty line
        if not line:
            return None

        if cmd is None or cmd == '':
            return None

        # supporto rozzo per gli alias
        if fn_map.has_key(cmd):
            cmd = fn_map[cmd]

        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            self.reply_to(user, channel, "command not found.")
            return None

        return func(user, channel, arg)

    def do_quote(self, user, channel, arg):
        if arg is not None and not re.match('\d+$', arg):
            reply = "aridaje... la sintassi e': !q <id numerico>"
        else:
            (q_id, q_txt) = self.factory.dbh.get_quote(arg)
            reply = "%i - %s" % (q_id, q_txt)

        self.reply_to(user, channel, reply)

    def do_addq(self, user, channel, arg):
        if arg is None:
            self.reply_to(user, channel,
                          "ao' ma de che?")

        elif self._get_config()['name'] != 'azzurra':
            self.reply_to(user, channel, "qui non posso :|")

        else:
            q_id = self.factory.dbh.add_quote(user, arg)
            self.reply_to(user, channel,
                          "aggiunto il quote %i!" % q_id)

    def do_search(self, user, channel, arg):
        if arg is None:
            self.reply_to(user, channel,
                          "Che cosa vorresti cercare?")
            return

        res = self.factory.dbh.search_quote(arg)
        if len(res) == 0:
            self.reply_to(user, channel,
                          "Non abbiamo trovato un cazzo! (cit.)")
        else:
            for r in res[:5]:
                self.reply_to(user, channel,
                              "%i - %s" % (r[0], r[1]))

    def do_joinall(self, user, channel, arg):
        if user == 'sand':
            for chan in self._get_config()['channels']:
                self.join(chan)

    def do_quit(self, user, channel, arg):
        if user == 'sand':
            self.clean_quit()

    # XXX TEST!
    def get_my_config(self):
        peer = self.transport.getPeer().host
        return self.factory.proto2config(peer)

    def get_name(self):
        if self.name is None or self.name == "":
            return self.transport.getPeer().host
        else:
            return self.name


class PinoloFactory(protocol.ReconnectingClientFactory):
    """the factory
    - ricorda che ha .padre!
    """

    #protocol = Pinolo

    def __init__(self, config):
        self.config = config
        self.clients = []
        self.dbh = db.DbHelper("quotes.db")

    def get_config(self, address, port):
        for a, p in self.config.keys():
            if address == a and port == p:
                return self.config[(a, p)]
        return None

    def config_from_name(self, name):
        for a, p in self.config.keys():
            cfg = self.config[(a, p)]
            if cfg['name'] == name:
                return cfg
        return None

    def buildProtocol(self, addr):
        log.msg("Connected to %s %s" % (addr.host, addr.port))
        config = self.get_config(addr.host, addr.port)
        c = Pinolo()
        c.factory = self
        c.name = config['name']
        return c

    def clientConnectionLost(self, connector, reason):
        log.msg("Lost connection: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector,
                                                                reason)
        if len(self.clients) == 0:
            reactor.stop()

    # Una connessione fallita va sempre segnalata e ritentata.
    def clientConnectionFailed(self, connector, reason):
        log.msg("Could not connect: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def stopFactory(self):
        log.msg("bye bye!")

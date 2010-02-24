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
from prcd import prcd

VALID_CMD_CHARS = string.ascii_letters + string.digits + '_'


class Pinolo(irc.IRCClient):
    """the protocol"""

    def _get_nickname(self):
        return self._get_config()['nickname']

    def _get_password(self):
        return self._get_config()['password']

    def _get_config(self):
        #return self.factory.config_from_name(self.name)
        name = self.transport.connector.name
        return self.factory.config_from_name(name)

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

    joined_channels = []

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
        """Called when a connection is made.

        This may be considered the initializer of the protocol, because it is
        called when the connection is completed. For clients, this is called
        once the connection to the server has been established; for servers,
        this is called after an accept() call stops blocking and a socket has
        been received. If you need to send any greeting or initial message, do
        it here. 
        """

        irc.IRCClient.connectionMade(self)
        # self.factory.clients.append(self)

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

        reactor.callLater(10, self.check_channels)

    def check_channels(self):
        channels = self._get_config()['channels']
        for channel in channels:
            if channel not in self.joined_channels:
                self.join(channel)
        reactor.callLater(10, self.check_channels)

    def joined(self, channel):
        log.msg("Joined %s." % (channel))
        self.joined_channels.append(channel)

    def kickedFrom(self, channel, kicker, message):
        self.joined_channels.remove(channel)

        self.join(channel)
        self.reply_to(kicker, channel,
                      "6 kattiv0!!1")

    def privmsg(self, user, channel, msg):
        user = user.split('!', 1)[0]

        # qui potrei "impacchettare":
        request = dict(user=user, channel=channel, msg=msg)

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
        # XXX cristo-u-ti-f8
        reply = reply.encode('utf-8')

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

    def do_dimmi(self, user, channel, arg):
        self.reply_to(user, channel,
                      "Io sono %s" % self.transport.connector.name)

    def do_quote(self, user, channel, arg):
        if arg is not None and not re.match('\d+$', arg):
            reply = "aridaje... la sintassi e': !q <id numerico>"
        else:
            q = self.factory.dbh.get_quote(arg)
            if q is None and arg is not None:
                self.reply_to(user, channel,
                              "quote %i non trovata" % int(arg))
            elif q is None:
                self.reply_to(user, channel,
                              "ho tipo il db vuoto!?")
            else:
                self.reply_to(user, channel,
                              "%i - %s" % (q.id, q.quote))

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

        # Per SQL LIKE = '%pattern%'
        arg = '%' + arg + '%'

        t, q = self.factory.dbh.search_quote(arg)
        if t == 0:
            self.reply_to(user, channel,
                          "Non abbiamo trovato un cazzo! (cit.)")
            return

        len_q = len(q)
        if len_q > 5:
            self.reply_to(user, channel,
                          "Search found %i results (%i displayed):" % (t, len_q))
        else:
            self.reply_to(user, channel,
                          "Search found %i results:" % t)

        for ss in q:
            self.reply_to(user, channel,
                          "%i - %s" % (ss.id, ss.quote))

    def do_prcd(self, user, channel, arg):
        if arg is not None:
            if arg not in prcd.categorie():
                self.reply_to(user, channel,
                              "categoria non trovata, PER GIOVE!")
                return

        cat, moccolo = prcd.a_caso(arg)
        self.reply_to(user, channel,
                      "%s [%s]" % (moccolo, cat))

    def do_joinall(self, user, channel, arg):
        if user == 'sand':
            for chan in self._get_config()['channels']:
                self.join(chan)

    def do_quit(self, user, channel, arg):
        if user == 'sand':
            if arg == 'all':
                for client in self.factory.clients:
                    client.clean_quit()
            else:
                self.clean_quit()

    # XXX TEST!
    def id_conn(self):
        """Ritorna una tuple(remote.addr, remote.port, local.addr, local.port)"""

        peer = self.transport.getPeer()
        host = self.transport.getHost()
        return (peer.host, peer.port, host.host, host.port)


class PinoloFactory(protocol.ReconnectingClientFactory):
    #protocol = Pinolo

    def __init__(self, config):
        self.config = config
        self.clients = []
        #self.dbh = db.DbHelper("quotes.db")
        self.dbh = db.SqlFairy('quotes.db')

    def config_from_name(self, name):
        for a, p in self.config.keys():
            cfg = self.config[(a, p)]
            if cfg['name'] == name:
                return cfg
        return None

    def buildProtocol(self, addr):
        log.msg("Connected to %s %s" % (addr.host, addr.port))
        #config = self.get_config(addr.host, addr.port)
        c = Pinolo()
        c.factory = self

        self.clients.append(c)

        # per ReconnectingClientFactory
        # http://twistedmatrix.com/documents/current/core/howto/clients.html
        self.resetDelay()

        #c.name = config['name']
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

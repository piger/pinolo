#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""

Ispirato da:
https://gist.github.com/676306

"""

import sys, os, re
import time
import logging
import imp

import gevent
from gevent.core import timer
from gevent import socket, ssl
from gevent.core import timer

import pinolo.plugins
from pinolo import FULL_VERSION, EOF_RECONNECT_TIME, FAILED_CONNECTION_RECONNECT_TIME
from pinolo import CONNECTION_TIMEOUT, PING_DELAY
from pinolo.database import init_db
from pinolo.prcd import moccolo_random, prcd_categories
from pinolo.cowsay import cowsay
from pinolo.utils import decode_text
from pinolo.config import database_filename
from pinolo.casuale import get_random_quit, get_random_reply
from pinolo.google import search_google

usermask_re = re.compile(r'(?:([^!]+)!)?(?:([^@]+)@)?(\S+)')

NEWLINE = '\r\n'
CTCPCHR = u'\x01'

COMMAND_ALIASES = {
    's': 'search',
    'g': 'google',
}

class LastEvent(Exception): pass

def parse_usermask(usermask):
    """Ritorna una tupla con (nickname, ident, hostname)

    ... oppure raisa una Exception
    """
    match = usermask_re.match(usermask)
    if match:
        return match.groups()
    else:
        raise RuntimeError(u"Invalid usermask: %s" % usermask)

class IRCUser(object):
    """
    Un utente IRC.
    """
    def __init__(self, ident, hostname, nickname):
        self.ident, self.hostname, self.nickname = ident, hostname, nickname

    def __repr__(self):
        return u"<IRCUser(nickname:%s, %s@%s)>" % (self.nickname, self.ident, self.hostname)

class IRCEvent(object):
    """
    Un evento IRC generico.
    """

    def __init__(self, client, user, command, argstr, args=None, text=None):
        self.client = client
        self.user = user
        self.command = command
        self.argstr = argstr
        if args:
            self.args = args[:]
        else:
            self.args = []
        self.text = text

    @property
    def nickname(self):
        return self.user.nickname

    def reply(self, message, prefix=True):
        """
        Manda un PRIVMSG di risposta all'evento, scrivendo in canale se si tratta
        di un evento pubblico o in query se l'evento e' privato.
        """
        assert type(message) is unicode
        assert type(self.user.nickname is unicode)

        recipient = self.args[0]
        if recipient.startswith('#'):
            if prefix:
                message = u"%s: %s" % (self.user.nickname, message)
            self.client.msg(recipient, message)
        else:
            self.client.msg(self.user.nickname, message)

    def __repr__(self):
        return u"<IRCEvent(%r, command: %s, argstr: %s, " \
               "args: %r, text: %r)>" % (self.user, self.command, self.argstr, self.args,
                                         self.text)


class IRCClient(object):
    """
    Un client IRC (bot) con gevent.
    """

    def __init__(self, name, config, general_config, head):
        self.name = name
        self.config = config
        self.general_config = general_config
        self.head = head

        self.nickname = self.config.nickname
        self.current_nickname = self.nickname

        self.socket = None
        self.stream = None
        self.throttle_out = 0.5
        self._last_write_time = 0
        self.logger = logging.getLogger('pinolo.irc.' + self.name)
        self.running = False

        self.ping_timer = None

    def connect(self):
        while True:
            try:
                self._connect()
            except socket.error, e:
                print u"[*] ERROR: Failed connecting to: %s:%d " \
                      "(%s) - %s" % (self.config.address, self.config.port,
                                     self.name, str(e))
                print u"[*] Sleeping %i seconds before reconnecting" % FAILED_CONNECTION_RECONNECT_TIME
                gevent.sleep(FAILED_CONNECTION_RECONNECT_TIME)
            else:
                break

        gevent.sleep(1)
        self.running = True
        self.login_to_server()
        self.ciclo_pingo()
        self.event_loop()

    def _connect(self):
        """
        Si connette al server IRC, fa partire i loop read/write e si autentica
        al server; infine fa partire l'event loop.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.config.ssl:
            self.socket = ssl.wrap_socket(self.socket)
        self.stream = self.socket.makefile()
        self.socket.connect((self.config.address, self.config.port))
        print u"[*] Connected to: %s:%d (%s)" % (self.config.address, self.config.port,
                                                self.name)

    def login_to_server(self):
        """
        Effettua il "login" nel server IRC, inviando la `password` se necessario.
        NOTA: rendere le "flag utente" configurabili? (+invisibile, etc)
        """
        if self.config.password:
            self.send_cmd(u"PASS %s" % self.config.password)
        self.set_nickname(self.current_nickname)
        self.send_cmd(u"USER %s 8 * :%s\n" % (self.general_config.ident,
                                              self.general_config.realname))

    def set_nickname(self, nickname):
        self.current_nickname = nickname
        self.send_cmd(u"NICK %s" % nickname)

    def event_loop(self):
        """
        Gestisce gli eventi da IRC.

        In questo caso ogni `riga` da IRC e' un evento, va percio' parsata e costruito
        un oggetto `Evento` da passare agli handler.

        For all of the rest of these messages, there is a source on
        the other messages from the server side. This is a user and
        hostmask for a user's message, and a server name otherwise. If
        you are writing a client, do not send the :source part.
        """
        while True:
            line = None
            with gevent.Timeout(CONNECTION_TIMEOUT, False):
                line = self.stream.readline()
            if line is None:
                print "timeout"
                self.logger.warning("Connection timeout: "
                                    "%d elapsed" % CONNECTION_TIMEOUT)
                break

            if line == '': break # EOF
            line = decode_text(line.strip())
            self.logger.debug(u"IN: %r" % line)

            if line.startswith(u':'):
                source, line = line[1:].split(u' ', 1)
            else:
                self.logger.debug("strana riga dal server IRC: %r" % line)
                source = None

            if source:
                nickname, ident, hostname = parse_usermask(source)
            else:
                nickname, ident, hostname = (None, None, None)

            command, line = line.split(u' ', 1)
            if u' :' in line:
                argstr, text = line.split(u' :', 1)

                # E' un "comando" del Bot
                if text.startswith(u'!'):
                    try:
                        command, text = text[1:].split(u' ', 1)
                    except ValueError:
                        command, text = text[1:], u''

                    # Espande il comando con gli alias
                    command = u"cmd_" + COMMAND_ALIASES.get(command, command)
            else:
                argstr, text = line, u''
            args = argstr.split()
            user = IRCUser(ident, hostname, nickname)
            event = IRCEvent(self, user, command, argstr, args, text)

            event_name = u'on_%s' % command
            self.dispatch_event(event_name, event)

        # qui siamo a EOF!
        if self.running:
            self.running = False
            self.logger.warning(u"EOF from server? Sleeping %i seconds before "
                                "reconnecting" % EOF_RECONNECT_TIME)
            gevent.sleep(EOF_RECONNECT_TIME)
            self.logger.info(u"Reconnecting to %s:%d (%s)" % (self.config.address,
                                                              self.config.port,
                                                              self.name))
            self.connect()

    def dispatch_event(self, event_name, event):
        for inst in [self] + self.head.plugins:
            if hasattr(inst, event_name):
                f = getattr(inst, event_name)
                try:
                    f(event)
                except LastEvent:
                    break

    def send_cmd(self, cmd):
        """
        Invia una riga al server IRC apponendo il giusto newline.
        """
        if isinstance(cmd, unicode):
            cmd = cmd.encode('utf-8')
        self.stream.write(cmd + NEWLINE)
        self.stream.flush()

    def msg(self, target, message):
        """
        Our `PRIVMSG`.
        """
        now = time.time()
        elapsed = now - self._last_write_time
        if elapsed < self.throttle_out:
            gevent.sleep(0.5 - elapsed)

        self.logger.debug(u"PRVIMSG %s :%s" % (target, message))
        self.send_cmd(u"PRIVMSG %s :%s" % (target, message))
        self._last_write_time = now


    def join(self, channel):
        self.logger.info(u"Joining %s" % channel)
        self.send_cmd(u"JOIN %s" % channel)
        self.me(channel, "saluta tutti")

    def quit(self, message="Bye"):
        self.logger.info(u"QUIT requested")
        self.running = False
        self.send_cmd(u"QUIT :%s" % message)
        # self.stream.close()
        self.socket.close()

    def notice(self, target, message):
        """
        NOTICE
        """
        self.logger.debug(u"NOTICE %s :%s" % (target, message))
        self.send_cmd(u"NOTICE %s :%s" % (target, message))

    def me(self, target, message):
        self.msg(target, u"%sACTION %s%s" % (CTCPCHR, message, CTCPCHR))

    def ctcp(self, target, message):
        """
        Invia un CTCP.
        """
        self.logger.debug(u"SENT CTCP TO %s :%s" % (target, message))
        self.msg(target, CTCPCHR + message + CTCPCHR)

    def ctcp_reply(self, target, message):
        """
        Risponde a un CTCP.
        """
        self.logger.debug("CTCP REPLY TO %s: %s" % (target, message))
        self.notice(target, u''.join([CTCPCHR, message, CTCPCHR]))

    def ctcp_ping(self, target):
        """
        Manda un CTCP PING a `target`.
        """
        tempo = int(time.time())
        self.ctcp(target, "PING " + str(tempo))

    def ping_reply(self, target, message):
        """
        Risponde a un CTCP PING.
        """
        self.ctcp_reply(target, u"PING %s" % message)

    def nickserv_login(self):
        """
        Autentica il nickname con NickServ.
        """
        self.logger.info(u"Authenticating with NickServ")
        self.msg(u'NickServ', u"IDENTIFY %s" % self.config.nickserv)
        gevent.sleep(1)

    def ciclo_pingo(self):
        """
        Setta il timer per pingare noi stessi.
        """
        self.ping_timer = timer(PING_DELAY, self.pingati)

    def pingati(self):
        """
        Pinga se stesso e setta di nuovo il timer.
        """
        self.logger.debug("PING to myself")
        self.ctcp_ping(self.current_nickname)
        self.ciclo_pingo()


    # EVENTS ################################################################################

    def on_001(self, event):
        """
        L'evento "welcome" del server IRC.
        NOTA: Non e' un `welcome` ufficiale, ma funziona.
        """
        if self.config.nickserv:
            self.nickserv_login()

        for channel in self.config.channels:
            self.join(channel)

    def on_433(self, event):
        """
        Nickname is already in use.
        """

        new_nick = self.current_nickname + '_'
        self.set_nickname(new_nick)

    def on_PING(self, event):
        self.logger.debug("PING from server")
        self.send_cmd(u"PONG %s" % event.argstr)

    def on_PRIVMSG(self, event):
        target = event.args[0]
        private = target == self.current_nickname

        # CTCP
        if (private and event.text.startswith(CTCPCHR)):
            event.text = event.text.strip(CTCPCHR)

            # PING request
            if event.text.startswith(u"PING"):
                ping = event.text.split(u' ', 1)[1]
                self.logger.info(u"CTCP PING from %s (%s)" % (event.user.nickname, ping))
                self.ping_reply(event.user.nickname, ping)
            elif event.text.startswith(u"VERSION"):
                self.ctcp_reply(event.user.nickname, "VERSION %s" % FULL_VERSION)
            else:
                self.logger.info(u"CTCP ? from %s: %s" % (event.user.nickname,
                                                          event.text))

        elif event.text.startswith(self.current_nickname) or private:
            event.reply(get_random_reply())

    def on_NOTICE(self, event):
        """
        Per lo piu' sono CTCP reply.
        """
        target = event.args[0]
        private = target == self.current_nickname

        # CTCP reply
        if (private and event.text.startswith(CTCPCHR)):
            event.text = event.text.strip(CTCPCHR)

            # PING reply
            if event.text.startswith(u"PING"):
                tempo = event.text.split(' ', 1)[-1]
                delay = time.time() - int(tempo)
                self.logger.debug("ping reply from %s: %d seconds" % (event.nickname,
                                                                      delay))

    def on_KICK(self, event):
        channel = event.args[0]
        self.logger.info(u"KICKed from %s by %s (%s)" % (channel, event.nickname, event.text))
        gevent.sleep(1)
        self.join(channel)

    def on_ERROR(self, event):
        # skip if it's our /quit command
        if '(Quit:' in event.argstr: return
        self.logger.warning("ERROR from server: %s" % event.argstr)

    def on_cmd_quit(self, event):
        if event.user.nickname == u'sand':
            reason = get_random_quit() if event.text == '' else event.text
            self.logger.warning(u"Global quit from %s (%s)" % (event.user.nickname, reason))
            for client in self.head.connections.values():
                client.quit(reason)

    def on_cmd_prcd(self, event):
        cat, moccolo = moccolo_random(event.text or None)
        if not moccolo:
            event.reply(u"La categoria non esiste!")
        else:
            event.reply(u"(%s) %s" % (cat, moccolo))

    def on_cmd_prcd_list(self, event):
        event.reply(u', '.join(prcd_categories))

    def on_cmd_PRCD(self, event):
        cat, moccolo = moccolo_random(event.text or None)
        if not moccolo:
            event.reply(u"La categoria non esiste!")
        else:
            text = cowsay(moccolo)
            for line in text:
                if line:
                    event.reply(line, prefix=False)

    def on_cmd_google(self, event):
        if not event.text: return
        results = search_google(event.text)
        if not results:
            event.reply(u"Non so niente, non ho visto niente.")
        else:
            for title, url, content in results:
                event.reply(u"\"%s\" %s - %s" % (title, url, content))

    def on_cmd_pingami(self, event):
        self.ctcp_ping(event.user.nickname)


class BigHead(object):
    """
    Questo oggetto e' il cervellone che gestisce i plugin e tutte le connessioni.
    """

    def __init__(self, config):
        self.config = config		# la config globale
        self.connections = {}
        self.plugins = []
        self.logger = logging.getLogger('pinolo.head')

        for root, dirs, files in os.walk("plugins"):
            for filename in files:
                if (filename.startswith('_') or not filename.endswith('.py')): continue
                name = filename.split('.')[0]
                self.logger.info(u"Plugin import: %s" % name)
                plugin = imp.load_source(name, os.path.join(root, filename))

        for plugin_name, plugin_cls in pinolo.plugins.registry:
            self.plugins.append(plugin_cls(self))
            COMMAND_ALIASES.update(plugin_cls.COMMAND_ALIASES.items())

        # init db
        db_uri = database_filename(self.config.datadir)
        init_db(db_uri)

        # activate plugins
        for plugin in self.plugins:
            plugin.activate()

    def run(self):
        print u"[*] Starting %s" % FULL_VERSION
        jobs = []

        for name, server in self.config.servers.iteritems():
            irc = IRCClient(name, server, self.config, self)
            self.connections[name] = irc
            jobs.append(gevent.spawn(irc.connect))

        try:
            gevent.joinall(jobs)
        except KeyboardInterrupt:
            for connection in self.connections.values():
                connection.quit(u"keyboard-interrupt")
            gevent.joinall(jobs)

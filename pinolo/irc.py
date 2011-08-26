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

import pinolo.plugins
from pinolo import FULL_VERSION, EOF_RECONNECT_TIME, FAILED_CONNECTION_RECONNECT_TIME
from pinolo.database import init_db
from pinolo.prcd import moccolo_random, prcd_categories
from pinolo.cowsay import cowsay
from pinolo.utils import decode_text
from pinolo.config import database_filename
from pinolo.casuale import get_random_quit, get_random_reply
# from pinolo.google import search_google

usermask_re = re.compile(r'(?:([^!]+)!)?(?:([^@]+)@)?(\S+)')

NEWLINE = '\r\n'
CTCPCHR = '\x01'

COMMAND_ALIASES = {
    's': 'search',
}

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

        gevent.sleep(1)
        self.running = True
        self.login_to_server()
        self.event_loop()

    def login_to_server(self):
        """
        Effettua il "login" nel server IRC, inviando la `password` se necessario.
        NOTA: rendere le "flag utente" configurabili? (+invisibile, etc)
        """
        if self.config.password:
            self.send_cmd(u"PASS %s" % self.config.password)
        self.send_cmd(u"NICK %s" % self.nickname)
        self.send_cmd(u"USER %s 8 * :%s\n" % (self.general_config.ident,
                                              self.general_config.realname))

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
        for line in self.stream:
            line = line.strip()
            line = decode_text(line)

            self.logger.debug(u"IN: %s" % line)

            if line.startswith(u':'):
                source, line = line[1:].split(u' ', 1)
            else:
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
                    if command in COMMAND_ALIASES:
                        command = COMMAND_ALIASES[command]

                    command = u"cmd_%s" % command
            else:
                argstr, text = line, u''
            args = argstr.split()

            # text = text.decode('utf-8')
            user = IRCUser(ident, hostname, nickname)
            event = IRCEvent(self, user, command, argstr, args, text)

            event_name = u'on_%s' % command
            for inst in [self] + self.head.plugins:
                if hasattr(inst, event_name):
                    f = getattr(inst, event_name)
                    f(event)

        # qui siamo a EOF!

        if self.running:
            self.logger.warning(u"EOF from server? Sleeping %i seconds before "
                                "reconnecting" % EOF_RECONNECT_TIME)
            gevent.sleep(EOF_RECONNECT_TIME)
            self.logger.info(u"Reconnecting to %s:%d (%s)" % (self.config.address,
                                                              self.config.port,
                                                              self.name))
            self.connect()

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

    def quit(self, message="Bye"):
        self.logger.info(u"QUIT requested")
        self.running = False
        self.send_cmd(u"QUIT :%s" % message)
        # self.stream.close()
        self.socket.close()

    def notice(self, target, message):
        self.logger.debug(u"NOTICE %s :%s" % (target, message))
        self.send_cmd(u"NOTICE %s :%s" % (target, message))

    def ctcp(self, target, message):
        self.logger.debug(u"SENT CTCP TO %s :%s" % (target, message))
        # XXX unicode?
        self.notice(target, CTCPCHR + message + CTCPCHR)

    def ctcp_ping(self, target, message):
        self.logger.info(u"CTCP PING reply to %s" % target)
        self.ctcp(target, u"PING " + message)

    def nickserv_login(self):
        """
        Autentica il nickname con NickServ.
        """
        self.logger.info(u"Authenticating with NickServ")
        self.msg(u'NickServ', u"IDENTIFY %s" % self.config.nickserv)
        gevent.sleep(1)

    # EVENTS

    def on_001(self, event):
        """
        L'evento "welcome" del server IRC.
        NOTA: Non e' un `welcome` ufficiale, ma funziona.
        """
        if self.config.nickserv:
            self.nickserv_login()

        for channel in self.config.channels:
            self.join(channel)

    def on_PING(self, event):
        self.logger.debug("PING from server")
        self.send_cmd(u"PONG %s" % event.argstr)

    def on_PRIVMSG(self, event):
        target = event.args[0]
        if target == self.current_nickname:
            private = True
        else:
            private = False

        if event.text.startswith(self.current_nickname) or private:
            event.reply(get_random_reply())
            return

        # CTCP
        if (target == self.current_nickname and event.text.startswith(CTCPCHR)):
            event.text = event.text.strip(CTCPCHR)

            if event.text.startswith(u"PING"):
                ping = event.text.split(u' ', 1)[1]
                self.logger.info(u"CTCP PING from %s (%s)" % (event.user.nickname, ping))
                self.ctcp_ping(event.nickname, ping)
            else:
                self.logger.info(u"CTCP ? from %s: %s" % (event.user.nickname,
                                                          event.text))

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
            if event.text == '':
                reason = get_random_quit()
            else:
                reason = event.text

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
            output = cowsay(moccolo)
            for line in output:
                if line:
                    event.reply(line, prefix=False)

    # def on_cmd_google(self, event):
    #     if not event.text: return
    #     results = search_google(event.text)
    #     if not results:
    #         event.reply(u"Non so niente, non ho visto niente.")
    #     else:
    #         for title, url, content in results:
    #             event.reply(u"\"%s\" %s - %s" % (title, url, content))


class BigHead(object):
    """
    Questo oggetto e' il cervellone che gestisce i plugin e tutte le connessioni.
    """

    def __init__(self, config):
        self.config = config		# la config globale
        self.connections = {}
        self.plugins = []
        self.logger = logging.getLogger('pinolo.head')
        plugins_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   'plugins')

        def my_import(name):
            """
            http://effbot.org/zone/import-string.htm#importing-by-filename
            """
            m = __import__(name)
            for n in name.split(".")[1:]:
                m = getattr(m, n)
            return m

        for root, dirs, files in os.walk(plugins_dir):
            files = [os.path.splitext(x)[0] for x in files if not x.startswith('_')]
            for libname in set(files): # uniqify
                libname = "pinolo.plugins." + libname
                self.logger.info(u"Importing plugin: %s" % (libname,))
                p = my_import(libname)

        for plugin_name, PluginClass in pinolo.plugins.registry:
            # init and append to internal list
            self.plugins.append(PluginClass(self))
            # and update aliases
            COMMAND_ALIASES.update(PluginClass.COMMAND_ALIASES.items())

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

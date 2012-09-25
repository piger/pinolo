# -*- encoding: utf-8 -*-
"""
IRC connections handling with gevent.

Heavily inspired by hmbot and the following gist by gihub:maxcountryman:
https://gist.github.com/676306
"""
import os
import re
import time
import logging
import errno
import gevent
from gevent.core import timer
from gevent import socket, ssl
from gevent.queue import Queue
import pinolo.plugins
from pinolo.database import init_db
from pinolo.prcd import moccolo_random, prcd_categories
from pinolo.cowsay import cowsay
from pinolo.utils.text import decode_text
from pinolo.config import database_filename
from pinolo.casuale import get_random_quit
from pinolo import (FULL_VERSION, EOF_RECONNECT_TIME,
                    FAILED_CONNECTION_RECONNECT_TIME,
                    CONNECTION_TIMEOUT, PING_DELAY, THROTTLE_TIME,
                    THROTTLE_INCREASE)


# re for usermask parsing
# usermask_re = re.compile(r'(?:([^!]+)!)?(?:([^@]+)@)?(\S+)')
# Note: some IRC events could not have a normal usermask, for example:
# PING :server.irc.net
usermask_re = re.compile(r'''
                         # nickname!ident@hostname
                         # optional nickname
                         (?:
                             ([^!]+)!
                         )?
                         # optional ident
                         (?:
                            ([^@]+)@
                         )?

                         # expected hostname
                         (\S+)
                         ''', re.VERBOSE)

# IRC newline
NEWLINE = '\r\n'

# IRC CTCP 'special' character
CTCPCHR = u'\x01'

# Standard command aliases
COMMAND_ALIASES = {
    's': 'search',
}


class LastEvent(Exception):
    pass


def parse_usermask(usermask):
    """Parse a usermask and returns a tuple with (nickname, ident, hostname).

    If the regexp fail to parse the usermask a tuple of None will be returned,
    like (None, None, None).
    """
    match = usermask_re.match(usermask)
    if match:
        return match.groups()
    else:
        return (None, None, None)


class IRCUser(object):
    """This class represent common IRC informations about a user.

    Attributes:

    self.ident
        Ident string for that user.

    self.hostname
        Hostname for that user.

    self.nickname
        Nickname for that user.
    """
    def __init__(self, ident, hostname, nickname):
        self.ident, self.hostname, self.nickname = ident, hostname, nickname

    def __repr__(self):
        return u"<IRCUser(nickname:%s, %s@%s)>" % (
            self.nickname, self.ident, self.hostname)


class IRCEvent(object):
    """Common IRC event class.

    Attributes:

    self.client
        The client instance that received the event.

    self.user
        The IRC user who triggered the event.

    self.command
        The command from the event; this can be an IRC event (e.g: PRIVMSG) or
        an internal command (e.g: !quote).

    self.argstr
        Arguments of `command` as a string; this can be for example the target
        of a PRVIMSG.

    self.args
        A list containing the splitted (by whitespace) words from argstr.

    self.text
        Everything after the first ':' in an IRC line; this can be, for
        example, the content of a PRVIMSG.
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
        """Send a PRIVMSG to a user or a channel as a reply to some query.

        message
            The text message that will be sent; it must be an unicode string
            object!

        prefix
            If `True` `message` will be prefixed with the nickname of the user
            who triggered the event.
        """
        assert type(message) is unicode
        assert type(self.user.nickname is unicode)

        recipient = self.args[0]
        if recipient.startswith(u'#'):
            if prefix:
                message = u"%s: %s" % (self.user.nickname, message)
            self.client.msg(recipient, message)
        else:
            self.client.msg(self.user.nickname, message)

    def __repr__(self):
        return u"<IRCEvent(%r, command: %s, argstr: %s, " \
               "args: %r, text: %r)>" % (self.user, self.command, self.argstr,
                                         self.args, self.text)


class IRCClient(object):
    """An IRC client with gevent.

    Attributes:

    self.name
        Name identifying this connection, usually the IRC network name.

    self.config
        Pointer to this client configuration dict.

    self.general_config
        Pointer to the global bot configuration.

    self.head
        Pointer to the "head" object (the connection manager).
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
        self.throttle_out = THROTTLE_TIME
        self._last_write_time = 0
        self.logger = logging.getLogger("%s.%s" % (__name__, self.name))
        self._running = False
        self._connected = False

        self.ping_timer = None
        self.greenlet = None

    def __repr__(self):
        return "%s(name: %r)" % (
            self.__class__.__name__, self.name
        )

    def connect(self):
        """Connect to the configured IRC server.

        In case of a connection error gevent.sleep() will be called to pause
        the client before attempting a new connection.
        """
        while True:
            try:
                self._connect()
                self._connected = True
            except socket.error, e:
                # Ad esempio:
                # e.errno == errno.ECONNREFUSED
                error_name = errno.errorcode[e.errno]
                error_desc = os.strerror(e.errno)

                self.logger.error(u"Failed connection to: %s:%d (%s %s)" % (
                    self.config.address, self.config.port, error_name,
                    error_desc))
                self.logger.warning(u"I'll be quiet for %d seconds before "
                                    "trying to connect again" %
                                    FAILED_CONNECTION_RECONNECT_TIME)

                self._connected = False
                gevent.sleep(FAILED_CONNECTION_RECONNECT_TIME)
            else:
                break

        gevent.sleep(1)
        self._running = True
        self.login_to_server()
        self.ciclo_pingo()
        self.event_loop()

    def _connect(self):
        """This is the real method for connecting to a IRC server.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.config.ssl:
            self.socket = ssl.wrap_socket(self.socket)
        self.stream = self.socket.makefile()
        self.socket.connect((self.config.address, self.config.port))
        self.logger.info(u"Connected to: %s:%d (%s)" % (
            self.config.address, self.config.port, self.name)
        )

    def login_to_server(self):
        """Login to the IRC server and optionally sends the server password.
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
        """IRC event handling.

        Every line read from a IRC server will be a new event, so a Event
        object will be created with all the details of the event.
        """
        while True:
            line = None
            with gevent.Timeout(CONNECTION_TIMEOUT, False):
                line = self.stream.readline()
            if line is None:
                self.logger.warning(u"Connection timeout: "
                                    "%d elapsed" % CONNECTION_TIMEOUT)
                break
                # continue

            if line == '':
                break       # EOF
            line = decode_text(line.strip())
            self.logger.debug(u"IN: %s" % line)

            if line.startswith(u':'):
                source, line = line[1:].split(u' ', 1)
                nickname, ident, hostname = parse_usermask(source)
            else:
                # PING :server.irc.net
                nickname, ident, hostname = (None, None, None)

            # Parsa il `command` e i suoi `argstr`; in caso di CTCP o !comando
            # cambia `command` adeguatamente.
            command, line = line.split(u' ', 1)
            command = command.encode('utf-8', 'replace')
            if u' :' in line:
                argstr, text = line.split(u' :', 1)

                # CTCP
                if (text.startswith(CTCPCHR) and text.endswith(CTCPCHR)):
                    text = text[1:-1]
                    old_command = command

                    try:
                        command, argstr = text.split(u' ', 1)
                    except ValueError:
                        command, argstr = text, u''
                    text = u''

                    if old_command == "PRIVMSG":
                        command = "CTCP_" + command
                    else:
                        command = "CTCP_REPLY_" + command

                # E' un "comando" del Bot
                elif text.startswith(u'!'):
                    try:
                        command, text = text[1:].split(u' ', 1)
                    except ValueError:
                        command, text = text[1:], u''
                    finally:
                        command = command.encode('utf-8', 'replace')

                    # Espande il comando con gli alias
                    command = "cmd_" + COMMAND_ALIASES.get(command, command)
            else:
                argstr, text = line, u''

            args = argstr.split()
            user = IRCUser(ident, hostname, nickname)
            event = IRCEvent(self, user, command, argstr, args, text)

            event_name = 'on_%s' % command
            self.logger.debug(u"looking for event %s" % (event_name,))
            self.dispatch_event(event_name, event)

        # qui siamo a EOF! ######################
        self._connected = False
        if self._running:
            self._running = False
            self.logger.warning(u"EOF from server? Sleeping %i seconds before "
                                "reconnecting" % EOF_RECONNECT_TIME)
            gevent.sleep(EOF_RECONNECT_TIME)
            self.logger.info(u"Reconnecting to %s:%d (%s)" % (
                self.config.address, self.config.port, self.name))
            self.connect()

    def dispatch_event(self, event_name, event):
        """Dispatch an Event object to the related methods.

        Method lookup will search this class and all plugin classes for a
        method named as in `event_name`.

        event_name
            The event name in the form "on_<event name>", for example:
            on_PRIVMSG.

        event
            The Event object.
        """
        for inst in [self] + self.head.plugins:
            if hasattr(inst, event_name):
                f = getattr(inst, event_name)
                try:
                    f(event)
                except LastEvent:
                    self.logger.debug(u"LastEvent for %s from %r" % (
                        event_name, f))
                    break

    def send_cmd(self, cmd):
        """Queue a IRC command to send to the server.

        cmd
            A formatted IRC command string.

        NOTA: Adesso scrive direttamente sul socket.
        """
        if not self._connected:
            self.logger.error(u"Discarding output (we aren't connected): %r" %
                              (cmd,))
            return
        if isinstance(cmd, unicode):
            cmd = cmd.encode('utf-8', 'replace')
        self.stream.write(cmd + NEWLINE)
        self.stream.flush()

    def msg(self, target, message):
        """
        Our `PRIVMSG` with flood protection.
        """
        now = time.time()
        elapsed = now - self._last_write_time
        if elapsed < self.throttle_out:
            gevent.sleep(0.5 - elapsed)

        self.logger.debug(u"PRVIMSG %s :%s" % (target, message))
        self.send_cmd(u"PRIVMSG %s :%s" % (target, message))
        self._last_write_time = now

    def msg_channels(self, msg, channels=None):
        """Send a PRIVMSG to a list of channels."""
        if channels is None:
            channels = self.config.channels[:]
        for channel in channels:
            self.msg(channel, msg)

    def join(self, channel):
        """Join a channel."""
        self.logger.info(u"Joining %s" % channel)
        self.send_cmd(u"JOIN %s" % channel)
        self.me(channel, u"saluta tutti")

    def quit(self, message="Bye"):
        """Quit this connection and kills the greenlet."""
        self.logger.info(u"QUIT requested")
        if self._running:
            self.send_cmd(u"QUIT :%s" % message)
            self._running = False           # XXX
        self.stop_ciclo_pingo()
        # self.stream.close() # XXX
        self.socket.close()
        self.greenlet.kill()

    def notice(self, target, message):
        """
        NOTICE
        """
        self.logger.debug(u"NOTICE %s :%s" % (target, message))
        self.send_cmd(u"NOTICE %s :%s" % (target, message))

    def me(self, target, message):
        self.msg(target, u"%sACTION %s%s" % (CTCPCHR, message, CTCPCHR))

    def ctcp(self, target, message):
        """Generic CTCP send method."""
        self.logger.debug(u"SENT CTCP TO %s :%s" % (target, message))
        self.msg(target, u"%s%s%s" % (CTCPCHR, message, CTCPCHR))

    def ctcp_reply(self, target, message):
        """Reply to a CTCP."""
        self.logger.debug(u"CTCP REPLY TO %s: %s" % (target, message))
        self.notice(target, u"%s%s%s" % (CTCPCHR, message, CTCPCHR))

    def ctcp_ping(self, target):
        """Send a CTCP PING to a target IRC user."""
        tempo = int(time.time())
        self.ctcp(target, u"PING %d" % (tempo,))

    def ctcp_ping_reply(self, target, message):
        """Reply to a CTCP PING."""
        self.ctcp_reply(target, u"PING %s" % message)

    def nickserv_login(self):
        """Handle authentication with NickServ service."""
        self.logger.info(u"Authenticating with NickServ")
        self.msg(u'NickServ', u"IDENTIFY %s" % self.config.nickserv)
        gevent.sleep(1)

    def ciclo_pingo(self):
        """Set a gevent.timer that will ping ourself from time to time."""
        self.ping_timer = timer(PING_DELAY, self.pingati)

    def stop_ciclo_pingo(self):
        """Stop the gevent.timer created by `ciclo_pingo`."""
        if self.ping_timer is not None:
            self.ping_timer.cancel()

    def pingati(self):
        """Ping myself and set a new self-ping timer."""
        # verifico che siamo connessi; non e' troppo affidabile...
        if self._running:
            self.logger.debug(u"PING to myself")
            self.ctcp_ping(self.current_nickname)
            self.ciclo_pingo()

    def increase_throttle(self):
        """Increase the throttle of PRIVMSG sent to the server."""
        old_value = self.throttle_out
        self.throttle_out += THROTTLE_INCREASE
        self.logger.warning(u"Increasing throttle: %f -> %f" % (
            old_value, self.throttle_out))

    # EVENTS ##################################################################

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
        """
        Server PING.
        """
        self.logger.debug(u"PING from server")
        self.send_cmd(u"PONG %s" % event.argstr)

    def on_PRIVMSG(self, event):
        target = event.args[0]
        private = target == self.current_nickname

        # if event.text.startswith(self.current_nickname) or private:
        #     event.reply(get_random_reply())

    def on_CTCP_PING(self, event):
        if event.user.nickname != self.current_nickname:
            self.logger.info(u"CTCP PING from %s: %s" % (event.user.nickname,
                                                         event.argstr))
        self.ctcp_ping_reply(event.user.nickname, event.argstr)

    def on_CTCP_VERSION(self, event):
        self.logger.info(u"CTCP VERSION from %s" % event.user.nickname)
        self.ctcp_reply(event.user.nickname, u"VERSION %s" % FULL_VERSION)

    def on_NOTICE(self, event):
        pass

    def on_KICK(self, event):
        channel = event.args[0]
        self.logger.info(u"KICKed from %s by %s (%s)" % (
            channel, event.nickname, event.text))
        gevent.sleep(1)
        self.join(channel)

    def on_ERROR(self, event):
        """
        2011-09-05 10:51:14,156 pinolo.irc.azzurra WARNING ERROR from server: :Closing Link: my.hostname.net (Excess Flood)
        """
        # skip if it's our /quit command
        if '(Quit:' in event.argstr:
            return
        match = re.search(r"\(([^)]+)\)", event.argstr)
        if match:
            reason = match.group(1)
            reason = reason.lower()
        else:
            reason = u""

        if reason == u"excess flood":
            self.logger.warning(u"ERROR: Excess Flood from server!")
            self.increase_throttle()
        self.logger.warning(u"ERROR from server: %s" % event.argstr)

    def on_cmd_quit(self, event):
        if event.user.nickname == u'sand':
            reason = get_random_quit() if event.text == '' else event.text
            self.logger.warning(u"Global quit from %s (%s)" % (
                event.user.nickname, reason))
            self.head.shutdown(reason)

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

    def on_cmd_pingami(self, event):
        self.ctcp_ping(event.user.nickname)


class BigHead(object):
    """
    Questo oggetto e' il cervellone che gestisce i plugin e tutte le
    connessioni.
    """

    def __init__(self, config):
        self.config = config		# la config globale
        self.connections = {}
        self.plugins = []
        self.logger = logging.getLogger('pinolo.head')
        self.plugins_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'plugins')
        self.db_uri = database_filename(self.config.datadir)

        self.load_plugins()
        self.start_plugins()
        # init_db() va DOPO start_plugins() per creare eventuali tabelle del DB
        # in realta' va DOPO l'import. XXX
        init_db(self.db_uri)
        self.activate_plugins()

    def load_plugins(self):
        def my_import(name):
            """
            http://effbot.org/zone/import-string.htm#importing-by-filename
            """
            m = __import__(name)
            for n in name.split(".")[1:]:
                m = getattr(m, n)
            return m

        # NOTA: SKIPPARE I .pyc!!!
        for root, dirs, files in os.walk(self.plugins_dir):
            files = [os.path.splitext(x)[0] for x in files
                     if (not x.startswith('_') and x.endswith('.py'))]
            for libname in set(files):      # uniqify
                libname = "pinolo.plugins." + libname
                self.logger.info(u"Importing plugin: %s" % (libname,))
                p = my_import(libname)

    def start_plugins(self):
        for plugin_name, PluginClass in pinolo.plugins.registry:
            # init and append to internal list
            self.plugins.append(PluginClass(self))
            # and update aliases
            COMMAND_ALIASES.update(PluginClass.COMMAND_ALIASES.items())

    def activate_plugins(self):
        self.logger.debug(u"Activating plugins")
        for plugin in self.plugins:
            plugin.activate()

    def deactivate_plugins(self):
        self.logger.debug(u"Deactivating plugins")
        for plugin in self.plugins:
            plugin.deactivate()

    def shutdown(self, reason=u"quit"):
        self.logger.warning(u"Global shutdown")
        self.deactivate_plugins()
        for client in self.connections.values():
            client.quit(reason)

    def run(self):
        print "[*] Starting %s" % FULL_VERSION
        jobs = []

        for name, server in self.config.servers.iteritems():
            irc = IRCClient(name, server, self.config, self)
            self.connections[name] = irc
            job = gevent.spawn(irc.connect)
            irc.greenlet = job
            jobs.append(job)

        try:
            gevent.joinall(jobs)
        except KeyboardInterrupt:
            self.shutdown(u"keyboard-interrupt")
            gevent.joinall(jobs)

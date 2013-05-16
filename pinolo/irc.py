# -*- coding: utf-8 -*-
"""
    pinolo.irc
    ~~~~~~~~~~

    IRC related functions and classes. It's basically a callback system, with
    events named by the IRC command (e.g. on_PRIVMSG, on_NOTICE, etc).

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import logging
import re
import socket
import errno
import time
import traceback
import ssl
from pinolo.tasks import TestTask
from pinolo.cowsay import cowsay
from pinolo.casuale import get_random_quit, get_random_reply
from pinolo import USER_AGENT


log = logging.getLogger(__name__)

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

r_ircline = re.compile(r"""
    (?:
        :(?P<source>\S+)\s+
        |
    )
    (?P<command>\S+)
    \s+
    (?P<args>[^:$]+)?
    (?:
        $
        |
        \s*:(?P<text>.*)
    )
    """, re.VERBOSE)

# IRC newline
NEWLINE = '\r\n'

# IRC CTCP 'special' character
CTCPCHR = u'\x01'

COMMAND_ALIASES = {}

re_comma = re.compile(r'\s*,\s+')


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
    def __init__(self, nickname, ident=None, hostname=None):
        self.nickname = nickname or ""
        self.ident = ident or ""
        self.hostname = hostname or ""

    def __repr__(self):
        return u"<IRCUser(%s!%s@%s)>" % (self.nickname, self.ident, self.hostname)


class IRCEvent(object):
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

    @property
    def name(self):
        return "on_" + self.command

    def reply(self, message, prefix=True):
        assert isinstance(message, unicode) is True
        assert isinstance(self.nickname, unicode) is True

        recipient = self.args[0]
        if recipient.startswith(u"#"):
            if prefix:
                message = u"{0}: {1}".format(self.nickname, message)
            self.client.msg(recipient, message)
        else:
            self.client.msg(self.nickname, message)

    def __repr__(self):
        return u"<IRCEvent(client=%r, user=%r, command=%r, argstr=%r, args=%r, text=%r)>" % (
            self.client, self.user, self.command, self.argstr,
            self.args, self.text)


class IRCConnection(object):
    def __init__(self, name, config, bot):
        # the connection name
        self.name = name
        # connection configuration
        self.config = config
        # pointer to manager object
        self.bot = bot
        # network stuff
        self.socket = None
        self.out_buffer = ""
        self.in_buffer = ""
        # are we connected, active?
        self.connected = False
        self.active = True
        # nickname handling
        self.nicknames = self.bot.config['nicknames']
        self.nicknames_id = 0
        self.current_nickname = None
        # la queue per i thread
        self.coda = self.bot.coda
        # SSL status
        self.ssl_must_handshake = False
        self.ssl_ca_path = self.config.get("ssl_ca_path")
        # state
        self.channels = {}

    def __repr__(self):
        return "<IRCConnection(%s)>" % self.name

    def wrap_ssl(self):
        old_socket = self.socket

        try:
            if self.config["ssl_verify"]:
                self.socket = ssl.wrap_socket(self.socket,
                                              cert_reqs=ssl.CERT_REQUIRED,
                                              ca_certs=self.ssl_ca_path,
                                              do_handshake_on_connect=False)
            else:
                self.socket = ssl.wrap_socket(self.socket,
                                              cert_reqs=ssl.CERT_NONE,
                                              do_handshake_on_connect=False)
            self.ssl_must_handshake = True
        except ssl.SSLError:
            raise
        
        return (old_socket, self.socket)

    def connect(self):
        """Create a socket and connect to the remote server; at the moment
        we have to do a blocking connect() to support SSL sockets.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)

        try:
            self.socket.connect((self.config['hostname'], self.config['port']))
        except socket.error, e:
            if isinstance(e, str):
                raise
            elif e[0] == errno.EINPROGRESS:
                pass
            else:
                raise
        except socket.gaierror as err:
            print "Unknown host: %s (%s)" % (self.config['hostname'], str(err))
            raise

        self.nick()
        self.ident()

    def send(self, line):
        """Send a command to the IRC server.

        NOTE: outgoing data must not be unicode!
        """
        buf = u"{0}{1}".format(line, NEWLINE)
        if isinstance(line, unicode):
            try:
                buf = buf.encode('utf-8', 'ignore')
            except UnicodeEncodeError, e:
                log.error("Invalid output line: %r" % buf)
                return
        log.debug(">>> %r" % buf)
        self.out_buffer += buf

    def parse_line(self, line):
        """Handle IRC lines

        Each IRC message may consist of up to three main parts: the prefix
        (optional), the command, and the command parameters (of which there
        may be up to 15).

        If the prefix is missing from the message, it is assumed to
        have originated from the connection from which it was received.
        """
        log.debug("<<< %r" % line)

        match = r_ircline.match(line)
        if match is None:
            log.error("Invalid IRC line: %r" % line)
            return

        data = match.groupdict()
        log.debug("IRC msg parsing: %r" % (data,))
        
        if data["source"] is None:
            nickname, ident, hostname = (None, None, None)
        else:
            nickname, ident, hostname = parse_usermask(data["source"])

        command = data["command"]
        argstr = data["args"].strip() if data["args"] else u""
        args = argstr.split()
        text = data["text"] or u""

        # CTCP
        if (text.startswith(CTCPCHR) and text.endswith(CTCPCHR)):
            text = text[1:-1]
            old_command = command

            # we use "args" and "argstr" for CTCP arguments
            ctcp_args = text.split()
            if not ctcp_args:
                return
            command = ctcp_args.pop(0)
            args = ctcp_args[:]
            argstr = u" ".join(args)

            if old_command == u"PRIVMSG":
                command = u"CTCP_" + command
            else:
                command = u"CTCP_REPLY_" + command

        # E' un "comando" del Bot
        elif text.startswith(u"!"):
            try:
                command, text = text[1:].split(u" ", 1)
            except ValueError:
                command, text = text[1:], u""

            # Espande il comando con gli alias
            command = u"cmd_" + COMMAND_ALIASES.get(command, command)

        user = IRCUser(nickname, ident, hostname)
        event = IRCEvent(self, user, command, argstr, args, text)
        self.dispatch_event(event)

    def dispatch_event(self, event):
        log.debug("Dispatching %r" % event)

        # Check only enabled plugins
        plugins = [plugin for plugin in self.bot.plugins if plugin.enabled]
        for handler in [self] + plugins:
            if not hasattr(handler, event.name):
                continue

            fn = getattr(handler, event.name)
            try:
                fn(event)
            except Exception, e:
                log.error("Exception in IRC callback %s: %s" % (
                    event.name, str(e)))
                print traceback.format_exc()

    def check_in_buffer(self):
        """Check for complete lines in the input buffer, encode them in UTF-8
        and pass them to the parser."""
        lines = []
        while "\n" in self.in_buffer:
            nl = self.in_buffer.find("\n")
            if nl == -1:
                break
            line = self.in_buffer[:nl]
            lines.append(line)
            self.in_buffer = self.in_buffer[nl + 1:]

        for line in lines:
            line = line.replace("\r", "")
            
            try:
                line = line.decode('utf-8', 'replace')
            except UnicodeDecodeError, e:
                log.error("Invalid encoding for irc line: %r" % line)
            else:
                self.parse_line(line)

    def after_nickserv(self):
        self.join_all()

    # IRC COMMANDS

    def nick(self, nickname=None):
        """Send a NICK command"""
        
        if nickname is None:
            nickname = self.nicknames[self.nicknames_id]
        self.send(u"NICK {0}".format(nickname))
        self.current_nickname = nickname

    def ident(self):
        """Send an USER command.

        Parameters: <user> <mode> <unused> <realname>
        For example:
            USER guest 8 * :My real name

        Note: user mode '8' means "invisible"
        """
        self.send(u"USER {0} 8 * :{1}".format(
            self.bot.config['ident'],
            self.bot.config['realname']))

    def join(self, channel, key=None):
        """Join a single channel"""
        self.send(u"JOIN {0}{1}".format(
            channel, " " + key if key else ""))

    def join_many(self, channels, keys):
        """Join many channels"""
        self.send(u"JOIN {0} {1}".format(
            ",".join(channels), ",".join(keys)))

    def join_all(self):
        """Join all the configured channels"""
        for channel in self.config['channels']:
            self.join(channel)

    def quit(self, message=None):
        """Quit from the server"""
        if message is None:
            message = get_random_quit()
        self.send(u"QUIT :{0}".format(message))

    def msg(self, target, message):
        self.send(u"PRIVMSG {0} :{1}".format(target, message))

    def notice(self, target, message):
        self.send(u"NOTICE {0} :{1}".format(target, message))

    def me(self, target, message):
        self.msg(target, u"{0}ACTION {1}{0}".format(CTCPCHR, message))

    def ctcp(self, target, message):
        self.msg(target, u"{0}{1}{0}".format(CTCPCHR, message))

    def ctcp_reply(self, target, message):
        self.notice(target, u"{0}{1}{0}".format(CTCPCHR, message))

    def ctcp_ping(self, target):
        tempo = int(time.time())
        self.ctcp(target, u"PING %d" % (tempo,))

    def ctcp_ping_reply(self, target, message):
        self.ctcp_reply(target, u"PING %s" % message)

    def nickserv_login(self):
        self.msg("NickServ", u"IDENTIFY %s" % self.config['nickserv'])
        
    # IRC EVENTS
    def on_001(self, event):
        """Server "welcome".

        If we have to login to NickServ we delay the join of all channels.
        """
        if 'nickserv' in self.config:
            self.nickserv_login()
        else:
            self.join_all()

    def on_433(self, event):
        """Nickname is already in use"""
        self.nicknames_id += 1
        if self.nicknames_id >= len(self.nicknames):
            self.nicknames_id = 0
        self.nick()

    def on_PING(self, event):
        if event.text:
            self.send(u"PONG %s" % event.text)
        else:
            seld.send(u"PONG foobar")

    def on_CTCP_PING(self, event):
        self.ctcp_ping_reply(event.user.nickname, event.argstr)

    def on_CTCP_VERSION(self, event):
        self.ctcp_reply(event.user.nickname, u"%s" % USER_AGENT)

    def on_KICK(self, event):
        channel = event.args[0]
        target = event.args[1].lower()
        
        if target == self.current_nickname.lower():
            self.join(channel)

    def on_NOTICE(self, event):
        """Handle NOTICEs."""
        # Skip message from ourself
        if event.user.nickname == self.current_nickname:
            return

        # React to NickServ messages
        # - after login to nickserv
        # - in case of network collision or when the server changes our nickname
        if event.user.nickname == "NickServ":
            if u"You are now identified" in event.text:
                self.after_nickserv()
            elif u"This nick is owned by someone else." in event.text:
                self.nickserv_login()

    def on_353(self, event):
        """RPL_NAMREPLY - reply to a NAMES command"""
        nicks = event.text.split()
        channel_name = event.args[-1]

    def on_JOIN(self, event):
        channel_name = event.text
        
        if event.user.nickname == self.current_nickname:
            log.info("Joined %s" % channel_name.encode('utf-8', 'replace'))

    def on_PART(self, event):
        channel_name = event.args[0]

    def on_QUIT(self, event):
        pass

    def on_cmd_quitta(self, event):
        if event.user.nickname == u"sand":
            self.bot.quit()
        else:
            self.msg(event.user.nickname, u"NO!")

    def on_cmd_joina(self, event):
        self.join_all()

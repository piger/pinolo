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


class Channel(object):
    def __init__(self, name):
        self.name = name
        self.users = {}

    def add_user(self, nickname, ident=None, address=None):
        user = IRCUser(nickname, ident, address)
        self.users[nickname] = user

    def del_user(self, nickname):
        if nickname in self.users:
            del self.users[nickname]

    def __repr__(self):
        return "<Channel(%s)>" % self.name


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

        # state
        self.channels = {}

    def __repr__(self):
        return "<IRCConnection(%s)>" % self.name

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        try:
            self.socket.connect((self.config['hostname'], self.config['port']))
        except socket.error, e:
            if isinstance(e, str):
                raise
            elif e[0] == errno.EINPROGRESS:
                pass
            else:
                raise
        self.connected = True

        self.nick()
        self.ident()

    def send(self, line):
        """Send a command to the IRC server.

        NOTE: outgoing data must not be unicode!
        """
        buf = u"{0}{1}".format(line, NEWLINE)
        if isinstance(line, unicode):
            buf = buf.encode('utf-8')
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
        command = data["command"].encode("utf-8", "replace")
        argstr = data["args"] or ""
        argstr = argstr.strip()
        args = argstr.split()
        text = data["text"] or ""

        # CTCP
        if (text.startswith(CTCPCHR) and text.endswith(CTCPCHR)):
            text = text[1:-1]
            old_command = command

            # we use "args" and "argstr" for CTCP arguments
            ctcp_args = text.split()
            if not ctcp_args:
                return
            command = ctcp_args.pop(0).encode("utf-8", "replace")
            args = ctcp_args[:]
            argstr = " ".join(args)

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
            # command = "cmd_{0}".format(command)

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
                import traceback
                print "Exception in IRC callback {0}: {1}".format(
                    event.name, str(e))
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
                print "Invalid encoding for irc line: %s" % (line,)
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
        channel = event.args[0].encode("utf-8", "replace")
        target = event.args[1].encode("utf-8", "replace")
        
        if target == self.current_nickname:
            self.join(channel)
        else:
            self.channels[channel].del_user(target)

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
        nicks = event.text.encode('utf-8', 'replace').split()
        channel_name = event.args[-1].encode('utf-8', 'replace')
        
        for nick in nicks:
            self.channels[channel_name].add_user(nick)

    def on_JOIN(self, event):
        name = event.text.encode('utf-8', 'replace')
        
        if event.user.nickname == self.current_nickname:
            channel = Channel(name)
            self.channels[name] = channel
            log.info("Joined %s" % name)
        else:
            self.channels[name].add_user(event.user.nickname)

    def on_PART(self, event):
        name = event.args[0].encode("utf-8", "replace")
        if event.user.nickname == self.current_nickname:
            if name in self.channels:
                del self.channels[name]
        else:
            self.channels[name].del_user(event.user.nickname)

    def on_QUIT(self, event):
        if event.user.nickname != self.current_nickname:
            for channel_name in self.channels:
                self.channels[channel_name].del_user(event.user.nickname)
    
    def on_cmd_quitta(self, event):
        if event.user.nickname == u"sand":
            # self.quit()
            self.bot.quit()
        else:
            self.msg(event.user.nickname, u"a pià nder culo!")

    def on_cmd_joina(self, event):
        self.join_all()

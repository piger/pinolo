# -*- encoding: utf-8 -*-
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
import threading
import Queue
import urllib2
from pinolo.tasks import TestTask
from pinolo.cowsay import cowsay


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
    def __init__(self, nickname, ident, hostname):
        self.nickname = nickname
        self.ident = ident
        self.hostname = hostname

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
        return u"<IRCEvent(client=%r, user=%r, command=%r, args=%r)>" % (
            self.client, self.user, self.command, self.args)


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
        self.out_buffer += buf

    def parse_line(self, line):
        """Handle IRC lines

        Each IRC message may consist of up to three main parts: the prefix
        (optional), the command, and the command parameters (of which there
        may be up to 15).

        If the prefix is missing from the message, it is assumed to
        have originated from the connection from which it was received.
        
        :localhost NOTICE AUTH :TclIRCD-0.1a initialized, welcome.
        NICK foobar
        USER sand 8 * :peto peto peto
        :localhost 001 foobar :Welcome to this IRC server foobar
        :localhost 002 foobar :Your host is localhost, running version TclIRCD-0.1a
        :localhost 003 foobar :This server was created ... I don't know
        :localhost 004 foobar localhost TclIRCD-0.1a aAbBcCdDeEfFGhHiIjkKlLmMnNopPQrRsStUvVwWxXyYzZ0123459*@ bcdefFhiIklmnoPqstv
        JOIN #test
        :foobar!~sand@localhost JOIN :#test
        :localhost 331 foobar #test :There isn't a topic.
        :localhost 353 foobar = #test :@foobar
        :localhost 366 foobar #test :End of /NAMES list.

        PRIVMSG:
        :petello!~petone@localhost PRIVMSG petone :ciao a te

        PING:
        :sand!~sand@localhost PRIVMSG petone :PING 1368113613 585318
        """
        print "<<< %s" % (line,)

        if line.startswith(u":"):
            # IRC message with prefix
            source, line = line[1:].split(u" ", 1)
            nickname, ident, hostname = parse_usermask(source)
        else:
            # IRC message without prefix (e.g. server's PING)
            nickname, ident, hostname = (None, None, None)

        # IRC command (e.g. PRIVMSG)
        # command = PRIVMSG
        # line = petone :ciao a te
        # where "petone" is the target (so it's an argstr) and ":ciao a te"
        # is the command text
        command, line = line.split(u" ", 1)
        # convert command to a string object since it will be used to lookup
        # the handler function (and thus can't be a unicode string)
        command = command.encode('utf-8', 'replace')

        # IRC command arguments and text
        # args will be a list of command arguments and text will be the command
        # text, if any.
        if u" :" in line:
            argstr, text = line.split(u" :", 1)

            # CTCP
            if (text.startswith(CTCPCHR) and text.endswith(CTCPCHR)):
                text = text[1:-1]
                old_command = command

                if u" " in text:
                    command, argstr = text.split(u" ", 1)
                else:
                    command, argstr = text, u""
                text = u""

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

        else:
            argstr, text = line, u""
        args = argstr.split()

        user = IRCUser(nickname, ident, hostname)
        event = IRCEvent(self, user, command, argstr, args, text)
        self.dispatch_event(event)

    def dispatch_event(self, event):
        for handler in [self] + self.bot.plugins:
            if hasattr(handler, event.name):
                fn = getattr(handler, event.name)
                try:
                    fn(event)
                except Exception, e:
                    import traceback
                    print "Exception in IRC callback {0}: {1}".format(
                        event.name, str(e))
                    print traceback.format_exc()
                    event.reply(u"Ho subito una exception, forse dovrei morire")

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

    # IRC COMMANDS

    def nick(self, nickname=None):
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
            message = "Il cesso gallico"
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
        self.join_all()

    def on_433(self, event):
        """Nickname is already in use"""
        self.nicknames_id += 1
        if self.nicknames_id >= len(self.nicknames):
            self.nicknames_id = 0
        self.nick()

    def on_PING(self, event):
        self.send(u"PONG %s" % event.argstr)

    def on_CTCP_PING(self, event):
        self.ctcp_ping_reply(event.user.nickname, event.argstr)

    def on_CTCP_VERSION(self, event):
        self.ctcp_reply(event.user.nickname, u"VERSION EY YE")

    def on_KICK(self, event):
        channel = event.args[0]
        self.join(channel)

    def on_cmd_saluta(self, event):
        event.reply(u"ciao")

    def on_cmd_getta(self, event):
        task = TestTask(self.name, self.coda)
        task.start()

    def on_cmd_quitta(self, event):
        if event.user.nickname == u"sand":
            self.quit()
        else:
            self.msg(event.user.nickname, u"a pià nder culo!")
    
    def on_cmd_cowsay(self, event):
        log.debug("Launching command cowsay")
        righe = cowsay("ciao amico")
        for line in righe:
            event.reply(line)

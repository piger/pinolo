from collections import namedtuple
import optparse


# to track individual IRC users
IRCUser = namedtuple('IRCUser', 'nickname ident hostname')

# OptionParser subclassed for IRC commands
class OptionParserError(Exception): pass

class MyOptionParser(optparse.OptionParser):
    """An OptionParser which raises an OptionParserError instead of sys.exit()"""

    def error(self, msg):
        """Raises OptionParserError with the error message"""

        raise OptionParserError(msg)

    def exit(self, status=0, msg=None):
        """Raises OptionParserError with the error message"""
        raise OptionParserError(msg)

    def print_help(self, file=None):
        msg = self.format_help().encode('utf-8', "replace")
        # msg = msg.split("\n")

        raise OptionParserError(msg)

class Request(object):
    def __init__(self, client, author, channel, reply_to, command, arguments):
        self.client = client
        self.author = author
        self.channel = channel
        self.reply_to = reply_to
        self.command = command
        self.arguments = arguments

    def reply(self, message):
        self.client.reply(self.reply_to, message)

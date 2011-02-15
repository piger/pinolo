import logging
from collections import namedtuple
import optparse

from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager


# to track individual IRC users
IRCUser = namedtuple('IRCUser', 'nickname ident hostname')
Configuration = namedtuple('Configuration',
                           'quotes_db xapian_db pidfile servers')

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
        self.arguments = arguments[:]

    def reply(self, message):
        if self.reply_to.startswith('#'):
            self.client.reply(self.reply_to, "%s: %s" % (self.author.nickname,
                                                         message))
        else:
            self.client.reply(self.reply_to, message)


class BasePlugin(IPlugin):
    def init(self, config):
        """Handle initial configuration through a ``config`` object"""
        pass

class UndefinedPlugin(BasePlugin): pass
class CommandPlugin(BasePlugin): pass

class PluginActivationError(Exception): pass


class MyPluginManager(PluginManager):
    def activatePluginByName(self, name, configuration, category="Default"):
        """
        Activate a plugin corresponding to a given category + name.
        """

        pta_item = self.getPluginByName(name, category)

        if pta_item is not None:
            plugin_to_activate = pta_item.plugin_object

            if plugin_to_activate is not None:
                logging.debug("Activating plugin: %s.%s"% (category,name))
                plugin_to_activate.activate(configuration)
                return plugin_to_activate

            return None

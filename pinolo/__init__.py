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
    """An IRC request object.

    This encapsulate all the informations needed to handle a request coming from
    an IRC user; any plugin can use reply() to reply directly to the user or
    channel where the command was issued.

    Arguments:
        - ``client``: a Pinolo instance
        - ``author``: an IRCUser instance (user who issued the command)
        - ``channel``: channel where the command was issued, if any
        - ``reply_to``: who to respond to (channel or user)
        - ``command``: the command issued
        - ``arguments``: a list with arguments, if any (shlex splitted)

    """
    def __init__(self, client, author, channel, reply_to, command, arguments):
        self.client = client
        self.author = author
        self.channel = channel
        self.reply_to = reply_to
        self.command = command
        self.arguments = arguments[:]

    def reply(self, message, prefix=True):
        """Reply to channel or user (see self.reply_to).

        With ``prefix`` set to False will NOT prefix the user nickname to the
        text.
        """

        if (self.reply_to.startswith('#')
            and prefix):
            self.client.reply(self.reply_to, "%s: %s" % (self.author.nickname,
                                                         message))
        else:
            self.client.reply(self.reply_to, message)


# Yapsy Plugin Categories
class BasePlugin(IPlugin): pass
class UndefinedPlugin(BasePlugin): pass
class CommandPlugin(BasePlugin): pass

class PluginActivationError(Exception): pass


class MyPluginManager(PluginManager):
    """An Extended PluginManager.

    My PluginManager will activate() plugins passing a new parameter
    (*configuration*) which can be used to configure the plugin inizialization.

    A new parameter ``fail_on_error` (default: **True**) on loadPlugins() will
    raise any Exception raised during a plugin inizialization phase.
    """

    def activatePluginByName(self, name, configuration, category="Default"):
        """
        Activate a plugin corresponding to a given category + name.

        NEW PARAMETER: ``configuration``, a *dict* with the plugin
        configuration, passed to plugin's activate().
        """

        pta_item = self.getPluginByName(name, category)

        if pta_item is not None:
            plugin_to_activate = pta_item.plugin_object

            if plugin_to_activate is not None:
                logging.debug("Activating plugin: %s.%s"% (category,name))
                plugin_to_activate.activate(configuration)
                return plugin_to_activate

            return None

        def loadPlugins(self, callback=None, fail_on_error=True):
                """
                Load the candidate plugins that have been identified through a
                previous call to locatePlugins.  For each plugin candidate
                look for its category, load it and store it in the appropriate
                slot of the ``category_mapping``.

                If a callback function is specified, call it before every load
                attempt.  The ``plugin_info`` instance is passed as an argument to
                the callback.

                NEW PARAMETER: ``fail_on_error``, to raise an Exception on
                plugin loading failure.
                """
#               print "%s.loadPlugins" % self.__class__
                if not hasattr(self, '_candidates'):
                        raise ValueError("locatePlugins must be called before loadPlugins")

                for candidate_infofile, candidate_filepath, plugin_info in self._candidates:
                        # if a callback exists, call it before attempting to load
                        # the plugin so that a message can be displayed to the
                        # user
                        if callback is not None:
                                callback(plugin_info)
                        # now execute the file and get its content into a
                        # specific dictionnary
                        candidate_globals = {"__file__":candidate_filepath+".py"}
                        if "__init__" in  os.path.basename(candidate_filepath):
                                sys.path.append(plugin_info.path)
                        try:
                                #candidateMainFile = open(candidate_filepath+".py","r")
                                # exec(candidateMainFile,candidate_globals)
                                execfile(candidate_filepath + '.py',
                                         candidate_globals)
                        except Exception,e:
                                logging.debug("Unable to execute the code in plugin: %s" % candidate_filepath)
                                logging.debug("\t The following problem occured: %s %s " % (os.linesep, e))
                                if "__init__" in  os.path.basename(candidate_filepath):
                                        sys.path.remove(plugin_info.path)

                                # sand
                                if fail_on_error:
                                    raise
                                continue

                        if "__init__" in  os.path.basename(candidate_filepath):
                                sys.path.remove(plugin_info.path)
                        # now try to find and initialise the first subclass of the correct plugin interface
                        for element in candidate_globals.itervalues():
                                current_category = None
                                for category_name in self.categories_interfaces:
                                        try:
                                                is_correct_subclass = issubclass(element, self.categories_interfaces[category_name])
                                        except:
                                                continue
                                        if is_correct_subclass:
                                                if element is not self.categories_interfaces[category_name]:
                                                        current_category = category_name
                                                        break
                                if current_category is not None:
                                        if not (candidate_infofile in self._category_file_mapping[current_category]):
                                                # we found a new plugin: initialise it and search for the next one
                                                plugin_info.plugin_object = element()
                                                plugin_info.category = current_category
                                                self.category_mapping[current_category].append(plugin_info)
                                                self._category_file_mapping[current_category].append(candidate_infofile)
                                                current_category = None
                                        break

                # Remove candidates list since we don't need them any more and
                # don't need to take up the space
                delattr(self, '_candidates')

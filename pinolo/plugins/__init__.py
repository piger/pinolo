# -*- coding: utf-8 -*-
"""
    pinolo.plugins
    ~~~~~~~~~~~~~~

    Plugin base class with a global register storing all the plugins
    instances.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
# This list will store tuples containing the plugin name and the plugin
# instance for each plugin loaded.
registry = []


class Plugin(object):
    """Base class for plugins

    This class use a `metaclass` to save a registry of loaded (aka imported)
    plugins classes that can later be used to create the plugin instances.

    A plugin loading sequence is divided in two steps: in the first step the
    plugin is imported and __init__() executed. After all plugins have been
    loaded the main class will load and activate the database support, so any
    SQLAlchemy model defined in the plugins will be loaded.
    
    When the main class have finished initialization it will call
    :meth:`activate` on every plugin instance.
    """
    
    COMMAND_ALIASES = {}

    class __metaclass__(type):
        def __init__(cls, name, bases, _dict):
            global registry
            
            type.__init__(cls, name, bases, _dict)
            # We must not add this class to the plugin registry!
            if name != "Plugin":
                registry.append((name, cls))

    def __init__(self, bot, enabled=True):
        """Initialize the plugin instance with a pointer to the bot object"""

        self.bot = bot
        self.enabled = enabled

    def activate(self):
        """Activate the plugin

        Here you can load the plugin state from the filesystem, initialize stuff,
        etc.
        """
        pass

    def deactivate(self):
        """Deactivate the plugin

        Here you can save the plugin state on the filesystem, or perform some
        cleanup.
        """
        pass

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
    """Base class for plugins"""
    
    class __metaclass__(type):
        def __init__(cls, name, bases, _dict):
            global registry
            
            type.__init__(cls, name, bases, _dict)
            # We must not add this class to the plugin registry!
            if name != "Plugin":
                registry.append((name, cls))

    def __init__(self, bot):
        """Initialize the plugin instance with a pointer to the bot object"""
        self.bot = bot

    def activate(self):
        """Activate the plugin"""
        pass

    def deactivate(self):
        pass

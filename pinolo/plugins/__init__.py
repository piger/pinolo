registry = []

class Plugin(object):

    COMMAND_ALIASES = {}

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(cls, name, bases, dict)
            registry.append((name, cls))

    def __init__(self, head):
        self.head = head

    def activate(self):
        pass

def load_plugins(head):
    def my_import(name):
        """
        http://effbot.org/zone/import-string.htm#importing-by-filename
        """
        m = __import__(name)
        for n in name.split(".")[1:]:
            m = getattr(m, n)
        return m

    plugins = []
    plugin_dir = os.path.abspath(__file__)
    for root, dirs, files in os.walk(plugin_dir):
        for filename in files:
            if (not filename.endswith('.py')
                or filename == '__init__.py'): continue
            name = os.path.splitext(filename)[0]
            my_import('pinolo.plugins.' + name)

        for plugin_name, PluginClass in registry:
            o = PluginClass(head)

            plugins.append(o)

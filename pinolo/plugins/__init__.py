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

    def deactivate(self):
        pass

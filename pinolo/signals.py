# -*- encoding: utf-8 -*-
# Heavily inspired by signals.py from ranger (file manager).
import weakref


class Signal(dict):
    stopped = False

    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        self.__dict__ = self

    def stop(self):
        self.stopped = True


class SignalHandler:
    active = True

    def __init__(self, name, function, priority):
        self._priority = max(0, min(1, priority))
        self._name = name
        self._function = function

    
class SignalDispatcher(object):
    def __init__(self):
        self._signals = dict()

    def signal_bind(self, name, function, priority=0.5):
        handlers = self._signals.setdefault(name, [])
        handler = SignalHandler(name, function, priority)
        handlers.append(handler)
        return handler

    def signal_unbind(self, signal_handler):
        if signal_handler._name in self._signals:
            signal_handler._function = None
            self._signals[signal_handler._name].remove(signal_handler)

    def signal_emit(self, name, **kw):
        if not name in self._signals:
            return True
        handlers = self._signals[name]
        if not handlers:
            return True

        signal = Signal(origin=self, name=name, **kw)
        
        for handler in tuple(handlers):
            if handler.active:
                try:
                    fn = handler._function
                    fn(signal)
                except Exception, e:
                    log.error("Signal error: %s" % str(e))
                    print "Error in signal: %s" % str(e)
                    
                if signal.stopped:
                    return False
        
        return True

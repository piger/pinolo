# -*- coding: utf-8 -*-
"""
    pinolo.debug
    ~~~~~~~~~~~~

    Fancy runtime debugging utilities.
    Credits: http://stackoverflow.com/questions/132058/getting-stack-trace-from-a-running-python-application

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import code
import traceback
import signal
import readline # history in InteractiveConsole ?


def debug_handler(sig, frame):
    d = { '_frame': frame }
    d.update(frame.f_globals)
    d.update(frame.f_locals)

    readline.parse_and_bind("tab: complete")

    i = code.InteractiveConsole(d)
    message = "Signal received: entering python shell.\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    i.interact(message)

def listen():
    signal.signal(signal.SIGUSR1, debug_handler)

# -*- coding: utf-8 -*-
"""
    pinolo.tasks
    ~~~~~~~~~~~~

    A Task object is a `threading.Thread` instance that will be executed
    without blocking the main thread.
    This is useful to perform potentially blocking actions like fecthing
    resources via HTTP.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import threading


class Task(threading.Thread):
    """A task is an execution unit that will be run in a separate thread
    that should not block tha main thread (handling irc connections).
    """
    def __init__(self, event, *args, **kwargs):
        self.event = event
        super(Task, self).__init__(*args, **kwargs)

    @property
    def queue(self):
        return self.event.client.bot.coda

    @property
    def reply(self):
        return self.event.reply

    def run(self):
        raise RuntimeError("Must be implemented!")
        
    def put_results(self, *data):
        """Task output will be sent to the main thread via the configured
        queue; data should be a string containing the full output, that will
        later be splitted on newlines."""
        self.queue.put(tuple(data))

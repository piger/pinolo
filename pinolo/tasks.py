# -*- encoding: utf-8 -*-
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
import urllib2


class Task(threading.Thread):
    """A task is an execution unit that will be run in a separate thread
    that should not block tha main thread (handling irc connections).
    """
    def __init__(self, connection_name, queue, *args, **kwargs):
        self.connection_name = connection_name
        self.queue = queue
        super(Task, self).__init__(*args, **kwargs)

    def run(self):
        raise RuntimeError("Must be implemented!")
        
    def put_results(self, data):
        """Task output will be sent to the main thread via the configured
        queue; data should be a string containing the full output, that will
        later be splitted on newlines."""
        unit = (self.connection_name, data)
        self.queue.put(unit)


class TestTask(Task):
    def run(self):
        """Main execution function. This must not be called directly! You
        must call threading.Thread.start() method."""

        url = "http://www.spatof.org/blog/robots.txt"
        resp = urllib2.urlopen(url)
        data = resp.read()

        self.put_results(data)

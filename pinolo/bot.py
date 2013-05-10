# -*- encoding: utf-8 -*-
"""
    pinolo.bot
    ~~~~~~~~~~

    The Bot class contains functions to start and stop the bot, handle network
    traffic and loading of plugins.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import os
import re
import socket
import select
import errno
import logging
import Queue
import pinolo.plugins
from pinolo.signals import SignalDispatcher
from pinolo.irc import IRCConnection


log = logging.getLogger()


class Bot(SignalDispatcher):
    """Main Bot controller class.

    Handle the network stuff, must be initialized with a configuration object.
    """
    def __init__(self, config):
        SignalDispatcher.__init__(self)
        self.config = config
        self.connections = {}
        self.connection_map = {}
        self.coda = Queue.Queue()
        self.plugins = []

        for server in config['servers']:
            server_config = config['servers'][server]
            ircc = IRCConnection(server, server_config, self)
            self.connections[server] = ircc

    def start(self):
        # Here we also load and activate the plugins
        self.load_plugins()
        self.activate_plugins()

        self.signal_emit("pre_connect")
        
        for conn_name, conn_obj in self.connections.iteritems():
            print "Connecting to server: {0}".format(conn_name)
            conn_obj.connect()

        for conn_obj in self.connections.values():
            self.connection_map[conn_obj.socket] = conn_obj

        self.running = True
        self.main_loop()

    def main_loop(self):
        """Main loop. Here we handle the network connections and buffers,
        dispatching events to the IRC clients when needed."""
        
        while self.running:
            # For the select() call we must create two distinct groups of sockets
            # to watch for: all the active sockets must be checked for reading, but
            # only sockets with a non empty out-buffer will be checked for writing.
            in_sockets = []
            for connection in self.connections.values():
                if connection.active:
                    in_sockets.append(connection.socket)
                    
            out_sockets = []
            for connection in self.connections.values():
                if len(connection.out_buffer):
                    out_sockets.append(connection.socket)

            # This is ugly. XXX
            if not in_sockets:
                log.error("No more active connections. exiting...")
                self.running = False
                continue

            # select() with 1 second timeout
            readable, writable, exceptional = select.select(in_sockets, out_sockets, [], 1)

            # Do the reading for the readable sockets
            for s in readable:
                
                # We must read data from socket until the syscall returns EAGAIN;
                # when the OS signals EAGAIN the socket would block reading.
                while True:
                    try:
                        chunk = s.recv(512)
                    except socket.error, e:
                        if e[0] == errno.EAGAIN:
                            break
                        else:
                            raise
                    if chunk == '':
                        self.connection_map[s].connected = False
                        self.connection_map[s].active = False
                        print "{0} disconnected".format(self.connection_map[s].name)
                        break
                    else:
                        self.connection_map[s].in_buffer += chunk
                self.connection_map[s].check_in_buffer()

            # scrive
            for s, conn_obj in self.connection_map.iteritems():
                # check if we got disconnected while reading from socket
                if not conn_obj.connected:
                    continue

                while len(conn_obj.out_buffer):
                    try:
                        sent = s.send(conn_obj.out_buffer)
                    except socket.error, e:
                        if e[0] == errno.EAGAIN:
                            break
                        else:
                            raise
                    conn_obj.out_buffer = conn_obj.out_buffer[sent:]

            # controlla coda
            try:
                conn_name, goo = self.coda.get(False, 1)
            except Queue.Empty, e:
                pass
            else:
                for line in goo.split("\n"):
                    self.connections[conn_name].msg("#test", line)

        # end while
    def quit(self):
        """Quit all connected clients"""
        print "Dicono che devo da quitta"
        for conn_obj in self.connections.values():
            conn_obj.quit("Ctrl-C")

    def load_plugins(self):
        """Load all plugins from the plugins module"""
        
        def my_import(name):
            """Import by filename (taken from effbot)"""
            
            m = __import__(name)
            for n in name.split(".")[1:]:
                m = getattr(m, n)
            return m

        plugins_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "plugins")

        self.signal_emit("pre_load_plugins")

        for filename in os.listdir(plugins_dir):
            if (not filename.endswith(".py") or
                filename.startswith("_")):
                continue
            plugin_name = os.path.splitext(filename)[0]
            log.debug("Loading plugin %s" % plugin_name)
            try:
                module = my_import("pinolo.plugins." + plugin_name)
                # module = __import__("pinolo.plugins", plugin_name)
            except Exception, e:
                print "Failed to load plugin '%s'" % plugin_name
                print "Exception: %s" % str(e)
                import traceback
                for line in traceback.format_exception_only(type(e), e):
                    print line
                # continue
                raise

            self.signal_emit("plugin_loaded", plugin_name=plugin_name,
                             plugin_module=module)

        self.signal_emit("post_load_plugins")

    def activate_plugins(self):
        """Call the activate method on all loaded plugins"""
        for plugin_name, plugin_class in pinolo.plugins.registry:
            log.debug("Activating plugin %s" % plugin_name)
            p_obj = plugin_class(self)
            p_obj.activate()
            self.plugins.append(p_obj)
            self.signal_emit("plugin_activated", plugin_name=plugin_name,
                             plugin_object=p_obj)

    def deactivate_plugins(self):
        """Call deactivate method on all the loaded plugins.

        TODO: Should we also destroy the plugin objects?
        """
        for plugin in self.plugins:
            plugin_name = plugin.__class__.__name__
            plugin.deactivate()
            self.signal_emit("plugin_deactivated", plugin_name=plugin_name,
                             plugin_object=plugin)

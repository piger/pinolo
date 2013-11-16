# -*- coding: utf-8 -*-
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
import ssl
import socket
import select
import errno
import time
import logging
import Queue
import traceback
import pinolo.plugins
from pinolo import signals
from pinolo import irc
from pinolo import database
from pinolo import config


log = logging.getLogger()

# Crontab interval in seconds
CRONTAB_INTERVAL = 60

# Timeout in seconds for the select() syscall
SELECT_TIMEOUT = 1


class Bot(signals.SignalDispatcher):
    """Main Bot controller class.

    Handle the network stuff, must be initialized with a configuration object.
    """
    def __init__(self, config):
        signals.SignalDispatcher.__init__(self)
        self.config = config
        self.connections = {}
        self.connection_map = {}
        self.coda = Queue.Queue()
        self.plugins = []
        self.db_uri = "sqlite:///%s" % os.path.join(
            self.config["datadir"], "db.sqlite")
        self.db_engine = None
        self.running = False
        self._last_crontab = time.time()

        for server in config['servers']:
            server_config = config['servers'][server]
            ircc = irc.IRCConnection(server, server_config, self)
            self.connections[server] = ircc

    def start(self):
        # Here we also load and activate the plugins
        self.load_plugins()
        # XXX Database get initialized HERE.
        self.db_engine = database.init_db(self.db_uri)
        self.activate_plugins()

        self.signal_emit("pre_connect")
        
        for conn_name, conn_obj in self.connections.iteritems():
            log.info("Connecting to server: %s", conn_name)
            conn_obj.connect()

        for conn_obj in self.connections.values():
            self.connection_map[conn_obj.socket] = conn_obj

        self.running = True
        self.main_loop()

        # at last...
        self.shutdown()

    def main_loop(self):
        """Main loop. Here we handle the network connections and buffers,
        dispatching events to the IRC clients when needed."""
        
        while self.running:
            # handle_network() will block for at most 1 second during
            # the select() syscall
            self.handle_network()
            self.check_queue()
            self.handle_cron()

    def do_handshake(self, s):
        try:
            s.do_handshake()
        except ssl.SSLError as err:
            if err.args[0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                return False
            else:
                raise
        return True

    def handle_network(self):
        # For the select() call we must create two distinct groups of sockets
        # to watch for: all the active sockets must be checked for reading, but
        # only sockets with a non empty out-buffer will be checked for writing.
        in_sockets = [c.socket for c in self.connections.values() if c.active]
        out_sockets = [c.socket for c in self.connections.values()
                       if len(c.out_buffer)]

        # This is ugly. XXX
        if not in_sockets:
            log.warning("No more active connections. exiting...")
            self.running = False
            return

        readable, writable, _ = select.select(in_sockets, out_sockets, [],
                                              SELECT_TIMEOUT)

        # Do the reading for the readable sockets
        for s in readable:
            connection = self.connection_map[s]
            self._handle_network_in(connection)

        # scrive
        for s in writable:
            connection = self.connection_map[s]

            # If this is the first time we get a "writable" status then
            # we are actually connected to the remote server.
            if connection.connected == False:
                log.info("Connected to %s", connection.name)
                connection.connected = True

                # SSL socket setup
                if connection.config["ssl"]:
                    connection.wrap_ssl()
                    # swap the socket in the connection map with the ssl one
                    del self.connection_map[s]
                    self.connection_map[connection.socket] = connection

            # SSL handshake
            if connection.ssl_must_handshake and connection.connected:
                if not self.do_handshake(connection.socket):
                    continue
                
            # check if we got disconnected while reading from socket
            # XXX should be empty the out buffer?
            if not connection.connected:
                log.error("Trying to write to a non connected socket!")
                connection.out_buffer = ""
                continue

            while len(connection.out_buffer):
                try:
                    sent = connection.socket.send(connection.out_buffer)
                    connection.out_buffer = connection.out_buffer[sent:]
                    # Qui si potrebbe inserire una pausa artificiale
                    # per evitare i flood? ma il flood anche sticazzi,
                    # server *decenti* tipo inspircd non hanno più quel
                    # problema.
                except (socket.error, ssl.SSLError) as err:
                    if err.args[0] in (errno.EAGAIN, ssl.SSL_ERROR_WANT_WRITE):
                        break
                    else:
                        raise

    def _handle_network_in(self, connection):
        # Do SSL handshake if needed
        if connection.ssl_must_handshake and connection.connected:
            if not self.do_handshake(connection.socket):
                return

        # We must read data from socket until the syscall returns EAGAIN;
        # when the OS signals EAGAIN the socket would block reading.
        while True:
            try:
                chunk = connection.socket.recv(512)
            except (socket.error, ssl.SSLError) as err:
                if err.args[0] in (errno.EAGAIN, ssl.SSL_ERROR_WANT_READ):
                    break
                else:
                    raise

            if chunk == '':
                connection.connected = False
                connection.active = False
                log.info("%s disconnected (EOF)", connection.name)
                return
            else:
                connection.in_buffer += chunk
        connection.check_in_buffer()

    def check_queue(self):
        """Check the thread queue

        THIS IS JUST A PROTOTYPE!
        We should pass the IRC event in the Thread object, so we can later send
        the output to the correct channel or nickname.
        """
        try:
            data = list(self.coda.get_nowait())
        except Queue.Empty:
            pass
        else:
            fn = data.pop(0)
            fn(*data)

    def handle_cron(self):
        """A simple crontab that will be run approximatly every
        CRONTAB_INTERVAL seconds."""
        now = time.time()
        
        if (now - self._last_crontab) >= CRONTAB_INTERVAL:
            self._last_crontab = now

    def quit(self, message="Ctrl-C"):
        """Quit all connected clients"""

        log.info("Shutting down all connections")
        for conn_obj in self.connections.itervalues():
            conn_obj.quit(message)

    def load_plugins(self, exit_on_fail=False):
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

        disabled_plugins = self.config.get("disabled_plugins", [])

        filtro = re.compile(r"^[^_].+\.py$")
        for filename in [name for name in os.listdir(plugins_dir)
                         if filtro.match(name)]:
            plugin_name = os.path.splitext(filename)[0]

            if plugin_name in disabled_plugins:
                log.info("Not loading disabled plugin (from config): %s",
                         plugin_name)
                continue
            
            log.info("Loading plugin %s", plugin_name)
            try:
                module = my_import("pinolo.plugins." + plugin_name)
            except Exception, e:
                print "Failed to load plugin '%s':" % plugin_name
                for line in traceback.format_exception_only(type(e), e):
                    print "-", line,
                if exit_on_fail:
                    raise

            self.signal_emit("plugin_loaded", plugin_name=plugin_name,
                             plugin_module=module)

        self.signal_emit("post_load_plugins")

    def activate_plugins(self):
        """Call the activate method on all loaded plugins"""

        def basename(s):
            return s.split(".")[-1]

        for _, plugin_class in pinolo.plugins.registry:
            plugin_name = basename(plugin_class.__module__)
            log.info("Activating plugin %s", plugin_name)
            if plugin_name in self.config["plugins"]:
                plugin_config = self.config["plugins"][plugin_name]
            else:
                plugin_config = config.empty_config(self.config, plugin_name)

            p_obj = plugin_class(self, plugin_config)
            p_obj.activate()
            self.plugins.append(p_obj)
            irc.COMMAND_ALIASES.update(p_obj.COMMAND_ALIASES.items())
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

    def shutdown(self):
        log.info("Bot shutdown")
        self.deactivate_plugins()

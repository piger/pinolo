#!/usr/bin/env python

import sys
from twisted.python import log
from irc import *
import db

factories = []

def stopConnections():
    global factories
    for factory in factories:
	factory.connection.quit("ADIEU!")


def main():
    #import ConfigParser
    from re import split
    global factories

    # start logging
    log.startLogging(sys.stdout)

    #defaultConfigFile = "./pinolo.cfg"
    #config = ConfigParser.ConfigParser()
    #config.read(defaultConfigFile)

    #channels = re.split("\s*,\s*", config.get("General", "channels"))

    #bot = Pinolo( channels,
    #        config.get("General", "nickname"),
    #        config.get("General", "server"),
    #        int(config.get("General", "port")),	    # int !
    #        config.get("NickServ", "password") )

    #bot.start()

    # quick conf
    servers = [
	{
	    'name' : "AZZURRA",
	    'address' : 'irc.azzurra.org',
	    'port' : 6667,
	    'nickname': 'p1nol0',
	    'channels' : ['#mortodentro']
	},
	{
	    'name' : "FREAKNET",
	    'address' : 'irc.hinezumilabs.org',
	    'port' : 6667,
	    'nickname': 'p1nol0',
	    'channels' : ['#test123']
	}
    ]

    for server in servers:
	f = PinoloFactory(server)
	factories.append(f)
	reactor.connectTCP(server['address'], 6667, f)
    reactor.addSystemEventTrigger('before', 'shutdown', stopConnections)

    reactor.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python

import sys
from irc import *
import db

def main():
    from twisted.python import log
    #import ConfigParser
    from re import split

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

    f = []
    for server in servers:
	factory = PinoloFactory(server)
	reactor.connectTCP(server['address'], 6667, factory)
	f.append(factory)
    reactor.run()

if __name__ == "__main__":
    main()

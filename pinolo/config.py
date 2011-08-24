import os, sys, re
from ConfigParser import SafeConfigParser
from collections import namedtuple

class ConfigError(Exception): pass
class ConfigFilesNotFound(ConfigError): pass

class Config(object):
    def __init__(self, name, **entries):
        self.config_name = name
        self.__dict__.update(entries)

    def __repr__(self):
        return "<Config %s(%s)>" % (self.config_name,
                                    ', '.join(["%s = %r" % (name, value)
                                               for name, value in self.__dict__.iteritems()]))


def read_config_files(filenames):
    cfp = SafeConfigParser()
    ret = cfp.read(filenames)
    if not ret:
        raise RuntimeError("No config file found!")

    config = {}
    for section in cfp.sections():
        config[section] = dict(cfp.items(section))

    fix_config(config)
    general = config['general']
    cfg = GeneralConfig(nickname=general['nickname'] or 'pinolo',
                        ident=general['ident'] or 'pinolo',
                        realname=general['realname'] or 'Pinot di pinolo',
                        datadir=general.get('datadir', os.getcwd()))

    for section in config.keys():
        if section == 'general': continue
        server = config[section]
        srv = ServerConfig(address=server['address'],
                           port=server['port'],
                           ssl=server.get('ssl', False),
                           channels=server['channels'],
                           nickserv=server.get('nickserv', None),
                           password=server.get('password', None),
                           nickname=server.get('nickname', cfg.nickname))
        cfg.servers[section] = srv

    return cfg

    # config['servers'] = {}
    # for section in config.keys():
    #     if section not in ('general', 'servers'):
    #         config['servers'][section] = Config('servers', **config[section])
    #         del config[section]
    # config["general"] = Config('general', **config["general"])
    # # config["servers"] = config["servers"])

    # return Config('global', **config)

numeric_options = ('port',)
boolean_options = ('ssl',)
list_options = ('channels',)
time_options = ('timeout',)

def boolywood(value):
    if value.lower() in ('0', 'false', 'no', 'nein', 'off'):
        return False
    return True

def parse_timeout(text):
    # 1h2m30s 1m30s 40s 2m
    match = re.match(r'(?:(\d*)h)?(?:(\d*)m)?(?:(\d*)s)?', text, re.I)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return (hours, minutes, seconds)
    raise RuntimeError("Invalid time format")

def fix_config(global_config):
    for name, config in global_config.iteritems():
        for option in numeric_options:
            if option in config:
                config[option] = int(config[option])
        for option in boolean_options:
            if option in config:
                config[option] = boolywood(config[option])
        for option in list_options:
            if option in config:
                config[option] = [x.strip() for x in config[option].split(',')]
        for option in time_options:
            if option in config:
                config[option] = parse_timeout(config[option])


class NewConfig(object): pass

class GeneralConfig(NewConfig):
    def __init__(self, nickname, ident, realname, datadir):
        self.nickname = nickname
        self.ident = ident
        self.realname = realname
        self.datadir = datadir

        self.servers = {}

class ServerConfig(NewConfig):
    def __init__(self, address, port, ssl=False, channels=None,
                 nickserv=None, password=None, nickname=None):
        self.address = address
        self.port = int(port)
        self.ssl = ssl
        if isinstance(channels, list):
            self.channels = channels[:]
        elif channels:
            self.channels = [channels]
        else:
            self.channels = []
        self.nickserv = nickserv
        self.password = password
        self.nickname = nickname


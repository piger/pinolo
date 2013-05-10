# -*- encoding: utf-8 -*-
"""
    pinolo.config
    ~~~~~~~~~~~~~

    Configuration file handling. Boring stuff.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import re
import codecs
from ConfigParser import SafeConfigParser


r_comma = re.compile(r'\s*,\s+')


def read_config_file(filename):
    cfp = SafeConfigParser()
    with codecs.open(filename, 'r', 'utf-8') as fd:
        cfp.readfp(fd, filename)

    config = dict(cfp.items("general"))
    config['servers'] = {}

    for opt in ('nicknames',):
        if opt in config:
            config[opt] = r_comma.split(config[opt])

    for section in cfp.sections():
        if not section.startswith("server:"):
            continue

        server_name = section.split(':')[1]
        server_config = dict(cfp.items(section))

        for opt in ('port',):
            server_config[opt] = int(server_config[opt])

        for opt in ('channels',):
            server_config[opt] = r_comma.split(server_config[opt])
            
        config['servers'][server_name] = server_config

    return config

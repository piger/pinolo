# -*- coding: utf-8 -*-
"""
    pinolo.config
    ~~~~~~~~~~~~~

    Configuration file handling. Boring stuff.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
import coil


def read_config_file(filename):
    """Read a configuration file in coil format and returns a Struct
    object (dict-like)"""

    def fatal(msg):
        sys.stderr.write("%s\n" % msg)
        sys.exit(1)
    
    config = coil.parse_file(filename, encoding="utf-8")

    if config.get("@root.datadir") is None:
        fatal("Config error: empty 'datadir' parameter")

    to_expand = ("@root.datadir", "@root.plugins.quotes2.db_path",
                 "@root.plugins.markov.db_file")
    for name in to_expand:
        path = config.get(name)
        if path is not None and path.startswith("~"):
            config.set(name, os.path.expanduser(path))
        
    return config

def empty_config(root, name):
    return coil.struct.Struct(container=root["plugins"], name=name)

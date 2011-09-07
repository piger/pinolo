#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
warnings.simplefilter('default')

import logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger('pinolo')

import optparse
from pinolo.config import read_config_files
from pinolo.irc import BigHead
from pinolo import FULL_VERSION

def main():
    parser = optparse.OptionParser(description="%s: "
                                   "the naughthy chat bot." % FULL_VERSION,
                                   version=FULL_VERSION)
    parser.add_option('--config',
                      help="Path to the configuration file")
    parser.add_option('--debug', action="store_true",
                      help="Set log level to DEBUG")
    parser.add_option('--unicode_nazi', action="store_true",
                      help="Enable unicode-nazi")
    opts, args = parser.parse_args()
    if not opts.config:
        parser.error("You must specify a configuration file")
    if opts.debug:
        logger.setLevel(logging.DEBUG)
    if opts.unicode_nazi:
        try:
            import unicodenazi
        except ImportError:
            pass

    config = read_config_files([opts.config])
    head = BigHead(config)
    head.run()

if __name__ == '__main__':
    main()

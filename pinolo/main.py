#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
warnings.simplefilter('default')

import sys
import logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S %d/%m/%y")
logger = logging.getLogger('pinolo')

from pinolo.options import Options
from pinolo.config import read_config_files
from pinolo.irc import BigHead
from pinolo import FULL_VERSION

optspec = """
pinolo [options]
--
c,config=   Read configuration options from file.
d,debug     Enable debugging messages.
unaz        Load 'unicode-nazi' library to debug unicode errors.
"""
header = "%s, the naughty chat bot." % FULL_VERSION

def main():
    print header
    o = Options(optspec)
    (options, flags, extra) = o.parse(sys.argv[1:])

    if not options.config:
        o.fatal("You must specify a configuration file!")
    if options.debug:
        logger.setLevel(logging.DEBUG)
    if options.unaz:
        try:
            import unicodenazi
        except ImportError:
            logger.warning("Cannot find unicode-nazi package!")

    config = read_config_files(options.config)
    head = BigHead(config)
    head.run()

if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
import logging
import getopt
import sys
import os
from pinolo.bot import Bot
from pinolo.config import read_config_file


logging.basicConfig(level=logging.WARNING,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S %d/%m/%y")

usage = \
"""
Usage: {0} [-v] [-d] [-h] [-V] -c filename
    {0} [--verbose] [--debug] [--help] [--version] --config filename
"""

version = "pinolo x.y"


def fatal(msg, code=1):
    """Print an error message and exit the program"""
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.exit(code)

    
def main():
    """Command line entry point"""
    opt_short = 'c:dvVh'
    opt_long = ['config=', 'debug' , 'verbose', 'version', 'help']
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], opt_short, opt_long)
    except getopt.GetoptError, e:
        fatal(e)

    options = {
        'config_file': None,
        'verbose': False,
        'debug': False,
    }
    
    for name, value in opts:
        if name in ('-h', '--help'):
            print usage.format(os.path.basename(sys.argv[0]))
            sys.exit(0)
        elif name in ('-c', '--config'):
            options['config_file'] = value
        elif name in ('-d', '--debug'):
            options['debug'] = True
        elif name in ('-v', '--verbose'):
            options['verbose'] = True
        elif name in ('-V', '--version'):
            print version
            sys.exit(0)

    # Check for mandatory options
    if not options['config_file']:
        fatal("You must specify a configuration file")

    # Set the global logging level
    root_log = logging.getLogger()
    if options['debug']:
        root_log.setLevel(logging.DEBUG)
    elif options['verbose']:
        root_log.setLevel(logging.INFO)
    else:
        root_log.setLevel(logging.WARNING)

    start_bot(options)


def start_bot(options):
    """Launch the irc bot instance"""
    config = read_config_file(options['config_file'])
    bot = Bot(config)

    # This try block is ugly but allow us to catch the interrupt signal
    # and still do a clean exit.
    try:
        bot.start()
    except KeyboardInterrupt:
        print "\nInterrupt, exiting.\nPress CTRL-C again to force exit"
        bot.quit()
        bot.main_loop()


if __name__ == '__main__':
    main()

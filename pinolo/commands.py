#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pinolo import args, main
import pinolo


def help_command(**options):
    """
    Prints out help for the commands. 

    pinolo help

    You can get help for one command with:

    pinolo help -for STR
    """
    if "for" in options:
        help_text = args.help_for_command(pinolo.commands, options['for'])
        if help_text:
            print help_text
        else:
            args.invalid_command_message(pinolo.commands, exit_on_error=True)
    else:
        print "Available commands:\n"
        print ", ".join(args.available_commands(pinolo.commands))
        print "\nUse pinolo help -for <command> to find out more."


def start_command(config='local.cfg', debug=False):
    """
    Runs pinolo with configuration found in pinolo.cfg:

    pinolo start -config pinolo.cfg -debug False
    """
    c = main.parse_config_file(config)
    main.run_foreground(c)


def stop_command(config='pinolo.cfg', debug=False):
    """
    Stops a running pinolo:

    pinolo stop -config pinolo.cfg -debug False
    """
    pass

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRCD plugin

"""

import os
import random
import subprocess
from pprint import pprint

from pkg_resources import resource_string
from twisted.python import log

from pinolo.main import CommandPlugin, PluginActivationError
from pinolo import MyOptionParser, OptionParserError


# Only these prcd files contains one line sentences.
PRCD_FILES = [
    'prcd_cri.txt',
    'prcd_dio.txt',
    'prcd_ges.txt',
    'prcd_mad.txt',
    'prcd_mtc.txt',
    'prcd_pap.txt',
    'prcd_vsf.txt',
]

COWSAY_SHAPES = [
    'apt', 'bong', 'bud-frogs', 'bunny',
    'cock', 'cower', 'default', 'duck',
    'flaming-sheep', 'head-in', 'hellokitty',
    'koala', 'moose', 'mutilated', 'satanic',
    'sheep', 'small', 'sodomized', 'sodomized-sheep',
    'suse', 'three-eyes', 'tux', 'udder',
    'vader',
]


def find_cowsay():
    """Find a cowsay binary in common system paths."""

    cowsay = None

    for f in [
        '/usr/games/cowsay',
        '/usr/bin/cowsay',
        '/usr/local/bin/cowsay',
        '/opt/bin/cowsay',
        '/opt/local/bin/cowsay',
    ]:
        if os.access(f, os.R_OK | os.X_OK):
            return f

    return None


def setup_prcd_database():
    """Read all the prcd files and build the database"""

    prcd_db = {}

    def extract_category(name):
        """Extract the category name from filename: prcd_(CATEGORY).txt"""

        u = name.index('_')
        e = name.index('.')

        return name[u+1:e]

    for f in PRCD_FILES:
        path = os.path.join('data', 'prcd', f)
        content = resource_string('pinolo', path)
        content = [line.strip() for line in content.split("\n")]
        content = [line for line in content if line != '']

        category = extract_category(f)
        prcd_db[category] = content

    return prcd_db


class Prcd(CommandPlugin):
    """This is the PRCD plugin"""

    prcd_opt = MyOptionParser(usage="!prcd [options]")
    cowsay_opt = MyOptionParser(usage="!PRCD [options]")

    def activate(self, config=None):
        super(Prcd, self).activate()

        self.prcd_db = setup_prcd_database()
        self.cowsay_bin = find_cowsay()

    def handle(self, request):
        if request.command in [ 'prcd' ]:
            try:
                (options, args) = self.prcd_opt.parse_args(request.arguments)
            except OptionParserError, e:
                request.reply(str(e))
            else:
                self.simple_prcd(request, options, args)

        elif request.command in [ 'PRCD' ]:
            try:
                (options, args) = self.cowsay_opt.parse_args(request.arguments)
            except OptionParserError, e:
                request.reply(str(e))
            else:
                self.cowsay(request, options, args)


    def simple_prcd(self, request, options, args):
        moccolo = None

        if options.category:
            if not options.category in self.prcd_db:
                request.reply("Categoria non trovata :(")
                return

            moccolo = random.choice(self.prcd_db[options.category])

        else:
            category = random.choice(self.prcd_db.keys())
            moccolo = random.choice(self.prcd_db[category])
            moccolo = "%s, %s" % (category, moccolo)

        request.reply(moccolo)


    def cowsay(self, request, options, args):
        shape = None
        moccolo = None

        if not self.cowsay_bin:
            request.reply("Non posseggo il binario... BINAAAARIOOOOOOOO... "
                          "TRISTE E SOLITARIOOOOOOOOOO...")
            return

        if options.shape:
            if not options.shape in COWSAY_SHAPES:
                request.reply("Quella forma non la posseggo")
                return

            shape = options.shape
        else:
            shape = random.choice(COWSAY_SHAPES)

        if options.category:
            if not options.category in self.prcd_db:
                request.reply("Categoria non trovata PER GIOVE!")
                return

            moccolo = random.choice(self.prcd_db[options.category])

        else:
            category = random.choice(self.prcd_db.keys())
            moccolo = random.choice(self.prcd_db[category])

        cmdline = [self.cowsay_bin, '-f', shape]
        pope = subprocess.Popen(cmdline, shell=False,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        (bocca, culo) = (pope.stdin, pope.stdout)
        bocca.write(moccolo)
        bocca.close()

        formina = culo.read()
        #formina = formina.strip()

        request.reply(formina, prefix=False)


Prcd.prcd_opt.add_option('-c', '--category', dest='category',
                         help='Seleziona il moccolo da una categoria')
Prcd.cowsay_opt.add_option('-c', '--category', dest='category',
                           help='Seleziona il moccolo da una categoria')
Prcd.cowsay_opt.add_option('-s', '--shape', dest='shape',
                           help='Seleziona una delle shape disponibili')

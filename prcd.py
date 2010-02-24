#!/usr/bin/env python

from __future__ import with_statement
import os
import random

PRCDPATH = './prcd/'
SKIPFILES = [ 'prcd_int.txt', 'prcd_out.txt',
             'prcd_rd!.txt', 'prcd_vpf.txt',
             'prcd_hst.txt' ]

class PathNotFoundError(Exception): pass

class Prcd():
    def __init__(self, prcd_path=PRCDPATH):
        self.prcd = {}

        if not os.path.exists(prcd_path):
            raise(PathNotFoundError, "prcd-path invalid")

        for path, names, files in os.walk(prcd_path):
            for f in files:
                if not f.endswith('.txt') or f in SKIPFILES:
                    continue

                fullpath = os.path.join(path, f)
                with open(fullpath) as fd:
                    self.prcd[f] = filter(lambda l: len(l.strip()) > 0,
                                          fd.readlines())

    def a_caso(self, categoria=None):
        if categoria is None:
            categoria = random.choice(self.prcd.keys())

        return categoria, random.choice(self.prcd[categoria]).\
                strip().strip("\n")

    def categorie(self):
        return self.prcd.keys()

if __name__ == '__main__':
    p = Prcd()

    print p.a_caso()

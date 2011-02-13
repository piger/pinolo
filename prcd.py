#!/usr/bin/env python
# Copyright (C) 2010-2011 sand <daniel@spatof.org>
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation and/or
#    other materials provided with the distribution.
# 3. The name of the author nor the names of its contributors may be used to
#    endorse or promote products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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

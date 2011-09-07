#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import random
import pkg_resources

def read_replies_file(filename):
    path = pkg_resources.resource_filename(__name__, "data/" + filename)
    fd = codecs.open(path, encoding='utf-8')
    replies = []
    for line in fd:
        line = line.strip()
        if line and not line.startswith(u'#'):
            replies.append(line)
    fd.close()
    return replies

random_quits = read_replies_file("quit.txt")
random_replies = read_replies_file("replies.txt")

def get_random_quit():
    return random.choice(random_quits)

def get_random_reply():
    return random.choice(random_replies)

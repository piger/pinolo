#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random

from pkg_resources import resource_string


QUIT_FILE = os.path.join('data', 'quit.txt')
REPLY_FILE = os.path.join('data', 'replies.txt')


def _read_flat_file(filename):
    return [x for x in resource_string(__name__, filename).split('\n')
             if x != '']

_random_quits = _read_flat_file(QUIT_FILE)
_random_replies = _read_flat_file(REPLY_FILE)

def random_quit():
    return random.choice(_random_quits)

def random_reply(subject=None):
    reply = random.choice(_random_replies)

    if subject:
        return subject + ': ' + reply
    else:
        return reply

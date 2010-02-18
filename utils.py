#!/usr/bin/env python

import re

def clean_irc(msg):
    """Prende del testo da IRC e lo pulisce da:
    - nickname: a inizio riga
    - whitespace
    - encoding utf-8
    """
    # strippa "nick: " all'inizio delle frasi
    msg = re.sub("^[^:]+:\s+", '', msg, 1)
    # strippa newline
    msg = re.sub("\n$", "", msg)
    # strippa whitespace a inizio e fine riga
    msg = msg.strip()
    #return unicodize(msg)
    return msg

def unicodize(s):
    """thx _ale"""
    for enc in ['ascii', 'utf-8', 'iso-8859-15', 'iso-8859-1']:
        try:
            return unicode(s, enc)
        except UnicodeDecodeError:
            continue
    return s

if __name__ == '__main__':
    from sys import exit
    exit()

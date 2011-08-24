# -*- encoding: utf-8 -*-

import logging
import subprocess
import random
import shlex

logger = logging.getLogger('pinolo.cowsay')

# le flag per modificare gli occhi della mucca
eyes_flags = ('b', 'd', 'g', 'p', 's', 't', 'w', 'y', '')

# le shape da escludere, troppo grandi per IRC
exclude = ('unipony', 'cheese', 'pony', 'beavis.zen', 'calvin',
           'daemon', 'dragon', 'dragon-and-cow', 'eyes', 'ghostbusters',
           'gnu', 'kosh', 'mech-and-cow', 'milk', 'ren', 'stegosaurus',
           'turkey', 'turtle', 'meow', 'snowman', 'stimpy')

def get_shapes():
    try:
        p = subprocess.Popen(['cowsay', '-l'], stdout=subprocess.PIPE)
        output = p.communicate()[0]
    except OSError, e:
        logger.error("ERROR: Disabling cowsay (%s)" % e)
        return []

    output = output[output.index("\n")+1:]
    shapes = [x for x in output.split() if x not in exclude]
    return shapes
shapes = get_shapes()

def random_flag():
    flag = random.choice(eyes_flags)
    if flag != '':
        flag = "-" + flag
    return flag

def cowsay(message):
    """
    Ritorna una lista contenente l'output di cowsay.
    """
    if not shapes: return None
    shape = random.choice(shapes)
    cmdline = shlex.split('cowsay %s -f %s' % (random_flag(), shape))
    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    output = p.communicate(message)[0]
    output = output.decode('utf-8')
    return output.split(u"\n")

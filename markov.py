#!/usr/bin/env python
# pynolo - markov chains
#
# sand <daniel@spatof.org> - Sett-09
#
# credits:
# http://code.autistici.org/trac/hmbot/browser
# http://www.eflorenzano.com/blog/post/writing-markov-chain-irc-bot-twisted-and-python/
# http://uswaretech.com/blog/2009/06/pseudo-random-text-markov-chains-python/

import random
import pickle
import os
import re
from collections import defaultdict
from utils import *

class Markov(object):
    def __init__(self, brain_file='brain.new',
	    sample_text='/Users/sand/Downloads/i_promes.txt', autosave=50):
	"""autosave = 0 per disattivare"""

	self.markov = defaultdict(list)
	self.brain_file = brain_file
	self.sample_text = sample_text
	self.autosave = autosave
	self.counter = 0

	if os.path.exists(self.brain_file):
	    fd = open(self.brain_file, 'rb')
	    self.markov = pickle.load(fd)
	    fd.close()
	else:
	    self.learn_from_file(self.sample_text)

    def dump_brain(self):
	fd = open(self.brain_file, 'wb')
	pickle.dump(self.markov, fd, pickle.HIGHEST_PROTOCOL)
	fd.close()

    def learn_from_file(self, filename):
	fd = open(filename, 'r')
	fd.seek(0)
	data = fd.read()
	data = unicodize(data)
	words = data.split()
	fd.close()
	if len(words) < 2:
	    print "Poche parole nel file da imparare."
	    raise Exception
	else:
	    print "totale parole: %i" % (len(words))

	# avoid autosave
	old_autosave = self.autosave
	self.autosave = 0
	self.learn(words)
	self.autosave = old_autosave

	self.dump_brain()

    def learn(self, words):
	if len(words) < 2:
	    return None

	chain = [None, None]
	for word in words:
	    chain[0], chain[1] = chain[1], word
	    if chain[0]:
		self.markov[chain[0]].append(chain[1])

	if self.autosave > 0:
	    self.counter += 1
	    if self.counter >= self.autosave:
		self.counter = 0
		self.dump_brain()

    def gen(self, sample=None, max_words=20):
	message = []

	if sample:
	    sample_words = sample.split()
	    random.shuffle(sample_words)
	    for word in sample_words:
		if self.markov.has_key(word):
		    message.append(word)
		    break

	# non ci sono dati sample, ne prendo uno a caso
	if len(message) == 0:
	    message.append(random.choice(self.markov.keys()))

	while len(message) < max_words:
	    if self.markov.has_key(message[-1]):
		message.append(random.choice(self.markov[message[-1]]))
	    else:
		message.append(random.choice(self.markov.keys()))

	    # mi fermo se c'e' un punto nella frase
	    if message[-1].endswith('.'):
		break

	return (' '.join(message) + '.').capitalize()

def usage():
    print "%s: [-h] [-g \"sample text\"] [-i \"input file\"]" % ("markov.py")

if __name__ == '__main__':
    import getopt, sys

    try:
	opts, args = getopt.getopt(sys.argv[1:], "hri:g:", ["help", "random", "import=",
	    "generate="])
    except getopt.GetoptError, err:
	print str(err)
	usage()
	sys.exit(2)

    m = Markov(autosave=0)

    for o, a in opts:
	if o in ("-g", "--generate"):
	    print m.gen(a)
	elif o in ("-i", "--import"):
	    m.learn_from_file(a)
	elif o in ("-h", "--help"):
	    usage()
	    sys.exit()
	elif o in ("-r", "--random"):
	    print m.gen()
	else:
	    assert False, "unhandled option"

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
import sys

class Markov(object):
    def __init__(self, brain_file='brain.b', autosave=50):
	"""autosave = 0 per disattivare"""
	self.cache = {}
	self.brain_file = brain_file
	self.setup_brain()

	self.autosave = 100
	self.counter = 0

	# XXX questo lo devo calcolare runtime
	#self.word_size = len(self.words)

	# e' che non capisco nel codice quando e se utilizza quelle probabilita'

    def setup_brain(self):
	if os.path.exists(self.brain_file):
	    fd = open(self.brain_file, 'r')

	    data = pickle.load(fd)
	    for k, v in data.iteritems():
		self.cache[k] = v

	    fd.close()

    def clean_irc(self, msg):
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
	#return msg.encode('utf-8')
	return msg

    def triples(self, words):
	if len(words) < 3:
	    return

	for i in range(len(words) - 2):
	    yield(words[i], words[i+1], words[i+2])

    def add_to_brain(self, msg):
	msg = self.clean_irc(msg)
	words = msg.split()

	for w1, w2, w3 in self.triples(words):
	    key = (w1, w2)
	    if key in self.cache:
		self.cache[key].append(w3)
	    else:
		self.cache[key] = [w3]

	# dumpa il brain ogni self.autosave chiamate a questa funzione.
	if self.autosave > 0:
	    self.counter += 1
	    if self.counter >= self.autosave:
		self.counter = 0
		self.dump_brain()

    def generate_text(self, msg, size=25):
	msg = self.clean_irc(msg)
	words = msg.split()

	if len(words) < 2:
	    w1, w2 = random.choice(self.cache.keys())
	else:
	    w1, w2 = words[0], words[1]

	gen_words = []
	for i in xrange(size):
	    gen_words.append(w1)
	    try:
		w1, w2 = w2, random.choice(self.cache[(w1, w2)])
	    except KeyError:
		break
	gen_words.append(w2)

	result = ' '.join(gen_words)
	if result.strip() == msg.strip():
	    return None
	else:
	    return result

    def dump_brain(self):
	fd = open(self.brain_file, 'w')
	pickle.dump(self.cache, fd, pickle.HIGHEST_PROTOCOL)
	fd.close()
	print "ho dumpato"


if __name__ == '__main__':

    if len(sys.argv) < 3:
	print "diohan: <brain file> <input file>"
	sys.exit(-1)

    m = Markov(brain_file=sys.argv[1], autosave=0)
    fd = open(sys.argv[2], 'r')
    counter = 0
    for line in fd:
        # x-chat
        # Aug 03 00:50:10 TheOsprey       culoh
	if re.match("^\w+ \d+ \d+:\d+:\d+ \S+", line):
	    m.add_to_brain(' '.join(line.split()[4:]))
	    counter += 1

    m.dump_brain()
    fd.close()
    print "Aggiunti: %s" % (counter)

    #m = Markov(autosave=0)
    #for i in range(10):
    #    if len(sys.argv) > 1:
    #        print m.generate_text(sys.argv[1])
    #    else:
    #        print m.generate_text('test')

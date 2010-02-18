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
import cPickle as pickle
import os
import re
from collections import defaultdict
from utils import *

class Markov(object):
    def __init__(self, n=2, max_words=25, brain_file='brain.new',
	    sample_text='/Users/sand/Downloads/i_promes.txt', autosave=50):
	"""autosave = 0 per disattivare"""

	self.markov = defaultdict(list)
	self.brain_file = brain_file
	self.sample_text = sample_text
	self.autosave = autosave
	self.counter = 0
	self.stopwords = set([x.strip() for x in open("stopwords_it.txt")])
	self.n = n
	self.max_words = max_words
	self.beginnings = []
	self.ngrams = {}

	if os.path.exists(self.brain_file):
	    fd = open(self.brain_file, 'rb')
	    self.markov = pickle.load(fd)
	    fd.close()
	else:
	    self.learn_from_file(self.sample_text)

    def tokenize(self, text):
	return text.split(" ")

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

    # hmbot
    def createProbabilityHash(self, words):
	numWords = len(words)
	wordCount = {}
	for word in words:
	    if wordCount.has_key(word):
		wordCount[word] += 1
	    else:
		wordCount[word] = 1

	for word in wordCount.keys():
	    wordCount[word] /= 1.0 * numWords
	return wordCount

	# mmm... XXX
	# calcolarlo in fase di gen()erazione ?
	# forse lento, ma almeno non perdo i valori originali

    def new_learn(self, text):
	tokens = self.tokenize(text)

	# PULIRE IL TESTO!

	if len(tokens) < self.n:
	    return

	# fare probability hash per questi ?
	beginning = tuple(tokens[:self.n])
	self.beginnings.append(beginning)

	for i in range(len(tokens) - self.n):
	    gram = tuple(tokens[i:i+self.n])
	    next = tokens[i+self.n]

	    if gram in self.ngrams:
		self.ngrams[gram].append(next)
	    else:
		self.ngrams[gram] = [next]

    def gen(self, sample=None, max_words=20):
	message = []

	if sample:
	    sample_words = sample.split()
	    sample_words = filter (lambda x: x not in self.stopwords,
		    sample_words)
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


class NewMarkov(object):
    def __init__(self, n=2, max=100):
	self.n = n
	#self.ngrams = {}
	self.ngrams = defaultdict(list)
	self.max = max
	self.beginnings = []
	self.stopwords = set([x.strip() for x in open("stopwords_it.txt")])

    def tokenize(self, text):
	return text.split(" ")

    def concatenate(self, elements):
	return ' '.join(elements)

    def feed(self, text):
	tokens = self.tokenize(text)

	if len(tokens) < self.n:
	    return

	beginning = tuple(tokens[:self.n])
	self.beginnings.append(beginning)

	for i in range(len(tokens) - self.n):
	    gram = tuple(tokens[i:i+self.n])
	    next = tokens[i+self.n]

	    self.ngrams[gram].append(next)
	    #if gram in self.ngrams:
	    #    self.ngrams[gram].append(next)
	    #else:
	    #    self.ngrams[gram] = [next]

    def pulisci(self, text):
	for pattern, repl in [
		(r'(?<![:;=])[\(\)]', " "),
		(r'["-]', " "),
		(r'\s+:\s', ": "),
		(r'\s+,\s', ", "),
		(r'\s+\.\s', ". "),
		(r'\s+\.+(?=\s|$)', '...'),
		(r' +', " "),
		(r'\.+', ".")
		]:
	    text = re.sub(pattern, repl, text)
	return text

    def generate(self):
	from random import choice

	current = choice(self.beginnings)
	output = list(current)

	for i in range(self.max):
	    if current in self.ngrams:
		possible_next = self.ngrams[current]
		next = choice(possible_next)
		output.append(next)
		current = tuple(output[-self.n:])
	    else:
		break
	output_str = self.concatenate(output)
	if not output_str.endswith('.'):
	    output_str += '.'

	return output_str

    def dump_brain(self):
	fd = open("brain_new.b", "wb")
	pickle.dump(self.ngrams, fd, pickle.HIGHEST_PROTOCOL)
	fd.close()

	fd = open("brain_new.n", "wb")
	pickle.dump(self.beginnings, fd, pickle.HIGHEST_PROTOCOL)
	fd.close()


def usage():
    print "%s: [-h] [-g \"sample text\"] [-i \"input file\"]" % ("markov.py")

if __name__ == '__main__':
    import getopt, sys
    import time

    # new
    p = NewMarkov(2)
    #fd = open('/Users/sand/Downloads/i_promes.txt', 'r')
    #for line in fd:
    #    for sentence in re.split("\.{1,3}(?:\n|\s+)", line):
    #        sentence = p.pulisci(sentence)
    #        p.feed(sentence)
    #fd.close()
    #fd = open('/Users/sand/Downloads/retro.log', 'r')


# NewMarkov
    #i = 0
    #fd = open('/tmp/porcoddio3.log', 'r')
    #print "Inizio alle: " + time.strftime("%H:%M %d-%m-%y")
    #for line in fd:
    #    p.feed(p.pulisci(line))
    #    i += 1
    #    if i >= 1000:
    #        print "1000"
    #        i = 0
    #fd.close()
    #print "Inizio il dump alle: " + time.strftime("%H:%M %d-%m-%y")
    #p.dump_brain()
    print "Inizio il load 1 del brain alle: " + time.strftime("%H:%M %d-%m-%y")
    fd = open("brain_new.b", "rb")
    p.ngrams = pickle.load(fd)
    fd.close()

    print "Inizio il load 2 del brain alle: " + time.strftime("%H:%M %d-%m-%y")
    fd = open("brain_new.n", "rb")
    p.beginnings = pickle.load(fd)
    fd.close()

    print "Inizio a generare tuo genero alle: " + time.strftime("%H:%M %d-%m-%y")
    for i in range(10):
        print p.generate()
        print "-"

    sys.exit()


    # end
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

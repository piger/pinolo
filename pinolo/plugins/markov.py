import os
import re
import codecs
import random
from collections import defaultdict
import cPickle as pickle

NEWLINE = '\r\n'

class Markov(object):
    def __init__(self, brainfile, n=2):
        self.brainfile = brainfile
        self.n = n
        self.beginnings = set()
        self.brain = defaultdict(list)

    def train_from_file(self, filename):
        data = None
        with codecs.open(filename, encoding='utf-8') as fd:
            data = fd.read()
        data = re.sub(r'(?:\r\n){2,}', NEWLINE + NEWLINE, data)
        phrases = data.split(NEWLINE + NEWLINE)
        phrases = [re.sub(r'(?:\r\n)+', ' ', x) for x in phrases]
        phrases = [re.sub(r'\s+', ' ', x) for x in phrases]

        # phrases = data.split("\n")
        for phrase in phrases:
            self.learn_phrase(phrase)

    def generate(self, max=100, from_beginnings=True):
        if from_beginnings:
            start = random.choice(list(self.beginnings))
        else:
            start = random.choice(self.brain.keys())

        message = list(start)
        print "start: %r" % (start,)
        gram = start
        for x in range(max):
            print "gram: %r" % (gram,)
            if not self.brain[gram]:
                print "%r non c'e', break" % (gram,)
                break
            print "-> %r" % (self.brain[gram])
            follow = random.choice(self.brain[gram])
            message.append(follow)

            if follow.endswith('.'): break
            gram = gram[1:] + (follow,)
        return u' '.join(message)

    def learn_phrase(self, phrase):
        words = phrase.split()

        if len(words) < self.n: return
        beginning = tuple(words[:self.n])
        self.beginnings.add(beginning)

        for i in range(len(words) - self.n):
            gram = tuple(words[i:i+self.n])
            follow = words[i+self.n]
            self.brain[gram].append(follow)
            # print "Learning %r for %r" % (follow, gram)

    def save(self):
        brain = (self.beginnings, self.brain)
        with open(self.brainfile, 'wb') as fd:
            pickle.dump(brain, fd)

    def load(self):
        with open(self.brainfile, 'rb') as fd:
            self.beginnings, self.brain = pickle.load(fd)


if __name__ == '__main__':
    import sys

    m = Markov("markovdb.pickle")
    # for arg in sys.argv[1:]:
    #     m.train_from_file(arg)
    m.load()
    print m.generate()
    # m.save()

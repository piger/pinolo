#!/usr/bin/env python
# http://code.google.com/p/kartoffelsalad/source/browse/trunk/lib/markov.py?r=9

from collections import defaultdict, deque
try:
    import cPickle as pickle
except ImportError:
    import pickle
import gzip
import os, sys, re
import random
import codecs

import logging
from pinolo.plugins import Plugin
from pinolo.plugins.quotes import Quote
from pinolo.casuale import get_random_reply
logger = logging.getLogger('pinolo.plugins.markov')

cleanups = [
    # nick: testo
    re.compile(r"^[^:]+:", re.UNICODE),
    # URL
    re.compile(r'''(?x)
    (?:
    \b\w+://\S+\b
    |
    (?:\w|\.)+
    \.\w{2,3}
    \/
    \S+
    \b)
    ''', re.UNICODE),
    # simboli
    re.compile(r"[\[\]\(\):;\"#]", re.UNICODE),
    # white space squeeze
    re.compile(r"\s{2,}", re.UNICODE),
]


class Markov(object):
    def __init__(self, n=2):
        self.n = n
        # self.tokens = defaultdict(lambda :defaultdict(int))
        self.tokens = {}
        self.keywords = defaultdict(set)

    def lex(self, sentence):
        """
        splitta per whitespace, toglie elementi vuoti.
        """
        words = [w.strip() for w in sentence.split()]
        words = [w for w in words if w]
        return words

    def cleanup(self, sentence):
        """
        toglie merda e IRC
        """
        for repl in cleanups:
            sentence = repl.sub(u"", sentence)

        return sentence

    def markov_sequence(self, tokens, context):
        """
        yielda (context), next_word

        (None, None) ciao
        (None, 'ciao') come
        ('ciao', 'come') stai
        ('come', 'stai') vaffanculo
        ('stai', 'vaffanculo') porcodio
        """
        # sequence = deque((None,) * context)
        sequence = deque(tuple(tokens[:context]))

        for token in tokens[context:]:
            yield tuple(sequence), token
            sequence.popleft()
            sequence.append(token)

    def learn(self, sentence):
        sentence = self.cleanup(sentence)
        if sentence is None:
            return
        tokens = self.lex(sentence)
        if len(tokens) < (self.n + 1):
            return

        for context, next_word in self.markov_sequence(tokens, self.n):
            if context not in self.tokens:
                self.tokens[context] = {}
                self.learn_keywords(context)
            weight = self.tokens[context].get(next_word, 0)
            self.tokens[context][next_word] = (weight + 1)
            # self.tokens[context][next_word] += 1

    def calc_keywords(self):
        for wp in self.tokens.keys():
            self.learn_keywords(wp)

    def learn_keywords(self, wp):
        for w in wp:
            self.keywords[w].add(wp)

    def find_keyword(self, words):
        for kw in words:
            if kw in self.keywords:
                return random.choice(list(self.keywords[kw]))

    def get_seed(self, words):
        random.shuffle(words)
        if words:
            seed = self.find_keyword(words)
            if seed:
                return seed
        return None

    def say(self, msg=None, max_words=50):
        if not self.tokens.keys():
            return None
        seed = None
        if msg:
            sample_words = msg.split()
            seed = self.get_seed(sample_words)

        if seed is None:
            starter = random.choice(self.tokens.keys())
            sequence = deque(tuple(starter))
            sentence = list(starter)
        else:
            print "uso seme!"
            sequence = deque(seed)
            sentence = list(seed)
        # sequence = deque((None,) * self.n)
        # sentence = []

        for i in xrange(max_words):
            context = tuple(sequence)
            try:
                next_dict = self.tokens[context]
            except KeyError:
                break
            total = sum(next_dict.itervalues())
            select = random.randint(1, total+1)

            for next_word, weight in next_dict.iteritems():
                total -= weight
                if total <= select:
                    sentence.append(next_word)
                    sequence.popleft()
                    sequence.append(next_word)
                    break

            if sentence[-1].endswith("."):
                break

        return u' '.join(sentence)

    def save(self, filename):
        f = gzip.GzipFile(filename, 'wb')
        data_to_save = (self.tokens, self.keywords)
        pickle.dump(data_to_save, f, -1)
        f.close()

    def load(self, filename):
        try:
            f = gzip.GzipFile(filename, 'rb')
        except IOError:
            return
        (self.tokens, self.keywords) = pickle.load(f)
        f.close()


class MarkovPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super(MarkovPlugin, self).__init__(*args, **kwargs)
        self.brainfile = os.path.join(self.head.config.datadir, 'markovdb.pickle')
        self.n = 2
        self.markov = Markov(self.n)
        self._savelimit = 0

    def activate(self):
        self.markov.load(self.brainfile)

    def save_brain(self):
        logger.info(u"Saving markov brain")
        self.markov.save(self.brainfile)

    def on_PRIVMSG(self, event):
        if event.user.nickname == event.client.current_nickname: return
        if not event.text: return

        if event.text.startswith(event.client.current_nickname):
            text = re.sub(r"^%s[:,]?\s+" % event.client.current_nickname,
                          u"", event.text)
            # prima impara, poi risponde
            # E INVECE QUESTA COSA E' DANNOSA!
            # self.markov.learn(text)
            reply = self.markov.say(text)
            if reply:
                event.reply(reply)
            else:
                event.reply(get_random_reply())
        else:
            self.markov.learn(event.text)
            self._savelimit += 1
            if self._savelimit >= 50:
                self.save_brain()
                self._savelimit = 0

    def on_cmd_savemarkov(self, event):
        if event.user.nickname == u"sand":
            self.save_brain()

if __name__ == "__main__":
    import sys

    m = MarkovGenerator(2)

    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            with codecs.open(filename, 'r', encoding='iso-8859-15') as fd:
                lines = fd.readlines()
                tot = len(lines)

                for i, line in zip(xrange(tot), lines):
                    print "\rLearning %d/%d" % (i, tot),
                    m.learn(line)

    while True:
        i = raw_input("> ")
        i = i.strip()

        if i == "quit": break

        if i:
            m.learn(i)
            reply = m.say(i)
        else:
            reply = m.say()

        print "@ %s" % (reply,)

# -*- coding: utf-8 -*-
"""
    pinolo.plugins.markov
    ~~~~~~~~~~~~~~~~~~~~~

    Markov chains for fun.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import os
import re
import random
import logging
import shutil
import cPickle as pickle
from collections import defaultdict, deque
from pinolo.plugins import Plugin


log = logging.getLogger(__name__)

cleanups = [
    # nickname: message -> message
    re.compile(r"^[^:]+:", re.UNICODE),

    # URL
    # xxx://yyyy
    # xxxx.yyy/zzzzzz
    re.compile(r'''(?x)
    (?:
    \b\w+://\S+\b
    |
    (?:\w|\.)+
    \.\w{2,3}
    \/
    \S+
    \b)''', re.UNICODE),

    # strip misc symbols
    re.compile(r"[\[\]\(\):;\"#]", re.UNICODE),

    # strip extra white spaces
    re.compile(r"\s{2,}", re.UNICODE),
]


class PersistentDict(dict):
    def __init__(self, filename, *args, **kwargs):
        self.filename = filename
        dict.__init__(self, *args, **kwargs)

    def save(self):
        tmpfile = self.filename + ".tmp"

        try:
            with open(tmpfile, "wb") as fd:
                data = pickle.dump(dict(self), fd, 2)
        except Exception, e:
            os.remove(tmpfile)
            raise
            
        shutil.move(tmpfile, self.filename)

    def load(self):
        if not os.path.exists(self.filename):
            return
            
        with open(self.filename, "rb") as fd:
            data = pickle.load(fd)
            self.update(data)


class MarkovBrain(object):
    def __init__(self, filename, context=2):
        self.context = context
        self.tokens = PersistentDict(filename)

    def load(self):
        log.info("Loading markov database")
        self.tokens.load()

    def save(self):
        log.info("Saving markov database")
        self.tokens.save()

    def lex(self, sentence):
        """Split a sentence"""
        words = [word.strip() for word in sentence.split() if len(word)]
        return words

    def cleanup(self, sentence):
        for regexp in cleanups:
            sentence = regexp.sub(u"", sentence)

        return sentence

    def _sequence(self, tokens, context):
        seq = deque(tuple(tokens[:context]))

        for token in tokens[context:]:
            yield tuple(seq), token
            seq.popleft()
            seq.append(token)

    def learn(self, sentence):
        sentence = self.cleanup(sentence)
        tokens = self.lex(sentence)
        if len(tokens) < (self.context + 1):
            return

        for context, next_word in self._sequence(tokens, self.context):
            self.tokens.setdefault(context, {})
            weight = self.tokens[context].get(next_word, 0)
            self.tokens[context][next_word] = (weight + 1)

    def start_from_seed(self, seed):
        tokens = self.lex(seed)
        if len(tokens) < (self.context + 1):
            return None

        for context, next_word in self._sequence(tokens, self.context):
            if context in self.tokens:
                return context

        return None

    def say(self, seed=None, max_words=50):
        # Empty database, we can't talk.
        if not self.tokens:
            return

        if seed:
            starter = self.start_from_seed(seed)
        else:
            starter = None

        if starter is None:
            starter = random.choice(self.tokens.keys())
        sequence = deque(tuple(starter))
        sentence = list(starter)

        for i in xrange(max_words):
            context = tuple(sequence)
            try:
                next_dict = self.tokens[context]
            except KeyError:
                break
            total = sum(next_dict.itervalues())
            select = random.randint(1, total + 1)

            for next_word, weight in next_dict.iteritems():
                total -= weight
                if total <= select:
                    sentence.append(next_word)
                    sequence.popleft()
                    sequence.append(next_word)
                    break

            if sentence[-1].endswith("."):
                break

        return u" ".join(sentence)


class MarkovPlugin(Plugin):

    def __init__(self, bot):
        super(MarkovPlugin, self).__init__(bot)
        self.db_file = os.path.join(self.bot.config['datadir'], "markov.pickle")
        self.markov = MarkovBrain(self.db_file)
        self._counter = 0
        self.verbosity = self.bot.config.get("markov_verbosity", 97)
        self.save_every = self.bot.config.get("markov_save_every", 50)

    def activate(self):
        self.markov.load()

    def deactivate(self):
        self.markov.save()
        
    def on_PRIVMSG(self, event):
        myname = event.client.current_nickname
        if (event.user.nickname == myname or not event.text):
            return

        if event.text.startswith(myname):
            # strip our nickname from the sentence
            text = re.sub(r"^%s[:,]?\s+" % myname, u"", event.text)
            reply = self.markov.say(text)
            if reply:
                event.reply(reply, prefix=False)
            else:
                event.reply(u"sono inibito e non so cosa dire")
        else:
            self.markov.learn(event.text)
            self._counter += 1
            if self._counter >= self.save_every:
                self._counter = 0
                self.markov.save()

            if random.randint(0, 100) >= self.verbosity:
                reply = self.markov.say(event.text)
                if reply:
                    event.reply(reply, prefix=False)

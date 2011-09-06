#!/usr/bin/env python
# http://code.google.com/p/kartoffelsalad/source/browse/trunk/lib/markov.py?r=9

import collections
try:
    import cPickle as pickle
except ImportError:
    import pickle
import gzip
import os, sys, re
import random
import codecs


PROPOSITION_SEPARATOR = r'[,:;]'
SENTENCE_TERMINATOR = r'[?!.]'
SMILEY = r"[:;8=][o\-']?[()\[\]/\\\?pPdD*$]+"
URL = r"\b\w+://\S*\b"

PROPOSITION_SEPARATOR_RE = re.compile(
    r'(?x)' + PROPOSITION_SEPARATOR, re.UNICODE)
SENTENCE_TERMINATOR_RE = re.compile(r'(?x)' + SENTENCE_TERMINATOR,
                                    re.UNICODE)
SPLIT_RE = re.compile(r'''(?x)
(
	%s | # An URL
        %s | # A Smiley
        %s | # Separators
        [()] | # Parenthesis
        %s | # foo
        \s+ | # white spaces
)''' % (URL, SMILEY, PROPOSITION_SEPARATOR, SENTENCE_TERMINATOR),
                      re.UNICODE)


class MarkovToken(object):
    def __init__(self, token):
        self.token = token
        if PROPOSITION_SEPARATOR_RE.match(token):
            self.space_before, self.end = False, False
        elif SENTENCE_TERMINATOR_RE.match(token):
            self.space_before, self.end = False, True
        else:
            self.space_before, self.end = True, False

    def output(self):
        if self.space_before:
            return [' ', self.token]
        else:
            return [self.token]

    def __str__(self):
        return self.token

    def __repr__(self):
        return "<token '%s'>" % self.token

    def __eq__(self, other):
        return (self.token == other.token and
                self.end == other.end and
                self.space_before == other.space_before)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return (hash(self.token) ^
                (hash(self.end) << 2) ^
                (hash(self.space_before) << 3))


class MarkovTokenFactory(object):
    def __init__(self):
        self.tokens = {}
        self.cnt = {}

    def __call__(self, s):
        self.cnt[s] = self.cnt.get(s, 0) + 1
        if s in self.tokens:
            return self.tokens[s]
        else:
            tok = MarkovToken(s)
            self.tokens[s] = tok
            return tok


class MarkovGenerator(object):
    def __init__(self, context=2):
        self.tokens = {}
        self.context = context
        self.factory = MarkovTokenFactory()

    def lex(self, sentence):
        """
        Splitta la frase
        """
        return [self.factory(x.strip()) for x
                in SPLIT_RE.split(sentence) if x.strip()]

    def markov_sequence(self, tokens, context):
        sequence = collections.deque((None,) * context)
        for token in tokens:
            yield tuple(sequence), token
            if token.end:
                sequence = collections.deque((None,) * context)
            else:
                sequence.popleft()
                sequence.append(token)

    def learn(self, sentence):
        tokens = self.lex(sentence)
        if len(tokens) < 4:
            return # !!!
        tokens[-1].end = True

        for context, next_word in self.markov_sequence(tokens, self.context):
            weight = self.tokens.setdefault(context, {}).setdefault(next_word, 0)
            self.tokens[context][next_word] = weight+1

    def say(self, start_word=None):
        sequence = collections.deque((None,) * self.context)
        if start_word:
            sequence.popleft()
            sequence.append(start_word)
            if tuple(sequence) not in self.tokens:
                return None

        sentence = []
        while not sentence or not sentence[-1].end:
            context = tuple(sequence)
            next_dict = self.tokens[context]
            total = sum(next_dict.itervalues())
            select = random.randint(1, total+1)

            for next_word, weight in next_dict.iteritems():
                total -= weight
                if total <= select:
                    sentence.append(next_word)
                    sequence.popleft()
                    sequence.append(next_word)
                    break
        return ''.join([''.join(x.output()) for x in sentence])

    def save(self, filename):
        f = gzip.GzipFile(filename, 'wb')
        data_to_save = (self.context, self.factory, self.tokens)
        pickle.dump(data_to_save, f, -1)
        f.close()

    def load(self, filename):
        try:
            f = gzip.GzipFile(filename, 'rb')
        except IOError:
            return
        (self.context, self.factory, self.tokens) = pickle.load(f)
        f.close()


class MarkovPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super(MarkovPlugin, self).__init__(*args, **kwargs)
        self.brainfile = os.path.join(self.head.config.datadir, 'markovdb.pickle')
        self.n = 2
        self.markov = MarkovGenerator(self.n)
        self._savelimit = 0

    def activate(self):
        self.markov.load(self.brainfile)

    def save_brain(self):
        self.markov.save(self.brainfile)

    def on_PRIVMSG(self, event):
        if event.user.nickname == event.client.current_nickname: return
        if not event.text: return

        if event.text.startswith(event.client.current_nickname):
            reply = self.markov.say()
            if reply:
                event.reply(reply)
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

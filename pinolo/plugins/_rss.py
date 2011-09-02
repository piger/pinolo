import os, re, sys
import pickle
import codecs
from collections import defaultdict
import time, datetime
import logging

import gevent
from gevent import socket
from gevent.pool import Pool
from gevent.core import timer
import gevent.queue

import feedparser
from pinolo.plugins import Plugin
from pinolo.utils import md5
from pinolo.plugins.google import gevent_HTTPHandler, gevent_HTTPConnection


HTTP_GET_TIMEOUT = float(60 * 2)
POOL_SIZE = 5
RSS_CRONTAB = float(60 * 10) # 10 min
logger = logging.getLogger('pinolo.plugins.rss')


class FakeConfig(object):
    def __init__(self):
        self.datadir = os.getcwd()

class FakeHead(object):
    def __init__(self):
        self.config = FakeConfig()


def title_from_url(url):
    match = re.match(r"http://([^/]+)/?", url)
    if match:
        return match.group(1).encode('utf-8', 'replace')
    else:
        return None

class RSSPlugin(Plugin):
    def __init__(self, head):
        super(RSSPlugin, self).__init__(head)
        self.pool = Pool(POOL_SIZE)
        self.queue = gevent.queue.Queue()
        self.feed_file = os.path.join(self.head.config.datadir, "rss.txt")
        self.cache_file = os.path.join(self.head.config.datadir, "rss.cache")
        self.seen_file = os.path.join(self.head.config.datadir, "rss.seen")
        self.feed_list = []
        self.feeds = {}
        self.seen_list = defaultdict(list)
        self.gtimer = None

    def activate(self):
        """
        - carica l'elenco dei feed da controllare.
        - carica la lista delle entry dei feed gia' viste.
        - carica la cache (parsata) dei feed.
        """
        self.load_rss_file()
        self.load_seen_file()
        self.load_cache()

        self.gtimer = timer(RSS_CRONTAB, self.job)

    def deactivate(self):
        if self.gtimer is not None:
            self.gtimer.cancel()

    def job(self):
        self.load_rss_file()
        self.fetch_all()
        self.print_feeds()
        self.gtimer = timer(RSS_CRONTAB, self.job) # reschedule

    def fetch_all(self):
        """
        Fetcha tutti i feed configurati con un pool di worker.
        """
        for feed in self.feed_list:
            self.pool.spawn(self.parse_feed, feed)
        self.pool.join()
        self.write_cache()

    def get_feed(self, url, etag=None, modified=None):
        """
        Fetcha un feed RSS usando sia `etag` che `HTTP Last-Modified`, con un timeout.
        """
        result = None
        with gevent.Timeout(HTTP_GET_TIMEOUT, False):
            result = feedparser.parse(url, handlers=[gevent_HTTPHandler],
                                      etag=etag, modified=modified)
        return result

    def parse_feed(self, url):
        """
        Scarica e parsa un feed RSS e lo inserisce nella cache.
        """
        title = title_from_url(url)
        # ERRORE
        if title is None:
            return
        cache = self.feeds.get(title, None)
        if cache is not None:
            feed = self.get_feed(url, cache.etag, cache.modified)
        else:
            feed = self.get_feed(url)

        if cache is None:
            self.feeds[title] = feed
        else:
            if (feed is not None and feed.status != 304):
                self.feeds[title] = feed

    def print_feeds(self):
        # published_parsed = time.struct_time, e puo' non esserci.

        for name, feed in self.feeds.items():
            # feed vuoto/errato.
            if feed is None: continue

            for entry in feed.entries:
                hashed = self.hash_entry(entry)
                if hashed is None: continue
                if not self.is_recent_entry(entry): continue

                if hashed not in self.seen_list[name]:
                    # e = self.format_entry(entry)
                    # print u"[%s] %s" % (name, e)

                    self.announce_entry(name, entry)

                    self.seen_list[name].append(hashed)
            # tiene solo gli ultimi 50 seen
            self.seen_list[name] = self.seen_list[name][-50:]

        self.write_seen_file()

    def announce_entry(self, name, entry):
        e = self.format_entry(entry)
        msg = u"[%s] %s" % (name, entry)

        for conn in self.head.connections.values():
            conn.msg_channels(msg)

    def hash_entry(self, entry):
        """
        Crea un hash dal titolo e dal link di una entry RSS.
        La entry non verra' considerata valida se sia `entry` che `link` sono `None`.
        """
        title = entry.get('title', None)
        link = entry.get('link', None)
        if (title is None and link is None):
            return None
        text = entry.title.encode('utf-8', 'replace') + '|' + entry.link.encode('utf-8', 'replace')
        return md5(text)

    def is_recent_entry(self, entry, max_days=7):
        """
        Ritorna `True` se una entry e' stata pubblicata negli ultimi `max_days` giorni;
        ritorna `True` anche se la data di pubblicazione e' assente o nel futuro.
        """
        today = datetime.datetime.today()
        published = entry.get('published_parsed', None)
        if published is None: return True
        published = datetime.datetime.fromtimestamp(time.mktime(published))
        # data nel futuro?
        if published > today: return True
        diff = today - published
        if diff.days < max_days:
            return True
        return False

    def format_entry(self, entry):
        title = entry.get('title', u'')
        link = entry.get('link', u'')
        return u"%s - %s" % (title, link)

    def write_pickle_data(self, filename, obj):
        """
        Scrive in un `filename` la versione pickle di un `obj`.
        """
        with open(filename, 'wb') as  fd:
            pickle.dump(obj, fd, pickle.HIGHEST_PROTOCOL)

    def load_pickle_data(self, filename, obj, raise_exc=False):
        """
        Carica da un `filename` pickle un `dict` e chiama `update` per `obj`.
        Di default non raisa Exception se ci sono errori nella lettura del file.
        """
        try:
            with open(filename, 'rb') as fd:
                data = pickle.load(fd)
                obj.update(data)
        except IOError, e:
            if raise_exc:
                raise

    # helper functions
    def write_cache(self):
        self.write_pickle_data(self.cache_file, self.feeds)

    def load_cache(self):
        self.load_pickle_data(self.cache_file, self.feeds)

    def load_seen_file(self):
        self.load_pickle_data(self.seen_file, self.seen_list)

    def write_seen_file(self):
        self.write_pickle_data(self.seen_file, self.seen_list)

    def load_rss_file(self):
        """
        Carica la lista dei feed rss da controllare.
        """
        try:
            with codecs.open(self.feed_file, 'r', encoding='utf-8') as fd:
                feeds = fd.readlines()
                feeds = [x.strip() for x in feeds]
                self.feed_list = feeds[:]
                # self.feed_list.extend(feeds)
        except IOError, e:
            raise

if __name__ == '__main__':
    head = FakeHead()

    p = RSSPlugin(head)
    p.activate()

    job = gevent.spawn(p.fetch_all)
    gevent.joinall([job])
    p.print_feeds()

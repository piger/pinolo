"""
BUG:

2011-09-06 12:41:48,256 pinolo.head INFO Importing plugin: pinolo.plugins.rss
Traceback (most recent call last):
  File "/home/sand/pinolo/env/bin/pinolo", line 9, in <module>
    load_entry_point('pinolo==0.1', 'console_scripts', 'pinolo')()
  File "/home/sand/pinolo_git/pinolo/main.py", line 32, in main
    head = BigHead(config)
  File "/home/sand/pinolo_git/pinolo/irc.py", line 523, in __init__
    self.activate_plugins()
  File "/home/sand/pinolo_git/pinolo/irc.py", line 553, in activate_plugins
    plugin.activate()
  File "/home/sand/pinolo_git/pinolo/plugins/rss.py", line 73, in activate
    self.load_cache()
  File "/home/sand/pinolo_git/pinolo/plugins/rss.py", line 227, in load_cache
    self.load_pickle_data(self.cache_file, self.feeds)
  File "/home/sand/pinolo_git/pinolo/plugins/rss.py", line 216, in load_pickle_data
    data = pickle.load(fd)
TypeError: ('__init__() takes exactly 4 arguments (2 given)', <class 'xml.sax._exceptions.SAXParseException'>, ('unclosed CDATA section',))

"""

import os, re
import codecs
from collections import defaultdict
import time, datetime
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle

import gevent
from gevent import socket
from gevent.pool import Pool
from gevent.core import timer
from gevent.queue import Queue
import feedparser

from pinolo.plugins import Plugin
from pinolo.utils import gevent_HTTPHandler
from pinolo.utils.text import md5

from pinolo import USER_AGENT
feedparser.USER_AGENT = USER_AGENT


HTTP_GET_TIMEOUT = float(60 * 2)
POOL_SIZE = 5
RSS_CRONTAB = float(60 * 10) # 10 min
# RSS_CRONTAB = float(10) # 10 sec / DEBUG
CACHE_FILE = "rss.cache"
SEEN_FILE = "rss.seen"
FEED_LIST_FILE = "rss.txt"
logger = logging.getLogger('pinolo.plugins.rss')


def title_from_url(url):
    match = re.match(r"http://([^/]+)/?", url)
    if match:
        return match.group(1).encode('utf-8', 'replace')
    else:
        raise RuntimeError("Invalid URL: %r" % (url,))

def the_fucking_date(entry):
    for key in ('updated_parsed', 'published_parsed', 'created_parsed'):
        if entry.has_key(key):
            return entry[key]
    return time.time()


class RSSPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super(RSSPlugin, self).__init__(*args, **kwargs)
        self.pool = Pool(POOL_SIZE)
        self.feed_file = os.path.join(self.head.config.datadir, FEED_LIST_FILE)
        self.cache_file = os.path.join(self.head.config.datadir, CACHE_FILE)
        self.seen_file = os.path.join(self.head.config.datadir, SEEN_FILE)
        self.feed_list = []
        self.feeds = {}
        self.seen_list = defaultdict(list)
        self.gtimer = None
        self.gjob = None

    def activate(self):
        """
        - carica l'elenco dei feed da controllare.
        - carica la lista delle entry dei feed gia' viste.
        - carica la cache (parsata) dei feed.
        """
        self.load_rss_file()
        if len(self.feed_list) == 0:
            return # no work to do

        self.load_seen_file()
        self.load_cache()

        # self.gtimer = timer(RSS_CRONTAB, self.job)
        self.gjob = gevent.spawn(self.job)

    def deactivate(self):
        if self.gtimer is not None:
            self.gtimer.cancel()

    def job(self):
        while True:
            gevent.sleep(RSS_CRONTAB)
            self.load_rss_file()
            self.fetch_all()
            self.print_feeds()
            # self.gtimer = timer(RSS_CRONTAB, self.job) # reschedule

    def fetch_all(self):
        """
        Fetcha tutti i feed configurati con un pool di worker.
        """
        for url in self.feed_list:
            name = title_from_url(url)
            logger.debug("Spawning greenlet for %s: %s" % (name, url))
            self.pool.spawn(self.parse_feed, url, name)
        logger.debug("Waiting for Pool() completion")
        self.pool.join()
        self.write_cache()

    def get_feed(self, url, etag=None, modified=None):
        """
        Fetcha un feed RSS usando sia `etag` che `HTTP Last-Modified`, con un timeout.
        """
        logger.debug(u"Fetching %s" % (url,))
        with gevent.Timeout(HTTP_GET_TIMEOUT, False):
            return feedparser.parse(url, handlers=[gevent_HTTPHandler], etag=etag,
                                    modified=modified)
        return None

    def parse_feed(self, url, name):
        """
        Scarica e parsa un feed RSS e lo inserisce nella cache.
        """
        cache = self.feeds.get(name, None)
        if cache is not None:
            etag = cache.get('etag', None)
            modified = cache.get('modified', None)
        else:
            etag, modified = (None, None)
        feed = self.get_feed(url, etag, modified)

        if feed is not None:
            status = feed.get('status', 200) # XXX
            if status != 304:
                self.feeds[name] = feed
            else:
                logger.debug("Feed %s already cached" % (name,))
        else:
            logger.warning("Timeout for feed %s (%s)" % (name, url))

    def print_feeds(self):
        # published_parsed = time.struct_time, e puo' non esserci.

        for name, feed in self.feeds.items():
            # feed vuoto/errato.
            if feed is None: continue

            entries = feed.entries[:]
            # sorta per data di pubblicazione
            sorted_entries = sorted(entries, key=lambda entry: the_fucking_date(entry))
            sorted_entries.reverse()

            for entry in sorted_entries[:5]:
                hashed = self.hash_entry(entry)
                if hashed is None: continue
                if not self.is_recent_entry(entry): continue

                if hashed not in self.seen_list[name]:
                    # logger.debug(u"Announcing feed: [%s] %r" % (name, entry))
                    self.announce_entry(name, entry)

                    self.seen_list[name].append(hashed)
            # tiene solo gli ultimi 50 seen
            self.seen_list[name] = self.seen_list[name][-50:]

        self.write_seen_file()

    def announce_entry(self, name, entry):
        e = self.format_entry(entry)
        msg = u"[%s] %s" % (name, e)

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
        published = the_fucking_date(entry)
        published = datetime.datetime.fromtimestamp(time.mktime(published))
        # data nel futuro?
        if published > today: return True
        diff = today - published
        if diff.days < max_days:
            return True
        return False

    def format_entry(self, entry):
        """
        Estrae titolo e URL da un feed e ritorna una stringa unicode.
        """
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

    def write_seen_file(self):
        self.write_pickle_data(self.seen_file, self.seen_list)

    def load_seen_file(self):
        self.load_pickle_data(self.seen_file, self.seen_list)

    def load_rss_file(self):
        """
        Carica la lista dei feed rss da controllare.
        """
        try:
            with codecs.open(self.feed_file, 'r', encoding='utf-8') as fd:
                feeds = fd.readlines()
                feeds = [x.strip() for x in feeds]
                feeds = [x for x in feeds if (x and not x.startswith('#'))]
                self.feed_list = feeds[:]
        except IOError, e:
            return

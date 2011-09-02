import os, re, sys
import pickle
import codecs

import gevent
from gevent import socket
from gevent.pool import Pool
import gevent.queue

import feedparser
from pinolo.plugins import Plugin
from pinolo.plugins.google import gevent_HTTPHandler, gevent_HTTPConnection

FEED_LIST = ["http://xkcd.com/rss.xml",
             "http://daringfireball.net/index.xml",
             "http://feeds.arstechnica.com/arstechnica/index",
             ]

HTTP_GET_TIMEOUT = float(60 * 2)

def title_from_url(url):
    match = re.match(r"http://([^/]+)/?", url)
    if match:
        return match.group(1)
    else:
        return None

class RSSPlugin(Plugin):
    def __init__(self, head):
        super(RSSPlugin, self).__init__(head)
        self.pool = Pool(5)
        self.queue = gevent.queue.Queue()
        self.feed_file = os.path.join(self.head.config.datadir, "rss.txt")
        self.cache_file = os.path.join(self.head.config.datadir, "rss.cache")
        self.feed_list = []
        self.feeds = {}

    def activate(self):
        self.load_rss_file()
        self.load_cache()

    def fetch_all(self):
        for feed in self.feed_list:
            self.pool.spawn(self.parse_feed, feed)
        self.pool.join()
        self.write_cache()

    def get_feed(self, url, etag=None, modified=None):
        result = None
        with gevent.Timeout(HTTP_GET_TIMEOUT, False):
            result = feedparser.parse(url, handlers=[gevent_HTTPHandler],
                                      etag=etag, modified=modified)
        return result

    def parse_feed(self, url):
        title = title_from_url(url)
        assert title is not None
        cache = self.feeds.get(title, None)
        if cache:
            feed = self.get_feed(url, cache.etag, cache.modified)
        else:
            feed = self.get_feed(url)

        if cache is None:
            self.feeds[title] = feed
        else:
            if feed is not None:
                self.feeds[title] = feed

    def write_cache(self):
        with open(self.cache_file, 'wb') as fd:
            pickle.dump(self.feeds, fd, pickle.HIGHEST_PROTOCOL)

    def load_cache(self):
        try:
            with open(self.cache_file, 'rb') as fd:
                data = pickle.load(fd)
                self.feeds.update(data)
        except IOError, e:
            return

    def load_rss_file(self):
        try:
            with codecs.open(self.feed_file, 'r', encoding='utf-8') as fd:
                feeds = fd.readlines()
                feeds = [x.strip() for x in feeds]
                self.feed_list.extend(feeds)
        except IOError, e:
            return

if __name__ == '__main__':
    p = MyFeedParser()
    p.load_cache()
    job = gevent.spawn(p.fetch_all)
    gevent.joinall([job])

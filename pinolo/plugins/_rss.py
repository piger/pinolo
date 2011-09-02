# import os
# from pinolo.plugins import Plugin

# class RssPlugin(Plugin):
#     def __init__(self, head):
#         super(RssPlugin, self).__init__(head)
#         self.rssfile = os.path.join(self.head.config.datadir, 'rss.txt')
#         self.feeds = []

#     def read_rss_file(self):
#         with open(self.rssfile) as fd:
#             self.feeds = [x for x in fd.readlines() if x.startswith('http')]

import os, re, sys
import json, pickle

import gevent
from gevent import socket
from gevent.pool import Pool
import gevent.queue

import feedparser
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

class MyFeedParser(object):
    def __init__(self):
        self.pool = Pool(10)
        self.queue = gevent.queue.Queue()
        self.datadir = os.getcwd()
        self.cache_file = os.path.join(os.getcwd(), "rss.dump")
        self.feeds = {}

    def fetch_all(self):
        for feed in FEED_LIST:
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

if __name__ == '__main__':
    p = MyFeedParser()
    p.load_cache()
    job = gevent.spawn(p.fetch_all)
    gevent.joinall([job])

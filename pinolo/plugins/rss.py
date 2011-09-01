import os
from pinolo.plugins import Plugin

class RssPlugin(Plugin):
    def __init__(self, head):
        super(RssPlugin, self).__init__(head)
        self.rssfile = os.path.join(self.head.config.datadir, 'rss.txt')
        self.feeds = []

    def read_rss_file(self):
        with open(self.rssfile) as fd:
            self.feeds = [x for x in fd.readlines() if x.startswith('http')]

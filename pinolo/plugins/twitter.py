# -*- coding: utf-8 -*-
"""
    pinolo.plugins.twitter
    ~~~~~~~~~~~~~~~~~~~~~~

    Twitter utilities

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import re
import requests
import logging
from pinolo.plugins import Plugin
from pinolo.tasks import Task


log = logging.getLogger()

# re to match a twitter status URL
r_twitter_status = re.compile(r"https?://twitter.com/(?P<user>[^/]+)/status/(?P<id>\d+)")

# API to retrieve a single tweet
json_status = "https://api.twitter.com/1/statuses/show.json?id={0}"


class TwitterTask(Task):
    def __init__(self, status_id, event, *args, **kwargs):
        self.status_id = status_id
        super(TwitterTask, self).__init__(event, *args, **kwargs)
        
    def run(self):
        log.debug("Fetching tweet %s" % self.status_id)
        response = requests.get(json_status.format(self.status_id))
        data = response.json()

        try:
            text = data["text"]
            username = data["user"]["screen_name"]
            name = data["user"]["name"]
        except KeyError:
            return

        reply = u'"%s" @%s: %s' % (name, username, text)
        self.put_results(self.event.reply, reply)
            

class TwitterPlugin(Plugin):
    def on_PRIVMSG(self, event):
        if event.user.nickname == event.client.current_nickname:
            return

        match = r_twitter_status.search(event.text)
        if match is None:
            return
        status_url = match.group()
        username = match.groupdict()["user"]
        status_id = match.groupdict()["id"]

        t = TwitterTask(status_id, event)
        t.start()

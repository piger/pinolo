# -*- coding: utf-8 -*-
"""
    pinolo.plugins.eztv
    ~~~~~~~~~~~~~~~~~~~

    Eztv search wrapper.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import re
import requests
from bs4 import BeautifulSoup
from pinolo.plugins import Plugin
from pinolo.tasks import Task


# URL with search form
SEARCH_URL = "http://eztv.it/search/"

# Maximum number of results returned
MAX_RESULTS = 6


class EztvTask(Task):
    def run(self):
        results = search_eztv(self.event.text)
        
        if not results:
            self.put_results(self.reply, u"Non ho trovato niente")
            return
        else:
            for result in results[:MAX_RESULTS]:
                self.put_results(self.event.client.notice,
                                 self.event.user.nickname,
                                 result)

def search_eztv(text):
    payload = {
        'SearchString1': text
    }

    r = requests.post(SEARCH_URL, data=payload)
    soup = BeautifulSoup(r.text)
    results = []

    for result in soup.findAll('tr', class_='forum_header_border'):
        amagnet = result.find('a', href=re.compile(r'^magnet'))
        magnet_url = None
        if amagnet is not None and 'href' in amagnet.attrs:
            magnet_url = amagnet.attrs['href']

        info = result.find('a', class_='epinfo')
        if info is None:
            # XXX risultato non valido!
            continue

        desc = info.text
        if magnet_url:
            desc = u"%s - %s" % (info.text, magnet_url)
        else:
            desc = info.text

        results.append(desc)

    return results


class EztvPlugin(Plugin):

    COMMAND_ALIASES = {
        'eztv': 'eztv_search'
    }

    def on_cmd_eztv_search(self, event):
        if not event.text:
            return

        t = EztvTask(event)
        t.start()

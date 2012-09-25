# -*- coding: utf-8 -*-
"""eztv.it search plugin"""
import re
import requests
from bs4 import BeautifulSoup
from pinolo.plugins import Plugin


SEARCH_URL = "http://eztv.it/search/"
MAX_RESULTS = 6


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
        results = search_eztv(event.text)

        if not results:
            event.reply(u"Non ho trovato una cippa di cazzo, sory")
            return

        for result in results:
            event.reply(result)

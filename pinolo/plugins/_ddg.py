# -*- coding: utf-8 -*-
"""
    pinolo.plugins.ddg
    ~~~~~~~~~~~~~~~~~~

    DuckDuckGo API client (WIP).

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import urllib
import json
import requests
from pinolo.plugins import Plugin
from pinolo.tasks import Task
from pinolo import USER_AGENT


# URL for search API
SEARCH_URL = "http://api.duckduckgo.com/"

MAX_RESULTS = 5

SEARCH_LANG = "it"

TYPES = {
    u'A': u'article',
    u'D': u'disambiguation',
    u'C': u'category',
    u'N': u'name',
    u'E': u'exclusive',
    u'': u'nothing',
}


def search_ddg(text):
    query = urllib.urlencode({
        'q': text,
        'format': 'json',
        'no_html': '1',
        'no_redirect': '1',
    })

    payload = dict(q=text, format="json", no_html="1", no_redirect="1")
    response = requests.get(SEARCH_URL, params=payload)
    data = response.json()

    r = json.loads(data)
    # toglie i value 'empty'
    # pr = dict((k, v) for k,v in r.items() if v)

    # tolgo i value vuoti o nulli e i value duplicati.
    # mi serve perche' il dict con i risultati contiene per alcuni campi sia la
    # versione plaintext che quella HTML, e io uso `no_html`.
    results = {}
    for k, v in r.items():
        if type(v) is list:
            if len(v) > 0:
                results[k] = r.pop(k)
            else:
                r.pop(k)
    rr = dict((v, k) for k, v in r.items() if v)
    results.update(dict((k, v) for v, k in rr.items()))

    if 'Results' in results:
        results['Results'] = results['Results'][:5]

    if 'Type' in results:
        t = results['Type']
        results['Type'] = TYPES.get(t, u'')

    return results


class DuckDuckGoPlugin(Plugin):
    COMMAND_ALIASES = {
        'ddg': 'duckduckgo',
    }

    def on_cmd_duckduckgo(self, event):
        if not event.text:
            return
        results = search_ddg(event.text)
        if not len(results.keys()):
            event.reply(u"DDG busta de piscio")
        else:
            for k, v in results.items():
                event.reply(u"%s: %s" % (k, v))

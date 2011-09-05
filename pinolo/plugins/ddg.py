# -*- coding: utf-8 -*-

import urllib
import json
from pinolo.plugins import Plugin
from pinolo.utils import gevent_url_open

SEARCH_URL = "http://api.duckduckgo.com/"
MAX_RESULTS = 5
SEARCH_LANG = "it"

def search_ddg(text):
    query = urllib.urlencode({
        'q': text,
        'format': 'json',
        'no_html': '1',
        'no_redirect': '1',
    })

    url = SEARCH_URL + "?" + query
    response = gevent_url_open(url)
    headers = response.headers
    if 'content-type' in headers:
        encoding = headers['content-type'].split('charset=')[-1]
        data = unicode(response.read(), encoding)
    else:
        data = response.read()
        data.decode('utf-8', 'replace')
    r = json.loads(data)

    print r

    if 'Results' in r:
        results = r['Results']
    else:
        results = []
    t = r.get('Type', u'')

    return { 'type': t, 'results': results }

class DuckDuckGoPlugin(Plugin):
    COMMAND_ALIASES = {
        'ddg': 'duckduckgo',
    }

    def on_cmd_duckduckgo(self, event):
        if not event.text: return
        results = search_ddg(event.text)
        event.reply(u"type: %s" % results['type'])
        for result in results['results']:
            event.reply(u"%s %s" % (result['FirstURL'], result['Text']))

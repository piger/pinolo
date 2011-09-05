# -*- coding: utf-8 -*-

import json
import urllib
import logging
logger = logging.getLogger('pinolo.plugins.google')

from pinolo.plugins import Plugin
from pinolo.utils import gevent_url_open, strip_html

MAX_RESULTS = 5
SEARCH_LANG = 'it'
SEARCH_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0"


def parse_result(result):
    title = strip_html(result['titleNoFormatting'])
    url = result['url']
    content = strip_html(result['content'])
    return (title, url, content)

def search_google(query_string):
    query = urllib.urlencode({
        'q': query_string,
        'rsz': MAX_RESULTS,
        'hl': SEARCH_LANG,
    })

    url = SEARCH_URL + "&" + query
    response = gevent_url_open(url)

    headers = response.headers
    encoding = headers['content-type'].split('charset=')[-1]
    data = unicode(response.read(), encoding)
    json_data = json.loads(data)

    if 'responseData' in json_data:
        if 'results' in json_data['responseData']:
            return [parse_result(x)
                    for x in json_data['responseData']['results']]
    return [] # error

def shorten_url(api_key, url):
    service_url = "https://www.googleapis.com/urlshortener/v1/url?key=" + api_key
    headers = [('Content-Type', 'application/json'), ]
    data = json.dumps({ 'longUrl': url })
    response = gevent_url_open(service_url, headers, data)

    headers = response.headers
    if 'content-type' in headers:
        encoding = headers['content-type'].split('charset=')[-1]
        data = unicode(response.read(), encoding)
    else:
        data = response.read()
        data.decode('utf-8', 'replace')
    r = json.loads(data)

    if u'id' in r:
        return (r.get(u"longUrl", u""), r.get(u"id", u""))
    else:
        return None

class GooglePlugin(Plugin):

    COMMAND_ALIASES = {
        'g': 'google',
        'gs': 'google_shortener',
    }

    def on_cmd_google(self, event):
        if not event.text: return
        results = search_google(event.text)
        if not results:
            event.reply(u"Non so niente, non ho visto niente.")
        else:
            for title, url, content in results:
                event.reply(u"\"%s\" %s - %s" % (title, url, content))

    def on_cmd_google_shortener(self, event):
        if not event.text: return
        result = shorten_url(self.head.config.googleapi, event.text)
        if result:
            long_url, short_url = result
            event.reply(u"%s -> %s" % (long_url, short_url))
        else:
            event.reply(u"Non ho shortato, me so' shittato addosso instead.")

if __name__ == '__main__':
    import sys
    print search_google(' '.join(sys.argv[1:]))

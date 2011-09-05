# -*- coding: utf-8 -*-

import re
import htmlentitydefs
import json
import urllib, urllib2
import httplib

from pinolo import USER_AGENT
from pinolo.plugins import Plugin
from pinolo.utils import gevent_HTTPConnection, gevent_HTTPHandler

MAX_RESULTS = 5
SEARCH_LANG = 'it'
SEARCH_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0"

def strip_html(text):
    """
    From: http://effbot.org/zone/re-sub.htm#unescape-html
    """

    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass

        elif text[:1] == "&":
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)

def gevent_url_fetch(url):
    request = urllib2.Request(url)
    request.add_header('User-Agent', USER_AGENT)
    opener = urllib2.build_opener(gevent_HTTPHandler)
    response = opener.open(request)
    return response

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
    response = gevent_url_fetch(url)

    headers = response.headers
    encoding = headers['content-type'].split('charset=')[-1]
    data = unicode(response.read(), encoding)
    json_data = json.loads(data)

    if 'responseData' in json_data:
        if 'results' in json_data['responseData']:
            return [parse_result(x)
                    for x in json_data['responseData']['results']]
    return [] # error

class GooglePlugin(Plugin):

    COMMAND_ALIASES = {
        'g': 'google',
    }

    def on_cmd_google(self, event):
        if not event.text: return
        results = search_google(event.text)
        if not results:
            event.reply(u"Non so niente, non ho visto niente.")
        else:
            for title, url, content in results:
                event.reply(u"\"%s\" %s - %s" % (title, url, content))

if __name__ == '__main__':
    import sys
    print search_google(' '.join(sys.argv[1:]))

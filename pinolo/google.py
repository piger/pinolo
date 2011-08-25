# -*- coding: utf-8 -*-

# import gevent
# from gevent import monkey
# monkey.patch_all()

import re
import htmlentitydefs
import json
import urllib, urllib2

import httplib
import socket
from gevent import socket as cosocket

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

class gevent_HTTPConnection(httplib.HTTPConnection):
    """
    Per evitare monkey.patch_all():
    http://groups.google.com/group/gevent/browse_thread/thread/c20181cb066ee97e?fwc=2&pli=1
    """
    def connect(self):
        if self.timeout is socket._GLOBAL_DEFAULT_TIMEOUT:
            timeout = cosocket._GLOBAL_DEFAULT_TIMEOUT
        else:
            timeout = self.timeout
        self.sock = cosocket.create_connection((self.host, self.port), timeout)

class gevent_HTTPHandler(urllib2.HTTPHandler):
    def http_open(self, request):
        return self.do_open(gevent_HTTPConnection, request)

def gevent_url_fetch(url):
    opener = urllib2.build_opener(gevent_HTTPHandler)
    resp = opener.open(url)
    return resp.headers, resp

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
    headers, response = gevent_url_fetch(url)
    encoding = headers['content-type'].split('charset=')[-1]
    data = unicode(response.read(), encoding)
    json_data = json.loads(data)

    if 'responseData' in json_data:
        if 'results' in json_data['responseData']:
            return [parse_result(x)
                    for x in json_data['responseData']['results']]
    return [] # error

if __name__ == '__main__':
    import sys
    print search_google(' '.join(sys.argv[1:]))

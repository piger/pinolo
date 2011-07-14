#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Search plugin

http://code.google.com/apis/websearch/docs/reference.html#_intro_fonje
"""

import urllib
import simplejson
from BeautifulSoup import BeautifulSoup

from pinolo.main import CommandPlugin, PluginActivationError
from pinolo import MyOptionParser, OptionParserError

MAX_RESULTS = 5
SEARCH_LANG = 'it'
SEARCH_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0"
# G_USER_IP = "127.0.0.1"
# G_API_KEY = ""

def utf8(text):
    return text.encode('utf-8', 'strict')

class SearchResult(object):
    def __init__(self, result):
        self.title = utf8(result['titleNoFormatting'])
        self.url = utf8(result['url'])
        self.content = utf8(strip_html(result['content']))

    def __repr__(self):
        return "%s - %s {%s}" % (self.title, self.url, self.content)

def strip_html(blob):
    s = BeautifulSoup(blob, convertEntities=BeautifulSoup.HTML_ENTITIES)
    page = u''.join(s.findAll(text=True))
    return page

def query_google(search):
    query = urllib.urlencode({
        'q': search,
        'rsz': MAX_RESULTS,
        'hl': SEARCH_LANG,
    })

    url = SEARCH_URL + "&" + query
    search_results = urllib.urlopen(url)
    data = search_results.read()
    json = simplejson.loads(data)

    results = json['responseData']['results']
    return results


class SearchCommand(CommandPlugin):
    search_opt = MyOptionParser(usage="!g <query string>")

    def handle(self, request):
        if request.command in ['google', 'g']:
            if not request.arguments:
                request.reply("Questa domanda non ha una risposta")
                return

            search_string = ' '.join(request.arguments)
            results = query_google(search_string)

            for result in results:
                r = SearchResult(result)
                request.reply("%s: %s {%s}" % (r.title, r.url, r.content))

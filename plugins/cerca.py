#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Search plugin

http://code.google.com/apis/websearch/docs/reference.html#_intro_fonje
"""

import re
import urllib
import simplejson
from BeautifulSoup import BeautifulSoup
import htmlentitydefs

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
        self.title = result['titleNoFormatting']
        self.url = result['url']
        self.content = strip_html(result['content'])

    def as_string(self):
        result = "%s - %s {%s}" % (self.title, self.url, self.content)
        return result
        #return result.encode('utf-8', 'replace')

def strip_html(blob):
    s = BeautifulSoup(blob, convertEntities=BeautifulSoup.HTML_ENTITIES)
    page = u''.join(s.findAll(text=True))
    return page

# from: http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass

        return text
    return re.sub("&#?\w+;", fixup, text)

def new_strip_html(text):
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
                    return unicode(entity, 'iso-8859-1')
        return text
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)


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

    def activate(self, config=None):
        super(SearchCommand, self).activate()

    def handle(self, request):
        if request.command in ['google', 'g']:
            if not request.arguments:
                request.reply("Questa domanda non ha una risposta")
                return

            search_string = ' '.join(request.arguments)
            results = query_google(search_string)

            for result in results:
                r = SearchResult(result)
                request.reply(r.as_string())

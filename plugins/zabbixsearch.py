#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unicodedata
from datetime import datetime

import xapian
from twisted.python import log
from pubsub import Publisher as pubsub

from pinolo.main import CommandPlugin, PluginActivationError


xapian_author = 0
xapian_date = 1
xapian_quote_id = 2

DATABASE_DIR = os.path.abspath('./xapiandb')


class ZabbixSearch(CommandPlugin):
    def __init__(self):
        self.database = xapian.WritableDatabase(DATABASE_DIR,
                                                xapian.DB_CREATE_OR_OPEN)
        self.indexer = xapian.TermGenerator()
        self.stemmer = xapian.Stem('italian')
        self.indexer.set_stemmer(self.stemmer)
        self.enquire = xapian.Enquire(self.database)

        self.qp = xapian.QueryParser()
        self.qp.set_stemmer(self.stemmer)
        self.qp.set_database(self.database)
        self.qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)

    def search(self, query_string, start=0, stop=5):

        query = self.qp.parse_query(query_string)
        self.enquire.set_query(query)
        matches = self.enquire.get_mset(start, stop)
        return matches

    def add_quote(self, quote):
        author = unicodedata.normalize('NFKC', quote.author)
        text = unicodedata.normalize('NFKC', quote.quote)

        doc = xapian.Document()
        doc.set_data(text)
        doc.add_value(xapian_author, author)
        doc.add_value(xapian_date, quote.creation_date.strftime('%Y%m%d%H%M%S'))
        doc.add_value(xapian_quote_id, quote.id)

        self.indexer.set_document(doc)
        self.indexer.index_text(text)

        self.database.add_document(doc)

    def handle(self, client, command, arguments, info, channel, reply_to):
        pass

    def activate(self):
        super(ZabbixSearch, self).activate()
        log.msg("Attivato ZabbixSearch")
        pubsub.subscribe(self.fai, 'get_quote')

    def fai(self, event):
        log.msg("Farei? %r" % event.data)

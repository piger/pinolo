#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '/Users/sand/dev/pinolo')

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


class XapianSearch(CommandPlugin):
    def activate(self, config):
        super(XapianSearch, self).activate()

        # PROVA
        pubsub.subscribe(self.fai, 'get_quote')
        pubsub.subscribe(self.add_quote_signal, 'add_quote')

        self.database = xapian.WritableDatabase(config.xapian_db,
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

    def add_quote_signal(self, event):
        log.msg("Adding a quote from a signal")
        self.add_quote(event.data)

    def add_quote(self, quote):
        author = unicodedata.normalize('NFKC', quote.author)
        text = unicodedata.normalize('NFKC', quote.quote)

        doc = xapian.Document()
        doc.set_data(text)
        doc.add_value(xapian_author, author)
        doc.add_value(xapian_date, quote.creation_date.strftime('%Y%m%d%H%M%S'))
        doc.add_value(xapian_quote_id, str(quote.id))

        self.indexer.set_document(doc)
        self.indexer.index_text(text)

        self.database.add_document(doc)

    def handle(self, request):
        if request.command in [ 'search' ]:
            if not request.arguments:
                request.reply("Cioe' bho io non lo so")
                return

            matches = self.search(' '.join(request.arguments))
            num_results = matches.get_matches_estimated()

            if not num_results:
                request.reply("Non abbiamo trovato un cazzo! (cit.)")
                return

            request.reply("%i results found" % num_results)

            for match in matches:
                text = unicode(match.document.get_data(), 'utf-8', 'replace')
                id = match.document.get_value(xapian_quote_id)
                id = int(id)
                request.reply("%i: %i%% %i, %s" % (match.rank + 1, match.percent,
                                                   id, text))

    def fai(self, event):
        log.msg("Hanno chiesto get_quote di %i" % event.data.id)


if __name__ == '__main__':
    # This should ONLY be used to populate a NEW xapian database with an
    # existing Quotes database.

    # This will read all quotes from the database specified on the command line
    # and write the Xapian database.

    # Usage: python plugins/xapiansearch.py <quotes.db> <xapian_db_dir>

    from quotedb import Quote
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    class FakeConfig(object):
        def __init__(self, xapian_db):
            self.xapian_db = xapian_db

    if len(sys.argv) > 2:
        db_file = 'sqlite:///' + sys.argv[1]
        xapian_db = sys.argv[2]
        cfg = FakeConfig(xapian_db)

        x = XapianSearch()
        x.activate(cfg)

        engine = create_engine(db_file, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        print "Adding quotes: ",

        for quote in session.query(Quote).all():
            x.add_quote(quote)
            print ".",
            sys.stdout.flush()

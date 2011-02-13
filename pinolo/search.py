#!/usr/bin/env python

import os
import sys
import re
import xapian
from datetime import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle
import unicodedata

from db import SqlFairy, Quote

ROOTDIR = os.path.realpath(os.path.dirname(__file__))
DATABASE = os.path.join(ROOTDIR, 'xapiandb')

xapian_author = 0
xapian_date = 1
xapian_quote_id = 2

class Searcher(object):
    def __init__(self, databasedir=DATABASE):
        self.databasedir = databasedir

        self.database = xapian.WritableDatabase(self.databasedir,
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

        #print "%i results found." % matches.get_matches_estimated()
        #print "Results 1-%i:" % matches.size()

        #for m in matches:
        #    quote_text = m.document.get_data()
        #    quote_author = m.document.get_value(xapian_author)
        #    quote_creation_date = m.document.get_value(xapian_date)
        #    quote_creation_date = datetime.strptime(quote_creation_date, '%Y%m%d%H%M%S')
        #    quote_date = quote_creation_date.strftime('%A, %B %d, %Y %I:%M%p')

        #    print "%i: %i%% docid=%i [author: %s (%s) - %s" % (m.rank +1,
        #                                                       m.percent,
        #                                                       m.docid,
        #                                                       quote_author,
        #                                                       quote_date,
        #                                                       quote_text)

        return matches


def main(create=False):
    s = SqlFairy("/Users/sand/quotes.db")
    database = xapian.WritableDatabase(DATABASE, xapian.DB_CREATE_OR_OPEN)

    indexer = xapian.TermGenerator()
    stemmer = xapian.Stem('italian')
    indexer.set_stemmer(stemmer)

    if create:
        quotes = s.session.query(Quote).order_by(Quote.id).all()
        for quote in quotes:
            #q_author = quote.author.encode('utf-8')
            q_author = unicodedata.normalize('NFKC', quote.author)
            #q_text = quote.quote.encode('utf-8')
            q_text = unicodedata.normalize('NFKC', quote.quote)

            doc = xapian.Document()

            doc.set_data(q_text)
            doc.add_value(xapian_author, q_author)
            doc.add_value(xapian_date, quote.creation_date.strftime('%Y%m%d%H%M%S'))
            doc.add_value(xapian_quote_id, quote.id)

            indexer.set_document(doc)
            indexer.index_text(q_text)

            database.add_document(doc)

    enquire = xapian.Enquire(database)
    query_string = " ".join(sys.argv[1:])

    qp = xapian.QueryParser()
    qp.set_stemmer(stemmer)
    qp.set_database(database)
    qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
    query = qp.parse_query(query_string)
    print "Parsed query: %s" % str(query)

    enquire.set_query(query)
    matches = enquire.get_mset(0, 10)

    print "%i results found." % matches.get_matches_estimated()
    print "Results 1-%i:" % matches.size()

    for m in matches:
        quote_text = m.document.get_data()
        #quote_text = quote_text.encode('utf-8')
        quote_author = m.document.get_value(xapian_author)
        quote_creation_date = m.document.get_value(xapian_date)
        quote_creation_date = datetime.strptime(quote_creation_date, '%Y%m%d%H%M%S')
        quote_date = quote_creation_date.strftime('%A, %B %d, %Y %I:%M%p')

        print "%i: %i%% docid=%i [author: %s (%s) - %s" % (m.rank +1,
                                                           m.percent,
                                                           m.docid,
                                                           quote_author,
                                                           quote_date,
                                                           quote_text)



if __name__ == '__main__':
    main(create=True)

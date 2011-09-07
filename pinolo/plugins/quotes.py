# -*- encoding: utf-8 -*-

import logging
import os
from datetime import datetime
import unicodedata

from pinolo.plugins import Plugin
from pinolo.database import Base, Session

from sqlalchemy import *
from sqlalchemy.orm.exc import NoResultFound
import xapian

logger = logging.getLogger('pinolo.plugins.quotes')

xapian_author = 0
xapian_date = 1
xapian_quote_id = 2

DEFAULT_SEARCH_FLAGS = (
    xapian.QueryParser.FLAG_DEFAULT |
    # supporto per AND, OR e parentesi
    xapian.QueryParser.FLAG_BOOLEAN |
    # supporto per testo quotato
    xapian.QueryParser.FLAG_PHRASE |
    # supporto per + e -
    xapian.QueryParser.FLAG_LOVEHATE |
    # supporto per AND, OR etc senza che siano SCRITTI IN CAPS
    xapian.QueryParser.FLAG_BOOLEAN_ANY_CASE |
    # supporto per parole troncate, tipo "porcod*"
    xapian.QueryParser.FLAG_WILDCARD
)


class Quote(Base):
    """
    Quote database description.
    """

    __tablename__ = 'quotes'

    id = Column(Integer, primary_key=True)
    quote = Column(Unicode(10000))
    author = Column(Unicode(1000))
    creation_date = Column(DateTime)
    karma = Column(Integer)

    def __init__(self, quote, author, creation_date=None, karma=0):
        self.quote = quote
        self.author = author
        if creation_date is None:
            self.creation_date = datetime.now()
        else:
            self.creation_date = creation_date
        self.karma = karma

    def __repr__(self):
        return u"<Quote('%s', '%s', '%s', '%i')>" % (self.author, self.quote,
                                                     self.creation_date, self.karma)

class QuotesPlugin(Plugin):

    COMMAND_ALIASES = {
        'addq': 'addquote',
        'q': 'quote',
        'qq': 'search',
    }

    def __init__(self, head):
        super(QuotesPlugin, self).__init__(head)
        self.xap_db_path = os.path.join(self.head.config.datadir, 'xapian')

    def activate(self):
        self.xap_indexer = xapian.TermGenerator()
        self.xap_stemmer = xapian.Stem('italian')
        self.xap_indexer.set_stemmer(self.xap_stemmer)

        self.create_xapian_datadir()

        self.xap_qp = xapian.QueryParser()
        self.xap_qp.set_stemmer(self.xap_stemmer)
        self.xap_qp.set_database(self.xap_database)
        self.xap_qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)

    def create_xapian_datadir(self):
        if os.path.exists(self.xap_db_path):
            create = False
        else:
            create = True
        self.xap_database = xapian.WritableDatabase(self.xap_db_path, xapian.DB_CREATE_OR_OPEN)

        if create:
            logger.info(u"Populating XAPIAN database")

            for quote in Quote.query.all():
                self.xapian_add_quote(quote, flush=False)

            self.xap_database.flush()
            logger.info(u"XAPIAN database populated.")

    def xapian_add_quote(self, quote, flush=True):
        logger.debug(u"Adding quote to XAPIAN engine: %s" % quote.quote)
        author = unicodedata.normalize('NFKC', quote.author)
        text = unicodedata.normalize('NFKC', quote.quote)

        doc = xapian.Document()
        doc.set_data(text)
        doc.add_value(xapian_author, author)
        doc.add_value(xapian_date, quote.creation_date.strftime('%Y%m%d%H%M%S'))
        doc.add_value(xapian_quote_id, str(quote.id))

        self.xap_indexer.set_document(doc)
        self.xap_indexer.index_text(text)
        self.xap_database.add_document(doc)
        if flush:
            self.xap_database.flush()

    def random_quote(self):
        quote = Quote.query.order_by(func.random()).first()
        return quote

    def quote_by_id(self, id):
        quote = Quote.query.filter_by(id=id).one()
        return quote


    # EVENTS

    def on_cmd_quote(self, event):
        if event.text:
            try:
                req = int(event.text)
                quote = self.quote_by_id(req)
            except (NoResultFound, ValueError):
                event.reply(u"l'ID non e' valido.")
                return
        else:
            quote = self.random_quote()

        if quote is not None:
            event.reply(u"(%i) %s" % (quote.id, quote.quote))
        else:
            event.reply(u"DB vuoto?")

    def on_cmd_addquote(self, event):
        if not event.text:
            event.reply(u"Errore! Te pare zi'?")
            return

        quote = Quote(quote=event.text, author=event.user.nickname)
        session = Session()
        session.add(quote)
        session.commit()

        self.xapian_add_quote(quote)
        event.reply(u"%s: Ho stipato la %i!" % (event.user.nickname, quote.id))

    def on_cmd_search(self, event):
        limit = 5

        if not event.text:
            event.reply(u"Eh si, cerco stocazzo.")
            return

        query = self.xap_qp.parse_query(event.text.encode('utf-8'),
                                        DEFAULT_SEARCH_FLAGS)
        enquire = xapian.Enquire(self.xap_database)
        enquire.set_query(query)
        matches = enquire.get_mset(0, limit)

        num_results = matches.get_matches_estimated()

        if not num_results:
            event.reply(u"Non abbiamo trovato un cazzo! (cit.)")
            return

        event.reply(u"ho trovato %i %s:" % (num_results,
                                            u"faccenda" if num_results == 1 else u"faccende"))

        for match in matches:
            text = unicode(match.document.get_data(), 'utf-8', 'replace')
            id = match.document.get_value(xapian_quote_id)
            id = int(id)
            event.reply(u"%i: %i%% %i, %s" % (match.rank + 1, match.percent, id, text))

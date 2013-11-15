# -*- coding: utf-8 -*-
import os
import re
import logging
from datetime import datetime
from sqlalchemy import (Column, Integer, Unicode, DateTime, func)
from sqlalchemy.orm.exc import NoResultFound
from whoosh import index
from whoosh.fields import (Schema, TEXT, NUMERIC, DATETIME)
from whoosh.analysis import (PyStemmerFilter, RegexTokenizer, LowercaseFilter,
                             StopFilter, CharsetFilter)
from whoosh.qparser import QueryParser
from whoosh.index import EmptyIndexError
from whoosh.support.charset import accent_map
from pinolo.plugins import Plugin
from pinolo.database import Base, Session


log = logging.getLogger(__name__)

stoplist = []
stem_lang = "italian"
my_analyzer = RegexTokenizer() \
              | LowercaseFilter() \
              | StopFilter(stoplist=stoplist) \
              | CharsetFilter(accent_map) \
              | PyStemmerFilter(stem_lang)

r_search_page = re.compile(r"--(?P<page>\d+)\s+")


class Quote(Base):
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
        return u"<Quote('%r', '%r', '%r', '%i')>" % (self.author, self.quote,
                                                     self.creation_date, self.karma)


class QuotesPlugin(Plugin):

    COMMAND_ALIASES = {
        'addq': 'addquote',
        'q': 'quote',
        'qq': 'search',
        's': 'search',
    }
    
    def __init__(self, bot, config, enabled=True):
        super(QuotesPlugin, self).__init__(bot, config, enabled)
        self.to_be_indexed = False
        self.ix = None
        self.init_whoosh()

    def init_whoosh(self):
        idx_dir = self.config['db_path']
        log.info("Opening Whoosh database %s", idx_dir)

        if os.path.exists(idx_dir):
            try:
                self.ix = index.open_dir(idx_dir)
            except EmptyIndexError:
                self.create_index()
        else:
            self.create_index()

    def create_index(self):
        idx_dir = self.config['db_path']
        schema = Schema(author=TEXT(), 
                        quote=TEXT(analyzer=my_analyzer),
                        creation_date=DATETIME(),
                        id=NUMERIC(stored=True))
        if not os.path.exists(idx_dir):
            os.mkdir(idx_dir)
        self.ix = index.create_in(idx_dir, schema)
        self.to_be_indexed = True

    def activate(self):
        if not self.to_be_indexed:
            return

        log.info("Indexing the quotes database for the first time")
        session = Session()
        writer = self.ix.writer()
        for quote in session.query(Quote).all():
            self.index_quote(quote, writer, commit=False)
        writer.commit()

    def deactivate(self):
        pass

    def index_quote(self, quote, writer=None, commit=True):
        if writer is None:
            writer = self.ix.writer()
        writer.add_document(id=quote.id, author=quote.author,
                            quote=quote.quote, 
                            creation_date=quote.creation_date)
        if commit:
            writer.commit()

    def on_cmd_addquote(self, event):
        if not event.text:
            event.reply(u"NO!")
            return

        quote = Quote(quote=event.text, author=event.user.nickname)
        session = Session()
        session.add(quote)
        session.commit()

        self.index_quote(quote)
        event.reply(u"Ho aggiunto la %d" % quote.id)

    def on_cmd_search(self, event):
        limit = 5
        
        if not event.text:
            event.reply(u"Eh sì, stocazzo")
            return

        match = r_search_page.match(event.text)
        if match:
            page = int(match.group(1))
        else:
            page = 1

        session = Session()
        results_id = []
        with self.ix.searcher() as searcher:
            qp = QueryParser("quote", self.ix.schema)
            query = qp.parse(event.text)
            # results = searcher.search(query, limit=limit)
            try:
                results = searcher.search_page(query, page, pagelen=limit)
            except ValueError:
                event.reply(u"La tua ricerca mi ha inibito il cervello")
                return

            found = results.scored_length()
            if not found:
                event.reply(u"Non ho trovato un cazzo!")
                return

            event.reply(u"Risultati pagina %d di %d, risultati %d-%d di %d" % (
                results.pagenum, results.pagecount, results.offset + 1,
                results.offset + results.pagelen + 1, len(results)))

            for result in results:
                results_id.append(result['id'])

        for quote in session.query(Quote).filter(Quote.id.in_(results_id)).all():
            event.reply(u"(%i) %s" % (quote.id, quote.quote))
            

    def on_cmd_quote(self, event):
        if event.text:
            try:
                req = int(event.text)
                quote = self.quote_by_id(req)
            except (NoResultFound, ValueError):
                event.reply(u"Te stai a sbajà")
                return
        else:
            quote = self.random_quote()

        if quote is not None:
            event.reply(u"(%i) %s" % (quote.id, quote.quote))

    def quote_by_id(self, _id):
        return Quote.query.filter_by(id=_id).one()

    def random_quote(self):
        return Quote.query.order_by(func.random()).first()

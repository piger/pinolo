# -*- coding: utf-8 -*-
import os
import re
import logging
import unicodedata
from datetime import datetime
from sqlalchemy import (Column, Integer, Unicode, DateTime, func)
from sqlalchemy.orm.exc import NoResultFound
from whoosh import index
from whoosh.fields import (Schema, TEXT, KEYWORD, NUMERIC, DATETIME)
from whoosh.analysis import PyStemmerFilter, StemmingAnalyzer
from whoosh.qparser import QueryParser
from pinolo.plugins import Plugin
from pinolo.database import Base, Session


log = logging.getLogger(__name__)

# RegexTokenizer LowercaseFilter StopFilter StemmingFilter
from whoosh.analysis import (RegexTokenizer, LowercaseFilter, StopFilter, PyStemmerFilter, CharsetFilter)
from whoosh.support.charset import accent_map

stoplist = []
stem_lang = "italian"
my_analyzer = RegexTokenizer() | LowercaseFilter() | StopFilter(stoplist=stoplist) | CharsetFilter(accent_map) | PyStemmerFilter(stem_lang)


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
        self.init_whoosh()

    def init_whoosh(self):
        log.info("Opening Whoosh database %s" % self.config["db_path"])
        if os.path.exists(self.config["db_path"]):
            self.ix = index.open_dir(self.config["db_path"])
        else:
            schema = Schema(author=TEXT(), 
                            quote=TEXT(analyzer=my_analyzer),
                            creation_date=DATETIME(),
                            id=NUMERIC(stored=True))
            os.mkdir(self.config["db_path"])
            self.ix = index.create_in(self.config["db_path"], schema)
            self.to_be_indexed = True

    def activate(self):
        if not self.to_be_indexed:
            return

        log.info("Indexing the quotes database for the first time")
        session = Session()
        writer = self.ix.writer()
        for quote in Session.query(Quote).all():
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

        for quote in Session.query(Quote).filter(Quote.id.in_(results_id)).all():
            event.reply(u"(%i) %s" % (quote.id, quote.quote))
            

    def on_cmd_quote(self, event):
        if event.text:
            try:
                req = int(event.text)
                quote = self.quote_by_id(req)
            except (NoResultFound, ValueError), e:
                event.reply(u"Te stai a sbajà")
                return
        else:
            quote = self.random_quote()

        if quote is not None:
            event.reply(u"(%i) %s" % (quote.id, quote.quote))

    def quote_by_id(self, id):
        return Quote.query.filter_by(id=id).one()

    def random_quote(self):
        return Quote.query.order_by(func.random()).first()

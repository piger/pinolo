#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quotes plugin

This is the first attempt to write pinolo features as pure python plugins.
Implementing the basic commands for getting quotes from the database and
creating new ones.

This requires SQLAlchemy.
"""

import os
import re
from datetime import datetime
from pprint import pprint
# from optparse import OptionParser

from twisted.python import log

from sqlalchemy import Column, Integer, DateTime, Unicode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func

from pubsub import Publisher as pubsub

from pinolo.main import CommandPlugin, PluginActivationError
from pinolo import MyOptionParser, OptionParserError

DATABASE = os.path.abspath('./quotes.db')

Base = declarative_base()
metadata = Base.metadata


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
        return u"<Quote('%s', '%s', '%s', '%i')>" % (self.author,
                                                     self.quote,
                                                     self.creation_date,
                                                     self.karma)

class Prova(CommandPlugin):
    """This is a test plugin implementing Quotes"""

    quote_opt = MyOptionParser(usage="!quote - !q : [options] [id]")

    def __init__(self):
        super(Prova, self).__init__()
        self.db_file = 'sqlite:///' + DATABASE
        self.engine = None
        self.session = None

    def activate(self):
        super(Prova, self).activate()
        try:
            self.engine = create_engine(self.db_file, echo=False)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        except Exception, e:
            raise PluginActivationError(e)


    def handle(self, request):
        # def handle(self, client, command, arguments, irc_user, channel, reply_to):
        """Generic IRC command handler"""

        if request.command in [ 'q', 'quote' ]:
            try:
                (options, args) = self.quote_opt.parse_args(request.arguments)
            except OptionParserError, e:
                request.reply(str(e))
            else:
                self.get_quote(request, options, args)

        elif request.command in [ 'addq', 'addquote', 'add' ]:
            request.reply("Non ce l'ho, me deve arriva'")

    def get_quote(self, request, options, arguments):
        query = self.session.query(Quote)

        if arguments:
            id = arguments.pop(0)

            if re.match(r'\d+$', id):
                query = query.filter_by(id=id)
            else:
                request.reply("Invalid ID")
                return

        else:
            query = query.order_by(func.random())

        if options.contains:
            # SA vuole parametri 'unicode' per colonne 'unicode' ;)
            filter_str = unicode(options.contains, 'utf-8', 'replace')
            query = query.filter(Quote.quote.contains(filter_str))

        result = query.first()
        if result is None:
            request.reply("Not found")
        else:
            request.reply("%i, %s" % (result.id, result.quote))


    def OLD_get_quote(self, id=None):
        """Get a quote from database, either random or specific with ``id``.

        Returns:
        A ``Quote`` object.
        """

        if id is None:
            q = self.session.query(Quote).order_by(
                func.random()
            ).limit(1).first()
        else:
            q = self.session.query(Quote).filter_by(
                id=id
            ).first()

        pubsub.sendMessage('get_quote', data=q)

        return q

Prova.quote_opt.add_option("-c", "--contains", dest="contains",
                           help="Prende un Quote che contiene TESTO",
                           metavar="TESTO")

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
from datetime import datetime

from twisted.python import log

from sqlalchemy import Column, Integer, DateTime, Unicode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func
from pprint import pprint

from pinolo.main import CommandPlugin, PluginActivationError

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

    def handle(self, client, command, arguments, info, channel, reply_to):
        """Generic IRC command handler"""

        if command in [ 'q', 'quote' ]:
            quote = self.get_quote()
            client.reply(reply_to, quote.quote)

    def get_quote(self, id=None):
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

        return q

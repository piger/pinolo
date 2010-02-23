#!/usr/bin/env python

import time

import utils

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, \
DateTime, Binary, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relation, backref, mapper
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func

Base = declarative_base()

# PASTE

class Quote(Base):
    __tablename__ = 'quotes'

    id = Column(Integer, primary_key=True)
    quote = Column(String)
    author = Column(String)
    data = Column(String)

    def __init__(self, quote, author, data=None):
        self.quote = quote
        self.author = author
        if data is None:
            data = time.strftime("%Y-%m-%d")
        self.data = data

    def __repr__(self):
        return "<Quote('%s', '%s', '%s')>" % (self.quote,
                                              self.author,
                                              self.data)


class SqlFairy():
    def __init__(self, filename=None):
        if filename is None:
            filename = 'quotes.db'
        db_url = 'sqlite:///' + filename
        self.engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_quote(self, author, txt):
        txt = utils.unicodize(txt)
        try:
            q = Quote(txt, author)
            self.session.add(q)
            self.session.commit()
            return q.id
        except:
            self.session.rollback()
            return None

    def random_quote(self):
        q = self.session.query(Quote).order_by(func.random()).limit(1)
        return (q.id, q.quote)

    def get_quote(self, search_id=None):
        if search_id is not None:
            q = self.session.query(Quote).filter_by(id=search_id).first()
        else:
            q =\
            self.session.query(Quote).order_by(func.random()).limit(1).first()

        return q

    def search_quote(self, pattern, limit=5):
        # safe check contro me stesso
        if limit > 10:
            log.msg("limit > 10 e' MALE")
            return None

        q = self.session.query(Quote).filter(Quote.quote.like(pattern))
        result_found = len(q.all())

        return result_found, q[:limit]

# END PASTE

class DbHelper:
    """DbHelper
    Questa classe contiene le funzioni per manipolare il DB di quotes.
    """
    def __init__(self, quotes_db='quotes.db', markov_db='brain_new.db'):
        self.quotes_db = quotes_db
        self.markov_db = markov_db
        self.cursors = {}

        self.q_dbconn = sqlite.connect(self.quotes_db)
        self.m_dbconn = sqlite.connect(self.markov_db)
        self.q_dbconn.text_factory = str
        self.m_dbconn.text_factory = str

        self.cursors['quotes'] = self.q_dbconn.cursor()
        self.cursors['markov'] = self.m_dbconn.cursor()

    def get_quote(self, id=None):
        """Ritorna una quote casuale o una specifica se gli passi l'ID."""
        try:
            if id:
                self.cursors['quotes'].execute("SELECT quoteid,quote FROM quotes WHERE quoteid = ?", (id,))
            else:
                self.cursors['quotes'].execute("SELECT quoteid,quote FROM quotes ORDER BY RANDOM() LIMIT 1")

        except OverflowError:
            log.msg("get_quote() con parametro non numerico")
            return (0, "ma che davero davero?")

        return self.cursors['quotes'].fetchone()

    def add_quote(self, author, quote):
        """Inserisce una quote nel DB.
        ritorna un intero che rappresenta l'ID (SQL) della quote.
        """
        now = time.strftime("%Y-%m-%d")
        quote = utils.unicodize(quote)
        self.cursors['quotes'].execute("INSERT INTO quotes(quote, author, data) VALUES (?, ?, ?)", (quote, author, now))
        self.q_dbconn.commit()
        return self.cursors['quotes'].lastrowid

    def search_quote(self, pattern):
        pattern = utils.unicodize(pattern)
        pattern = '%' + pattern.strip() + '%'
        t = (pattern,)
        self.cursors['quotes'].execute("SELECT quoteid,quote FROM quotes WHERE quote LIKE ? ORDER BY RANDOM()", t)
        return self.cursors['quotes'].fetchall()

    def shutdown(self):
        self.q_dbconn.close()

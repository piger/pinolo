#!/usr/bin/env python

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, \
DateTime, Binary, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relation, backref, mapper
from sqlalchemy.ext.declarative import declarative_base
from pprint import pprint

Base = declarative_base()

class Quote(Base):
    __tablename__ = 'quotes'

    quoteid = Column(Integer, primary_key=True)
    quote = Column(String)
    author = Column(String)
    data = Column(String)

    def __init__(self, quote, author, data):
        self.quote = quote
        self.author = author
        self.data = data

    def __repr__(self):
        return "<Quote('%s', '%s', '%s')>" % (self.quote,
                                              self.author,
                                              self.data)

# Valid SQLite URL forms are:
#  sqlite:///:memory: (or, sqlite://)
#  sqlite:///relative/path/to/file.db
#  sqlite:////absolute/path/to/file.db
engine = create_engine('sqlite:///quotes.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
# pprint(session.query(Quote).filter_by(quoteid=100).first())
q = session.query(Quote).filter_by(quoteid=300).first()
print "(%s) %s" % (q.author, q.quote)

new = Quote('test', 'sand', '01/04/1984 13:00')
session.add(new)
pprint(session.dirty)
pprint(session.new)

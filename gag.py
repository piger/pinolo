#!/usr/bin/env python

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, \
DateTime, Binary, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relation, backref, mapper
from sqlalchemy.ext.declarative import declarative_base
from pprint import pprint
import random
from sqlalchemy.sql.functions import random as sql_random
from sqlalchemy import func

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

tot = random.randrange(0, session.query(Quote).count())
print tot
gnagna = session.query(Quote)[tot]
print gnagna.quote

print "GAG!"
#semental = session.query(Quote).order_by(sql_random()).limit(1)
semental = session.query(Quote).order_by(func.random()).limit(1)
# pprint(semental.first())

print "GOO!"
for mm in semental:
    print mm.quote


qq = session.query(Quote)
moo = qq.filter(Quote.quote.like('%porcoddio%'))
for r in moo[:5]:
    print "."

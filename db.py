# Copyright (C) 2010-2011 sand <daniel@spatof.org>
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation and/or
#    other materials provided with the distribution.
# 3. The name of the author nor the names of its contributors may be used to
#    endorse or promote products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import time
import utils

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, \
        DateTime, Binary, Text, Unicode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relation, backref, mapper
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func
from pprint import pprint
import datetime

Base = declarative_base()
metadata = Base.metadata


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
            self.creation_date = datetime.datetime.now()
        else:
            self.creation_date = creation_date
        self.karma = karma

    def __repr__(self):
        return u"<NewQuote('%s', '%s', '%s', '%i')>" % (self.author,
                                                        self.quote,
                                                        self.creation_date,
                                                        self.karma)
class SqlFairy():
    """La classe che gestisce l'interazione con il database."""

    def __init__(self, filename='./quotes.db'):
        sqlite_prefix = 'sqlite:///'
        db_url = sqlite_prefix + filename

        self.engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_quote(self, author, text):
        """Aggiunge una quote al database.

        `txt` deve essere Unicode!
        """

        assert type(author) == unicode, "author must be unicode!"
        assert type(text) == unicode, "text must be unicode!"

        try:
            new_quote = Quote(quote=text, author=author)
            self.session.add(new_quote)
            self.session.commit()
            return new_quote.id
        except Exception, e:
            self.session.rollback()
            print "ERROR: add_quote:", str(e)
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



if __name__ == "__main__":
    s = SqlFairy("/Users/sand/quotes.db")
    import sys
    quote = s.get_quote(sys.argv[1])
    print quote.quote.encode('utf-8')
    #metadata.create_all(s.engine)

    #quotes = s.session.query(NewQuote).order_by(NewQuote.id).all()
    #for quote in quotes:
    #    new_quote = Quote(quote=quote.quote,
    #                      author=quote.author,
    #                      creation_date=quote.creation_date,
    #                      karma=quote.karma)
    #    s.session.add(new_quote)
    #s.session.commit()
    ##quotes = s.session.query(Quote).order_by(Quote.id).limit(10)
    #for quote in quotes:
    #    author = quote.author
    #    text = quote.quote

    #    try:
    #        data = datetime.datetime.strptime(quote.data, "%H:%M:%S %d/%m/%Y")
    #    except ValueError:
    #        try:
    #            data = datetime.datetime.strptime(quote.data, "%d/%m/%Y %H:%M")
    #        except ValueError:
    #            data = datetime.datetime.strptime(quote.data, "%Y-%m-%d")

    #    #print text.encode('utf-8'), data.hour

    #    new_quote = NewQuote(quote=text, author=author, creation_date=data)
    #    s.session.add(new_quote)

    #s.session.commit()

    # DATE FIXER

    #quotes = s.session.query(NewQuote).order_by(NewQuote.creation_date).all()
    #wrong_date = datetime.datetime.strptime("1970-01-01 01:00:00", "%Y-%m-%d %H:%M:%S")
    #for quote in quotes:
    #    if quote.creation_date != wrong_date:
    #        print quote.creation_date

#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#from pysqlite2 import dbapi2 as sqlite
import sqlite3 as sqlite
from time import strftime
import utils

# (a, b) -> c, d, e, f, g, h
# SELECT word FROM followers WHERE follow_word = (a, b)

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
        now = strftime("%Y-%m-%d")
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

if __name__ == '__main__':
    import sys

    dbh = DbHelper("quotes.db")
    #dbh.add_quote("sand", u"perché porcoddio")
    if len(sys.argv) > 1:
        pattern = ' '.join(sys.argv[1:])
        print "cerco: \"%s\"" % (pattern)
        dbh.search_quote(pattern)
    else:
        print dbh.get_quote(1335)
        res = dbh.get_quote(1335)[0]
        print res
        text = u"perché porcoddio"
        assert res == text.encode('utf-8')

#!/usr/bin/env python

#from pysqlite2 import dbapi2 as sqlite
import sqlite3 as sqlite

class DbHelper:
    """DbHelper
    Questa classe contiene le funzioni per manipolare il DB di quotes.
    """

    def __init__(self, filename):
	self.filename = filename
	self.dbconn = sqlite.connect(self.filename)
	self.dbconn.text_factory = str
	self.dbcursor = self.dbconn.cursor()

    def search_quote(self, pattern):
	self.dbcursor.execute('SELECT quoteid,quote FROM quotes WHERE quote LIKE ? ORDER BY RANDOM()', ('%' + pattern.strip() + '%',))
	res = self.dbcursor.fetchall()
	return res

    def get_quote(self, id=None):
	"""Ritorna una quote casuale o una specifica se gli passi l'ID."""
	try:
	    if id:
		self.dbcursor.execute("SELECT quote FROM quotes WHERE quoteid = ?", (id,))
	    else:
		self.dbcursor.execute("SELECT quoteid,quote FROM quotes ORDER BY RANDOM() LIMIT 1")

	except OverflowError:
	    print "overlofw error!"
	    return None

	return self.dbcursor.fetchone()

    def add_quote(self, author, quote):
	"""Inserisce una quote nel DB.
	ritorna un intero che rappresenta l'ID (SQL) della quote.
	"""
	now = strftime("%Y-%m-%d")
	self.dbcursor.execute("INSERT INTO quotes(quote, author, data) VALUES (?, ?, ?)", (quote, author, now))
	self.dbconn.commit()
	return self.dbcursor.lastrowid

    def shutdown(self):
	self.dbconn.close()

if __name__ == '__main__':
    print "Hi!"
    # test
    dbh = DbHelper("quotes.db")
    print dbh.get_quote()

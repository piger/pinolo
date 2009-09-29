#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

#from pysqlite2 import dbapi2 as sqlite
import sqlite3 as sqlite
from time import strftime
import utils

class DbHelper:
    """DbHelper
    Questa classe contiene le funzioni per manipolare il DB di quotes.
    """

    def __init__(self, filename):
	self.filename = filename
	self.dbconn = sqlite.connect(self.filename)
	self.dbconn.text_factory = str
	self.dbcursor = self.dbconn.cursor()

    def get_quote(self, id=None):
	"""Ritorna una quote casuale o una specifica se gli passi l'ID."""
	try:
	    if id:
		self.dbcursor.execute("SELECT quoteid,quote FROM quotes WHERE quoteid = ?", (id,))
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
	quote = utils.unicodize(quote)
	self.dbcursor.execute("INSERT INTO quotes(quote, author, data) VALUES (?, ?, ?)", (quote, author, now))
	self.dbconn.commit()
	return self.dbcursor.lastrowid

    def search_quote(self, pattern):
	pattern = utils.unicodize(pattern)
	pattern = '%' + pattern.strip() + '%'
	t = (pattern,)
	self.dbcursor.execute("SELECT quoteid,quote FROM quotes WHERE quote LIKE ? ORDER BY RANDOM()", t)
	results = self.dbcursor.fetchall()
	if len(results) < 1:
	    print "La tua ricerca non ha dato risultati."
	else:
	    for result in results:
		print "%i: %s" % (result[0], result[1])

    def shutdown(self):
	self.dbconn.close()

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

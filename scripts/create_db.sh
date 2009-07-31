#!/bin/sh

cat quotes.db.schema | sqlite3 quotes.db

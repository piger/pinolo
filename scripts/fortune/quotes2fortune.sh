#!/bin/sh

QUOTESDB="../../quotes.db"

if [ ! -e ${QUOTESDB} ]; then
    echo "Cannot find a valid quotes database!"
    exit 1
fi

sqlite3 -line ${QUOTESDB} "SELECT quote FROM quotes" | perl ./fai.pl > fortune.pinolo
strfile fortune.pinolo

# -*- coding: utf-8 -*-
"""
    pinolo.database
    ~~~~~~~~~~~~~~~

    SQLAlchemy database initialization.

    :copyright: (c) 2013 Daniel Kertesz
    :license: BSD, see LICENSE for more details.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

Session = scoped_session(sessionmaker())

Base = declarative_base()
Base.query = Session.query_property()

def init_db(uri, echo=False):
    log.info("Initializing database at %s", uri)
    engine = create_engine(uri, echo=echo)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    return engine

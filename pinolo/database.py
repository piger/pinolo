from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

Session = scoped_session(sessionmaker())

Base = declarative_base()
Base.query = Session.query_property()

def init_db(uri, echo=False):
    engine = create_engine(uri, echo=echo)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)

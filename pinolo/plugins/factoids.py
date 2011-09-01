# -*- encoding: utf-8 -*-

import logging
import re
import random

from pinolo.plugins import Plugin
from pinolo.database import Base, Session

from sqlalchemy import *
from sqlalchemy.orm.exc import NoResultFound

re_domanda = re.compile(r"""
(?:(?:cosa|chi|che|cos')\s*(?:e'|è|é)\s+)?
([^?]+)\s*\?+
""", re.UNICODE | re.VERBOSE)
re_subjfact = re.compile(r"\s*(?:e'|è|é)\s*", re.UNICODE)

risposte = ("pare sia", "e'", "a mio dire e'", "secondo le scritture e'",
            "me pare tipo", "e' tipo", "assomiglia a",
            "m'hanno detto che e'",)


class Fact(Base):
    __tablename__ = 'facts'

    id = Column(Integer, primary_key=True)
    subject = Column(String, unique=True)
    meaning = Column(String)
    previous_meaning = Column(String, nullable=True)

    def __init__(self, subject, meaning):
        self.subject = subject
        self.meaning = meaning
        self.previous_meaning = None

    def __repr__(self):
        return u"<Fact(%r -> %r)>" % (self.subject, self.meaning)


class FactsPlugin(Plugin):
    def on_PRIVMSG(self, event):
        if event.user.nickname == event.client.current_nickname: return
        match = re_domanda.search(event.text)
        if match:
            self.domanda(event, match.group(1).strip())
        else:
            try:
                subject, fact = re_subjfact.split(event.text, 1)
            except ValueError:
                return
            else:
                if subject and fact: # evito subject = ""
                    self.apprendi(event, subject, fact)

    def domanda(self, event, subject):
        fact = Fact.query.filter_by(subject=subject).first()
        if fact:
            event.reply(u"%s %s %s" % (subject, random.choice(risposte), fact.meaning))

    def apprendi(self, event, subject, meaning):
        session = Session()
        fact = Fact.query.filter_by(subject=subject).first()
        if fact:
            fact.previous_meaning = fact.meaning
            fact.meaning = meaning
        else:
            fact = Fact(subject, meaning)
            session.add(fact)
        session.commit()

    def undo(self, subject):
        session = Session()
        fact = Fact.query.filter_by(subject=subject).first()
        if fact:
            if fact.previous_meaning:
                meaning = fact.meaning
                fact.meaning = fact.previous_meaning
                fact.previous_meaning = meaning
                session.commit()

    def on_cmd_fundo(self, event):
        if event.text:
            self.undo(event.text)

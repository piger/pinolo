# -*- encoding: utf-8 -*-

import logging
import re

from pinolo.plugins import Plugin
from pinolo.database import Base, Session

from sqlalchemy import *
from sqlalchemy.orm.exc import NoResultFound

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
        if event.user.nickname == event.client.nickname: return
        match = re.search(r"(?:cosa|chi)\s+e'\s+(.*)\?$", event.text)
        if match:
            self.domanda(event, match.group(1).strip())
        else:
            match = re.search(r"(.*?)\s+e'\s+(.*)", event.text)
            if match:
                self.apprendi(event, match.group(1), match.group(2))

    def domanda(self, event, subject):
        fact = Fact.query.filter_by(subject=subject).first()
        if fact:
            event.reply(u"%s pare sia %s" % (subject, fact.meaning))

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

    def on_cmd_undo(self, event):
        if event.text:
            self.undo(event.text)

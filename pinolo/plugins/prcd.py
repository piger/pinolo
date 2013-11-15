# -*- coding: utf-8 -*-
import codecs
import pkg_resources
import logging
import random
from pinolo.cowsay import cowsay
from pinolo.plugins import Plugin


log = logging.getLogger('pinolo.prcd')

PRCD_FILES = [
    'prcd_cri.txt',
    'prcd_dio.txt',
    'prcd_ges.txt',
    'prcd_mad.txt',
    'prcd_mtc.txt',
    'prcd_pap.txt',
    'prcd_vsf.txt',
]


def read_prcd_files():
    """
    Legge i file PRCD e popola un `dict`.
    NOTA: pkg_resource vuole i path separati da '/' a prescindere dal sistema
    operativo in uso.
    """
    moccoli = {}
    for filename in PRCD_FILES:
        category = filename[filename.index('_')+1:filename.index('.')]
        category = unicode(category, 'utf-8', 'replace')
        # fd = pkg_resources.resource_stream(__name__, "data/prcd/%s" % filename)
        path = pkg_resources.resource_filename("pinolo", "data/prcd/%s" % filename)
        log.debug("Opening PRCD file %s", path)
        try:
            with codecs.open(path, "rb", encoding="utf-8") as fd:
                lines = fd.readlines()
                moccoli[category] = lines
        except IOError:
            pass

    return moccoli


class PrcdPlugin(Plugin):
    def activate(self):
        self.moccoli = read_prcd_files()
        self.prcd_categories = self.moccoli.keys()
        if not self.moccoli or not self.prcd_categories:
            log.error("No PRCD files, deactivating prcd plugin")
            self.enabled = False

    def moccolo_random(self, category=None):
        if not category:
            category = random.choice(self.prcd_categories)
        return (category, random.choice(self.moccoli[category]))

    def on_cmd_prcd(self, event):
        cat, moccolo = self.moccolo_random(event.text or None)
        if not moccolo:
            event.reply(u"La categoria non esiste!")
        else:
            event.reply(u"(%s) %s" % (cat, moccolo))

    def on_cmd_prcd_list(self, event):
        event.reply(u', '.join(self.prcd_categories))

    def on_cmd_PRCD(self, event):
        _, moccolo = self.moccolo_random(event.text or None)
        if not moccolo:
            event.reply(u"La categoria non esiste!")
        else:
            output = cowsay(moccolo)
            for line in output:
                if line:
                    event.reply(line, prefix=False)

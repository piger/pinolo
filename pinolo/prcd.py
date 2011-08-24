# -*- encoding: utf-8 -*-

import codecs
import pkg_resources
import logging
import random

logger = logging.getLogger('pinolo.prcd')

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

    logger.debug("Reading PRCD files")
    for filename in PRCD_FILES:
        category = filename[filename.index('_')+1:filename.index('.')]
        # fd = pkg_resources.resource_stream(__name__, "data/prcd/%s" % filename)
        path = pkg_resources.resource_filename(__name__, "data/prcd/%s" % filename)
        fd = codecs.open(path, encoding='utf-8')
        lines = fd.readlines()
        moccoli[category] = lines
        fd.close()

    return moccoli
moccoli = read_prcd_files()
prcd_categories = moccoli.keys()

def moccolo_random(category=None):
    if not category:
        category = random.choice(moccoli.keys())
    if not category in moccoli: return (None, None)
    return (category, random.choice(moccoli[category]))

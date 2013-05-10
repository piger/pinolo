# -*- coding: utf-8 -*-
import re
import htmlentitydefs
import hashlib


def strip_html(text):
    """Strip HTML tags from a given `text` string.

    From: http://effbot.org/zone/re-sub.htm#unescape-html
    """

    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass

        elif text[:1] == "&":
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)


def decode_text(text):
    """Decode a given text string to an Unicode string.

    If `text` can't be decoded to a common encoding, it will be decoded to UTF-8
    passing the "replace" options.
    """
    for enc in ('utf-8', 'iso-8859-15', 'iso-8859-1', 'ascii'):
        try:
            return text.decode(enc)
        except UnicodeDecodeError:
            continue
    # fallback
    return text.decode('utf-8', 'replace')


def md5(text):
    """Calculate the MD5 hash for a given text, returning an hex string."""
    return hashlib.md5(text).hexdigest()

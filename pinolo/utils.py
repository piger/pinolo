import re
import hashlib
import httplib
import urllib2
import htmlentitydefs
import subprocess
import errno
import sys
import os
import fcntl

import gevent
from gevent import socket

from pinolo import USER_AGENT

def strip_html(text):
    """
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
    for enc in ('utf-8', 'iso-8859-15', 'iso-8859-1', 'ascii'):
        try:
            return text.decode(enc)
        except UnicodeDecodeError:
            continue
    # fallback
    return text.decode('utf-8', 'replace')

def md5(text):
    return hashlib.md5(text).hexdigest()


class gevent_HTTPConnection(httplib.HTTPConnection):
    """
    httplib.HTTPConnection compatibile con gevent.
    - da python 2.6

    Per evitare monkey.patch_all():
    http://groups.google.com/group/gevent/browse_thread/thread/c20181cb066ee97e?fwc=2&pli=1
    """
    def connect(self):
        self.sock = socket.create_connection((self.host, self.port),
                                             self.timeout)
        if self._tunnel_host:
            self._tunnel()

class gevent_HTTPHandler(urllib2.HTTPHandler):
    """
    urllib2.HTTPHandler compatibile con gevent.
    """
    def http_open(self, request):
        return self.do_open(gevent_HTTPConnection, request)

def gevent_url_open(url, headers=[], data=None):
    """
    Fa una richiesta HTTP GET o POST con eventuali `headers` aggiunti.
    E' compatibile con gevent.
    """
    request = urllib2.Request(url, data)
    request.add_header('User-Agent', USER_AGENT)

    for name, value in headers:
        request.add_header(name, value)

    opener = urllib2.build_opener(gevent_HTTPHandler)
    return opener.open(request)


def popen_communicate(args, data=''):
    """
    Communicate with the process non-blockingly.
    # from gevent/examples
    """
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    fcntl.fcntl(p.stdin, fcntl.F_SETFL, os.O_NONBLOCK)  # make the file nonblocking
    fcntl.fcntl(p.stdout, fcntl.F_SETFL, os.O_NONBLOCK)  # make the file nonblocking

    bytes_total = len(data)
    bytes_written = 0
    while bytes_written < bytes_total:
        try:
            # p.stdin.write() doesn't return anything, so use os.write.
            bytes_written += os.write(p.stdin.fileno(), data[bytes_written:])
        except IOError, ex:
            if ex[0] != errno.EAGAIN:
                raise
            sys.exc_clear()
        socket.wait_write(p.stdin.fileno())

    p.stdin.close()

    chunks = []

    while True:
        try:
            chunk = p.stdout.read(4096)
            if not chunk:
                break
            chunks.append(chunk)
        except IOError, ex:
            if ex[0] != errno.EAGAIN:
                raise
            sys.exc_clear()
        socket.wait_read(p.stdout.fileno())

    p.stdout.close()
    return ''.join(chunks)

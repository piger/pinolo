import hashlib
import httplib
import urllib2

import gevent
from gevent import socket

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
    httplib/urllib2 + gevent
    modificata a mano perche' la versione in rete SUCA

    Per evitare monkey.patch_all():
    http://groups.google.com/group/gevent/browse_thread/thread/c20181cb066ee97e?fwc=2&pli=1
    """
    def connect(self):
        self.sock = socket.create_connection((self.host, self.port),
                                             self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()

class gevent_HTTPHandler(urllib2.HTTPHandler):
    def http_open(self, request):
        return self.do_open(gevent_HTTPConnection, request)


# from gevent/examples

import subprocess
import errno
import sys
import os
import fcntl


def popen_communicate(args, data=''):
    """Communicate with the process non-blockingly."""
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

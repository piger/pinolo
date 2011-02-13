# Copyright (C) 2010-2011 sand <daniel@spatof.org>
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation and/or
#    other materials provided with the distribution.
# 3. The name of the author nor the names of its contributors may be used to
#    endorse or promote products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re

def clean_irc(msg):
    """Prende del testo da IRC e lo pulisce da:
    - nickname: a inizio riga
    - whitespace
    - encoding utf-8
    """
    # strippa "nick: " all'inizio delle frasi
    msg = re.sub("^[^:]+:\s+", '', msg, 1)
    # strippa newline
    msg = re.sub("\n$", "", msg)
    # strippa whitespace a inizio e fine riga
    msg = msg.strip()
    #return unicodize(msg)
    return msg

def unicodize(s):
    """thx _ale"""
    for enc in ['ascii', 'utf-8', 'iso-8859-15', 'iso-8859-1']:
        try:
            return unicode(s, enc)
        except UnicodeDecodeError:
            continue
    return s

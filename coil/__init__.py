# Copyright (c) 2005-2006 Itamar Shtull-Trauring.
# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Coil: A Configuration Library."""

__version_info__ = (0,3,21)
__version__ = ".".join([str(x) for x in __version_info__])
__all__ = ['struct', 'parser', 'tokenizer', 'errors']

from coil.parser import Parser

def parse_file(file_name, **kwargs):
    """Open and parse a coil file.

    See :class:`Parser <coil.parser.Parser>` for possible keyword arguments.

    :param file_name: Name of file to parse.
    :type file_name: str

    :return: The root object.
    :rtype: :class:`Struct <coil.struct.Struct>`
    """
    file_fd = open(file_name)
    parser = Parser(file_fd, file_name, **kwargs)
    file_fd.close()
    return parser.root()

def parse(string, **kwargs):
    """Parse a coil string.

    See :class:`Parser <coil.parser.Parser>` for possible keyword arguments.

    :param file_name: String containing data to parse.
    :type file_name: str

    :return: The root object.
    :rtype: :class:`Struct <coil.struct.Struct>`
    """
    return Parser(string.splitlines(), **kwargs).root()

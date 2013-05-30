# Copyright (c) 2005-2006 Itamar Shtull-Trauring.
# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Struct is the core object in Coil.

Struct objects are similar to dicts except they are intended to be used
as a tree and can handle relative references between them.
"""

from __future__ import generators

import re
from UserDict import DictMixin

from coil import tokenizer, errors


# Used by _expand_str()
_EXPAND_BRACES = re.compile("^(.*){([^}]+)}(.*)$")
_EXPAND_RANGE = re.compile("^(0*(\d+))\.\.(\d+)$")

def _expand_str(string):
    """Helper function for _expand_list to operate on individual strings"""

    if not isinstance(string, basestring):
        return [string]

    match = _EXPAND_BRACES.search(string)
    if not match:
        return [string]
    else:
        new = []
        prefix = match.group(1)
        postfix = match.group(3)

        for item in match.group(2).split(','):
            range = _EXPAND_RANGE.match(item)
            if range:
                fmt = "%%s%%0%dd%%s" % len(range.group(1))
                for i in xrange(int(range.group(2)), int(range.group(3))+1):
                    new.extend(_expand_str(fmt % (prefix, i, postfix)))
            else:
                new.extend(_expand_str("%s%s%s" % (prefix, item, postfix)))

        return new

def _expand_list(seq):
    """Expand {1..2} and {1,2} constructs in a list of strings.
    Although this would be a useful public function it is private for
    now since in the future I think I will provide a list subclass.
    """

    new = []
    for item in seq:
        new.extend(_expand_str(item))

    return new


class Link(object):
    """A temporary symbolic link to another item."""

    def __init__(self, path):
        """
        :param path: A path to point at.
        :type path: str
        """
        self.path = path

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.path))

class Struct(tokenizer.Location, DictMixin):
    """A dict-like object for use in trees."""

    KEY = re.compile(r'^%s$' % tokenizer.Tokenizer.KEY_REGEX)
    PATH = re.compile(r'^%s$' % tokenizer.Tokenizer.PATH_REGEX)
    EXPAND = re.compile(r'\$\{(%s)\}' % tokenizer.Tokenizer.PATH_REGEX)

    #: Signal :meth:`get` to raise an error if key is not found
    _raise = object()
    #: Signal :meth:`set` to preserve location data for key
    keep = object()
    #: All possible types of expansion
    _expansion_types = frozenset(['links', 'strings'])

    # These first methods likely would need to be overridden by subclasses

    def __init__(self, base=(), container=None, name=None, location=None):
        """
        :param base: A :class:`dict`, :class:`Struct`, or a sequence of
            (key, value) pairs to initialize with. Any child :class:`dict`
            or :class:`Struct` will be recursively copied.
        :param container: the parent :class:`Struct` if there is one.
        :param name: The name of this :class:`Struct` in its container.
        :param location: The where this :class:`Struct` is defined.
            This is normally only used by the :class:`Parser
            <coil.parser.Parser>`.
        """
        assert getattr(base, '__iter__', False)

        tokenizer.Location.__init__(self, location)
        self.container = container
        self.name = name
        self._values = {}
        self._order = []

        # the list of child structs if this is a map, this map
        # copy kludge probably can go away when StructPrototype does.
        self._map = getattr(base, '_map', None)

        # this has to be compared to none,
        # because Struct overrides len
        if name and container is not None:
            self._path = "%s.%s" % (container._path, name)
        else:
            self._path = "@root"

        if getattr(base, 'iteritems', False):
            base_iter = base.iteritems()
        else:
            base_iter = iter(base)

        for key, value in base_iter:
            if isinstance(value, (Struct, dict)):
                value = self.__class__(value, self, key)
            elif isinstance(value, list):
                value = list(value)
            self[key] = value

    def _get(self, key):
        return self._values[key]

    def _set(self, key, value):
        self._values[key] = value
        if key not in self._order:
            self._order.append(key)

    def _del(self, key):
        del self._values[key]
        try:
            self._order.remove(key)
        except ValueError:
            raise KeyError

    def __contains__(self, key):
        return key in self._values

    def __iter__(self):
        """Iterate over the ordered list of keys."""
        for key in self._order:
            yield key

    def __len__(self):
        return len(self._values)

    # The remaining methods likely do not need to be overridden in subclasses

    def get(self, path, default=_raise):
        """Get a value from any :class:`Struct` in the tree.

        :param path: key or arbitrary path to fetch.
        :param default: return this value if item is missing.
            Note that the behavior here differs from a :class:`dict`.
            If *default* is unspecified and missing a
            :exc:`~errors.KeyMissingError` will be raised as
            __getitem__ does, not return *None*.

        :return: The fetched item or the value of *default*.
        """

        try:
            parent, key = self._get_next_parent(path)
        except KeyError:
            if default is self._raise:
                raise
            else:
                return default

        if parent is self:
            if not key:
                value = self
            else:
                try:
                    value = self._get(key)
                except KeyError:
                    if default is self._raise:
                        raise errors.KeyMissingError(self, key)
                    else:
                        value = default
        else:
            value = parent.get(key, default)

        return value

    __getitem__ = get

    def _update_path(self, path):
        self._path = path
        for key, node in self.iteritems():
            if isinstance(node, Struct):
                node._update_path("%s.%s"  % (path, key))

    def set(self, path, value, location=None):
        """Set a value in any :class:`Struct` in the tree.

        :param path: key or arbitrary path to set.
        :param value: value to save.
        :param location: defines where this value was defined.
            Set to :data:`Struct.keep` to not modify the location if it
            is already set, this is used by :meth:`expanditem`.
        """

        parent, key = self._get_next_parent(path, True)

        if parent is self:
            if not key or not self.KEY.match(key):
                raise errors.KeyValueError(self, key)

            if isinstance(value, Struct) and value.container is None:
                value.container = self
                value.name = key
                value._update_path("%s.%s" % (parent._path, key))

            self._set(key, value)
        else:
            parent.set(key, value, location)

    __setitem__ = set

    def __delitem__(self, path):
        parent, key = self._get_next_parent(path)

        if parent is self:
            if not key:
                raise errors.KeyValueError(path)

            try:
                self._del(path)
            except KeyError:
                raise errors.KeyMissingError(self, key)
        else:
            del parent[key]

    def merge(self, other):
        """Recursively merge a coil :class:`Struct` tree.

        This is similar to :meth:`update` except that it will update
        the entire subtree rather than just this object.
        """

        for key, value in other.iteritems():
            if isinstance(value, Struct):
                dest = self.get(key, None)
                if not isinstance(dest, Struct):
                    dest = Struct(container=self, name=key)
                dest.merge(value)
                self._set(key, dest)
            else:
                self._set(key, value)

    def keys(self):
        """Get an ordered list of keys."""
        return list(iter(self))

    def attributes(self):
        """Alias for :meth:`keys`.

        Only for compatibility with Coil <= 0.2.2.
        """
        return self.keys()

    def has_key(self, key):
        """True if key is in this :class:`Struct`"""
        return key in self

    def iteritems(self):
        """Iterate over the ordered list of (key, value) pairs."""
        for key in self:
            yield key, self[key]

    def sort(self, cmp=None, reverse=False):
        """Sort in place. By default items are sorted by key.

        Alternate sort methods may be provided by giving a custom
        cmp method. The arguments to cmp will be (key, value) pairs.
        """

        def cmp_wrap(a, b):
            return cmp((a, self[a]), (b, self[b]))

        if not cmp:
            self._order.sort(reverse=reverse)
        else:
            self._order.sort(cmp=cmp_wrap, reverse=reverse)

    def expand(self, defaults=(), ignore_missing=(), recursive=True,
               ignore_types=(), _block=()):
        """Expand all :class:`Link` and sub-string variables in this
        and, if recursion is enabled, all child :class:`Struct`
        objects. This is normally called during parsing but may be
        useful if more control is required.

        This method modifies the tree!

        :param defaults: See :meth:`expandvalue`
        :param ignore_missing: :meth:`expandvalue`
        :param recursive: recursively expand sub-structs
        :type recursive: :class:`bool`
        :param ignore_types: :meth:`expandvalue`
        :param _block: See :meth:`expandvalue`
        """

        abspath = self.path()
        if abspath in _block:
            raise errors.StructError(self, "Circular reference to %s" % abspath)

        _block = list(_block)
        _block.append(abspath)

        if self._map is not None:
            map = _expand_list(self._map)
            self._map = None
            structs = []
            lists = []

            # We don't use iter because this loop delete stuff
            for key, value in self.items():
                value = self.expanditem(key,
                                        defaults=defaults,
                                        ignore_missing=ignore_missing,
                                        ignore_types=ignore_types,
                                        _block=_block)
                if isinstance(value, Struct):
                    structs.append((key, value))
                    del self[key]
                elif isinstance(value, list):
                    value = _expand_list(value)
                    if len(value) != len(map):
                        raise errors.StructError(self, "Invalid @map list: "
                                "expected length is %s, %s has length of %s" %
                                (len(map), key, len(value)))
                    lists.append((key, value))
                    del self[key]
                else:
                    self.set(key, value, self.keep)

            for key, orig in structs:
                for i, suffix in enumerate(map):
                    name = "%s%s" % (key, suffix)
                    if not self.validate_key(name):
                        raise errors.StructError(self, "Invalid @map list: "
                                "key contains invalid characters: %r" % suffix)
                    new = orig.__class__(orig, name=name, container=self)
                    self[name] = new

                    for item_key, item_values in lists:
                        new[item_key] = item_values[i]

                    if recursive:
                        new.expand(defaults=defaults,
                                   ignore_missing=ignore_missing,
                                   ignore_types=ignore_types,
                                   recursive=True,
                                   _block=_block)

        else:
            for key in self:
                value = self.expanditem(key,
                                        defaults=defaults,
                                        ignore_missing=ignore_missing,
                                        ignore_types=ignore_types,
                                        _block=_block)
                self.set(key, value, self.keep)
                if recursive and isinstance(value, Struct):
                    value.expand(defaults=defaults,
                                 ignore_missing=ignore_missing,
                                 ignore_types=ignore_types,
                                 recursive=True,
                                 _block=_block)

    def expanditem(self, path, defaults=(), ignore_missing=(),
                   ignore_types=(), _block=()):
        """Fetch and expand an item at the given path. All :class:`Link`
        and sub-string variables will be followed in the process. This
        method is a no-op if value is a :class:`Struct`, use the
        :meth:`Struct.expand` method instead.

        This method does not make any changes to the tree.

        :param path: A key or arbitrary path to get.
        :param defaults: See :meth:`expandvalue`
        :param ignore_missing: See :meth:`expandvalue`
        :param ignore_types: :meth:`expandvalue`
        :param _block: See :meth:`expandvalue`
        """

        parent, key = self._get_next_parent(path)

        if parent is self:
            abspath = self.path(key)
            if abspath in _block:
                raise errors.StructError(self,
                        "Circular reference to %s" % abspath)

            _block = list(_block)
            _block.append(abspath)

            try:
                value = self[key]
            except errors.KeyMissingError:
                if key in defaults:
                    return defaults[key]
                else:
                    raise

            return self.expandvalue(value,
                                    defaults=defaults,
                                    ignore_missing=ignore_missing,
                                    ignore_types=ignore_types,
                                    _block=_block)
        else:
            return parent.expanditem(key,
                                     defaults=defaults,
                                     ignore_missing=ignore_missing,
                                     ignore_types=ignore_types,
                                     _block=_block)

    def expandvalue(self, value, defaults=(), ignore_missing=(),
                    ignore_types=(), _block=()):
        """Use this :class:`Struct` to expand the given value. All
        :class:`Link` and sub-string variables will be followed in
        the process. This method is a no-op if value is a
        :class:`Struct`, use the :meth:`expand` method instead.

        This method does not make any changes to the tree.

        :param value: Any value to expand, typically a
            :class:`Link` or string.
        :param defaults: default values to use if undefined.
        :type defaults: :class:`dict`
        :param ignore_missing: a set of keys that are ignored if
            undefined and not in defaults. If simply set to True
            then all are ignored. Otherwise raise
            :exc:`~errors.KeyMissingError`.
        :type ignore_missing: *True* or any container
        :param ignore_types: a set of types that should be ignored
            during expansion. Possible values in the set are:

            - 'strings': Don't expand ${foo} references in strings.
            - 'links': Don't follow links, leaves the Link object.

            More values will be added in the future.
        :type ignore_types: container of strings
        :param _block: a set of absolute paths that cannot be expanded.
            This is only for use internally to avoid circular references.
        :type block: any container
        """

        def expand_substr(match):
            subkey = match.group(1)
            try:
                subval = self.expanditem(subkey,
                                         defaults=defaults,
                                         ignore_missing=ignore_missing,
                                         ignore_types=ignore_types,
                                         _block=_block)
            except errors.KeyMissingError, ex:
                if ignore_missing is True or ex.key in ignore_missing:
                    return match.group(0)
                else:
                    raise

            return str(subval)

        def expand_link(link):
            try:
                subval = self.expanditem(link.path,
                                         defaults=defaults,
                                         ignore_missing=ignore_missing,
                                         ignore_types=ignore_types,
                                         _block=_block)
            except errors.KeyMissingError, ex:
                if ignore_missing is True or ex.key in ignore_missing:
                    return link
                else:
                    raise

            # Structs and lists must be copied
            if isinstance(subval, Struct):
                subval = subval.copy()
            if isinstance(subval, list):
                subval = list(subval)

            return subval

        def expand_list(list_):
            for i in xrange(len(list_)):
                if ("strings" not in ignore_types and
                        isinstance(list_[i], basestring)):
                    list_[i] = self.EXPAND.sub(expand_substr, list_[i])
                elif isinstance(list_[i], list):
                    expand_list(list_[i])

        # defaults should only contain simple keys, not paths.
        for key in defaults:
            assert "." not in key

        # allow ignore_missing=False
        if ignore_missing is False:
            ignore_missing = ()

        # catch invalid values of ignore_types
        ignore_types = frozenset(ignore_types)
        if not ignore_types.issubset(self._expansion_types):
            raise ValueError("Invalid ignore_types: %s" % ", ".join(
                ignore_types.difference(self._expansion_types)))

        if isinstance(value, Struct):
            pass
        elif "strings" not in ignore_types and isinstance(value, basestring):
            value = self.EXPAND.sub(expand_substr, value)
        elif "links" not in ignore_types and isinstance(value, Link):
            value = expand_link(value)
        elif isinstance(value, list):
            expand_list(value)

        return value

    def unexpanded(self, absolute=False, recursive=True):
        """Find a set of all keys that have not been expanded.
        This is generally only useful if :meth:`expand` was
        run with the ignore_missing parameter was set to see got
        missed.

        Normally only the short key name is given as it would be
        provided in defaults or ignore_missing parameters for the
        various expansion methods. Set absolute=True to return the
        full path for each key instead.

        :param absolute: Enables absolute paths.
        :type absolute: :class:`bool`
        :param recursive: recursively search sub-structs
        :type recursive: :class:`bool`

        :return: unexpanded keys
        :rtype: set
        """

        def normalize_key(key):
            if absolute:
                return self.path(key)
            else:
                return key.rsplit('.', 1).pop()

        def unexpanded_list(list_):
            keys = set()

            for item in list_:
                if isinstance(item, basestring):
                    for match in self.EXPAND.finditer(item):
                        keys.add(normalize_key(match.group(1)))
                elif isinstance(item, Link):
                    keys.add(normalize_key(item.path))
                elif isinstance(item, (list, tuple)):
                    keys.update(unexpanded_list(item))
                elif recursive and isinstance(item, Struct):
                    keys.update(item.unexpanded(absolute))

            return keys

        return unexpanded_list(self.values())

    def copy(self):
        """Recursively copy this :class:`Struct`"""

        return self.__class__(self)

    def dict(self, strict=False, flat=False):
        """Recursively copy this :class:`Struct` into :class:`dict` objects

        :param strict: If True then fail if the tree contains any
            values that cannot be represented in the coil text format.
        :type strict: :class:`bool`

        :param flat: If True this :class:`Struct` is copied into a single
            :class:`dict` object whose keys are the full paths to the values
            in the :class:`Struct`.
        :type flat: :class:`bool`

        :return: :class:`dict` representation of this :class:`Struct`
        :rtype: :class:`dict`
        """

        new = {}
        for key, value in self.iteritems():
            if strict:
                assert self.KEY.match(key)

            if isinstance(value, Struct):
                value = value.dict(strict, flat)
                if flat:
                    new.update(dict([('%s.%s' % (key, k), value[k])
                                     for k in value]))
                else:
                    new[key] = value
            elif isinstance(value, dict):
                new[key] = value.copy()
            elif isinstance(value, list):
                new[key] = list(value)
            else:
                new[key] = value

        return new



    def path(self, path=None):
        """Get the absolute path of this :class:`Struct` if path is
        *None*, otherwise the relative path from this :class:`Struct`
        to the given path."""

        if path:
            parent, key = self._get_next_parent(path)

            if parent is self:
                return "%s.%s" % (self._path, key)
            else:
                return parent.path(key)
        else:
            return self._path

    def _stritem(self, item):
        # FIXME: unicode breaks this, we need to handle encodings
        # explicitly in Structs rather than just in Parser
        if isinstance(item, basestring):
            # Should we use """ for multi-line strings?
            item = item.replace('\\', '\\\\')
            item = item.replace('\n', '\\n')
            item = item.replace('\r', '\\r')
            item = item.replace('"', '\\"')
            return '"%s"' % item
        elif isinstance(item, (list, tuple)):
            return "[%s]" % " ".join([self._stritem(x) for x in item])
        elif (isinstance(item, (int, long, float)) or
                item in (True, False, None)):
            return str(item)
        else:
            raise errors.StructError(self,
                "%s cannot be represented in the coil text format" % item)

    def string(self, strict=True, prefix=''):
        """Convert this :class:`Struct` tree to the coil text format.

        Note that if any value is a unicode string then this
        will return a unicode object rather than a str.

        :param strict: If True then fail if the tree contains any
            values that cannot be represented in the coil text format.
        :type strict: *bool*
        :param prefix: Start each line with the given prefix.
            Used internally to properly intend sub-structs.
        :type prefix: string
        """

        result = ""

        for key, val in self.iteritems():
            # This should never happen, but might as well be safe
            assert self.KEY.match(key)

            if isinstance(val, Struct):
                child = val.string(strict, "%s    " % prefix)
                if child:
                    result = "%s%s%s: {\n%s\n%s}\n" % (result,
                            prefix, key, child, prefix)
                else:
                    result = "%s%s%s: {}\n" % (result, prefix, key)
            else:
                result = "%s%s%s: %s\n" % (result, prefix,
                        key, self._stritem(val))

        return result.rstrip()

    def flatten(self, strict=True, prefix='', path=''):
        """Alternate version of :meth:`Struct.string` that generates a
        flat key: value list rather than a Struct tree. This is equally
        as valid as the standard format and sometimes is easier to read.

        :param strict: If True then fail if the tree contains any
            values that cannot be represented in the coil text format.
        :type strict: *bool*
        :param prefix: Start each line with the given prefix.
        :type prefix: string
        :param path: path to prefix each key with. Used for recursion.
        :type: string
        """

        result = ""

        for key, val in self.iteritems():
            assert self.KEY.match(key)

            if path:
                child_path = "%s.%s" % (path, key)
            else:
                child_path = key

            if isinstance(val, Struct):
                child = val.flatten(strict, prefix, child_path)
                if child:
                    result = "%s%s\n" % (result, child)
                else:
                    result = "%s%s%s: {}\n" % (result, prefix, child_path)
            else:
                result = "%s%s%s: %s\n" % (result, prefix,
                        child_path, self._stritem(val))

        return result.rstrip()

    def __str__(self):
        return self.string()

    def __repr__(self):
        attrs = ["%s: %s" % (repr(key), repr(val))
                 for key, val in self.iteritems()]
        return "%s({%s})" % (self.__class__.__name__, ", ".join(attrs))

    @classmethod
    def validate_key(cls, key):
        """Check if the given key is valid.

        :rtype: :class:`bool`
        """
        return bool(cls.KEY.match(key))

    @classmethod
    def validate_path(cls, path):
        """Check if the given path is valid.

        :rtype: :class:`bool`
        """
        return bool(cls.PATH.match(path))

    def _get_next_parent(self, path, add_parents=False):
        """Returns the next Struct in a path and the remaining path.

        If the path is a single key just return self and the key.
        If add_parents is true then create parent Structs as needed.
        """

        if not isinstance(path, basestring):
            raise errors.KeyTypeError(self, path)

        if path.startswith("@root"):
            if self.container:
                parent = self.container
            else:
                parent = self
                path = path[5:]
        elif "." not in path:
            # Quick exit for the simple case...
            return self, path
        elif path.startswith(".."):
            if self.container:
                parent = self.container
            else:
                raise errors.StructError(self, "Reference past root")
            path = path[1:]
        elif path.startswith("."):
            parent = self
            path = path[1:]
        else:
            # check for mid-path parent references
            if ".." in path:
                raise errors.KeyValueError(self, path)

            split = path.split(".", 1)
            key = split.pop(0)
            if split:
                path = split[0]
            else:
                path = ""

            try:
                parent = self.get(key)
            except errors.KeyMissingError:
                if add_parents:
                    parent = self.__class__(container=self, name=key)
                    self.set(key, parent)
                else:
                    raise

            if not isinstance(parent, Struct):
                raise errors.ValueTypeError(self, key, type(parent), Struct)

        if parent is self and "." in path:
            # Great, we went nowhere but there is still somewhere to go
            parent, path = self._get_next_parent(path, add_parents)

        return parent, path


#: For compatibility with Coil <= 0.2.2, use KeyError or KeyMissingError
StructAttributeError = errors.KeyMissingError

class StructNode(object):
    """For compatibility with Coil <= 0.2.2, use :class:`Struct` instead."""

    def __init__(self, struct, container=None):
        assert isinstance(struct, Struct)
        assert (container is None or
                (isinstance(container, StructNode) and
                container._struct is struct.container))
        self._struct = struct
        self._struct.prototype = None
        self._struct._attrsDict = struct
        self._struct._attrsOrder = struct.keys()
        self._struct._deletedAttrs = {}
        self._container = struct.container

    def has_key(self, attr):
        return self._struct.has_key(attr)

    def get(self, attr, default=Struct._raise):
        val = self._struct.get(attr, default)
        if isinstance(val, Struct):
            val = self.__class__(val, self)
        return val

    def attributes(self):
        return self._struct.keys()

    def iteritems(self):
        for key in self._struct:
            yield key, self.get(key)

    def __getattr__(self, attr):
        return self.get(attr)

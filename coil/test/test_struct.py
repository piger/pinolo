"""Tests for coil.struct."""

import unittest
from coil import struct, errors

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        # Use a tuple to preserve order
        self.data = (('first', {
                        'string': "something",
                        'float': 2.5,
                        'int': 1,
                        'dict': {
                            'x': 1,
                            'y': 2,
                            'z': "another thing"}
                        }),
                    ('second', "something else"),
                    ('last', [ "list", "of", "strings" ]))
        self.struct = struct.Struct(self.data)

    def testFirstLevelContains(self):
        for key in ('first', 'second', 'last'):
            self.assert_(key in self.struct)

    def testSecondLevelContains(self):
        for key in ('string', 'float', 'int'):
            self.assert_(key in self.struct['first'])

    def testKeyOrder(self):
        self.assertEquals(self.struct.keys(), ['first', 'second', 'last'])

    def testGetItem(self):
        self.assertEquals(self.struct['second'], "something else")

    def testGetSimple(self):
        self.assertEquals(self.struct.get('second'), "something else")

    def testGetDefault(self):
        self.assertEquals(self.struct.get('bogus', "awesome"), "awesome")
        self.assertEquals(self.struct.get('bogus.sub', "awesome"), "awesome")

    def testGetPath(self):
        self.assertEquals(self.struct.path(), "@root");
        self.assertEquals(self.struct.get('first.int'), 1)

    def testGetRelativePath(self):
        self.assertEquals(self.struct.path(''), "@root")
        self.assertEquals(self.struct.path('first'), "@root.first")
        self.assertEquals(self.struct.path('last'), "@root.last")
        self.assertEquals(self.struct.get('first').path('string'), "@root.first.string")
        self.assertEquals(self.struct.get('first').path('dict.x'), "@root.first.dict.x")
        self.assertEquals(self.struct.get('first').path('dict.y'), "@root.first.dict.y")

    def testGetParent(self):
        child = self.struct['first']
        self.assertEquals(child.get('..second'), "something else")

    def testGetRoot(self):
        child = self.struct['first']
        self.assertEquals(child.get('@root.second'), "something else")

    def testIterItems(self):
        itemlist = [("one", 1), ("two", 2), ("three", 3)]
        self.assertEquals(list(struct.Struct(itemlist).iteritems()), itemlist)

    def testKeyMissing(self):
        self.assertRaises(errors.KeyMissingError, lambda: self.struct['bogus'])
        self.assertRaises(errors.KeyMissingError, self.struct.get, 'bad')

    def testKeyType(self):
        self.assertRaises(errors.KeyTypeError, lambda: self.struct[None])
        self.assertRaises(errors.KeyTypeError, self.struct.get, None)

    def testKeyValue(self):
        self.assertRaises(errors.KeyValueError,
                self.struct.set, 'first#', '')
        self.assertRaises(errors.KeyValueError,
                self.struct.set, 'first..second', '')

    def testDict(self):
        self.assertEquals(self.struct['first'].dict(), dict(self.data[0][1]))

    def testFlatDict(self):
        fd = self.struct.dict(flat=True)
        s = struct.Struct()
        for k in fd:
            s[k] = fd[k]
        self.assertEquals(self.struct, s)

    def testSetShort(self):
        s = struct.Struct()
        s['new'] = True
        self.assertEquals(s['new'], True)

    def testSetLong(self):
        s = struct.Struct()
        s['new.sub'] = True
        self.assertEquals(s['new.sub'], True)
        self.assertEquals(s['new']['sub'], True)

    def testSetSubStruct(self):
        s = struct.Struct({'sub': {'x': '${y}'}})
        self.assertRaises(KeyError, s.expand)
        s['sub.y'] = "zap"
        s.expand()
        self.assertEquals(s['sub.x'], "zap")
        self.assertEquals(s['sub.y'], "zap")
        self.assertEquals(s['sub']['x'], "zap")
        self.assertEquals(s['sub']['y'], "zap")

    def testCopy(self):
        a = self.struct['first'].copy()
        b = self.struct['first'].copy()
        a['string'] = "this is a"
        b['string'] = "this is b"
        self.assertEquals(a['string'], "this is a")
        self.assertEquals(b['string'], "this is b")
        self.assertEquals(a['@root.string'], "this is a")
        self.assertEquals(b['@root.string'], "this is b")
        self.assertEquals(self.struct['first.string'], "something")

    def testValidate(self):
        self.assertEquals(struct.Struct.validate_key("foo"), True)
        self.assertEquals(struct.Struct.validate_key("foo.bar"), False)
        self.assertEquals(struct.Struct.validate_key("@root"), False)
        self.assertEquals(struct.Struct.validate_key("#blah"), False)
        self.assertEquals(struct.Struct.validate_path("foo"), True)
        self.assertEquals(struct.Struct.validate_path("foo.bar"), True)
        self.assertEquals(struct.Struct.validate_path("@root"), True)
        self.assertEquals(struct.Struct.validate_path("#blah"), False)

    def testMerge(self):
        s1 = self.struct.copy()
        s2 = struct.Struct()
        s2['first.new'] = "whee"
        s2['other.new'] = "woot"
        s2['new'] = "zomg"
        s1.merge(s2)
        self.assertEquals(s1['first.string'], "something")
        self.assertEquals(s1['first.new'], "whee")
        self.assertEquals(s1['other'], struct.Struct({'new': "woot"}))
        self.assertEquals(s1['new'], "zomg")

class ExpansionTestCase(unittest.TestCase):

    def testExpand(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}"
        root.expand()
        self.assertEquals(root.get('bar'), "omgwtfbbq")

    def testExpandItem(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}")
        self.assertEquals(root.expanditem('bar'), "omgwtfbbq")

    def testExpandDefault(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}${baz}"
        root.expand({'foo':"123",'baz':"456"})
        self.assertEquals(root.get('bar'), "omgwtfbbq456")

    def testExpandItemDefault(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}${baz}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}${baz}")
        self.assertEquals(root.expanditem('bar',
            defaults={'foo':"123",'baz':"456"}), "omgwtfbbq456")

    def testExpandIgnore(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}${baz}"
        root.expand(ignore_missing=True)
        self.assertEquals(root.get('bar'), "omgwtfbbq${baz}")
        root.expand(ignore_missing=('baz',))
        self.assertEquals(root.get('bar'), "omgwtfbbq${baz}")

    def testExpandIgnoreType(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}"
        root.expand(ignore_types=('strings',))
        self.assertEquals(root.get('bar'), "omgwtf${foo}")
        root["lfoo"] = struct.Link("foo")
        root.expand(ignore_types=('links',))
        self.assertEquals(root.get('bar'), "omgwtfbbq")
        self.assert_(isinstance(root.get('lfoo'), struct.Link))
        root.expand()
        self.assert_(isinstance(root.get('lfoo'), basestring))
        self.assertEquals(root.get('lfoo'), "bbq")

    def testUnexpanded(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}${baz}"
        root.expand(ignore_missing=True)
        self.assertEquals(root.unexpanded(), set(["baz"]))
        self.assertEquals(root.unexpanded(True), set(["@root.baz"]))

    def testExpandItemIgnore(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}${baz}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}${baz}")
        self.assertEquals(root.expanditem('bar', ignore_missing=('baz',)),
                "omgwtfbbq${baz}")

    def testExpandError(self):
        root = struct.Struct()
        root["bar"] = "omgwtf${foo}"
        self.assertRaises(KeyError, root.expand)
        self.assertEquals(root.get('bar'), "omgwtf${foo}")

    def testExpandItemError(self):
        root = struct.Struct()
        root["bar"] = "omgwtf${foo}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}")
        self.assertRaises(KeyError, root.expanditem, 'bar')
        self.assertEquals(root.get('bar'), "omgwtf${foo}")

    def testExpandInList(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = [ "omgwtf${foo}" ]
        self.assertEquals(root['bar'][0], "omgwtf${foo}")
        root.expand()
        self.assertEquals(root['bar'][0], "omgwtfbbq")

    def testExpandInSubList(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = [ [ "omgwtf${foo}" ] ]
        self.assertEquals(root['bar'][0][0], "omgwtf${foo}")
        root.expand()
        self.assertEquals(root['bar'][0][0], "omgwtfbbq")

    def testExpandMixed(self):
        root = struct.Struct()
        root["foo"] = "${bar}"
        self.assertEquals(root.expanditem("foo", {'bar': "a"}), "a")
        root["bar"] = "b"
        self.assertEquals(root.expanditem("foo", {'bar': "a"}), "b")

    def testCopy(self):
        a = struct.Struct()
        a["foo"] = [ "omgwtf${bar}" ]
        a["bar"] = "a"
        b = a.copy()
        b["bar"] = "b"
        self.assertEquals(a.expanditem("foo"), [ "omgwtfa" ])
        self.assertEquals(b.expanditem("foo"), [ "omgwtfb" ])
        a.expand()
        b.expand()
        self.assertEquals(a.get("foo"), [ "omgwtfa" ])
        self.assertEquals(b.get("foo"), [ "omgwtfb" ])

    def testSortKeys(self):
        ukeys = ['z','r','a','c']
        skeys = sorted(ukeys)
        a = struct.Struct([(k,None) for k in ukeys])
        self.assertEquals(a.keys(), ukeys)
        self.assertNotEqual(a.keys(), skeys)
        a.sort()
        self.assertEquals(a.keys(), skeys)
        self.assertNotEqual(a.keys(), ukeys)

    def testSortValues(self):
        def keycmp(a,b):
            return cmp(a[1], b[1])
        uvalues = ['z','r','a','c']
        svalues = sorted(uvalues)
        a = struct.Struct()
        for i,v in enumerate(uvalues):
            a["_%s" % i] = v
        self.assertEquals(a.values(), uvalues)
        self.assertNotEqual(a.values(), svalues)
        a.sort(cmp=keycmp)
        self.assertEquals(a.values(), svalues)
        self.assertNotEqual(a.values(), uvalues)


class StringTestCase(unittest.TestCase):
    def testNestedList(self):
        root = struct.Struct({'x': ['a', ['b', 'c']]})
        self.assertEquals(str(root), 'x: ["a" ["b" "c"]]')

    def testNormal(self):
        root = struct.Struct({'x': {'y': None}})
        self.assertEquals(str(root), 'x: {\n    y: None\n}')

    def testFlat(self):
        root = struct.Struct({'x': {'y': None}})
        self.assertEquals(root.flatten(), 'x.y: None')

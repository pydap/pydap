import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from pydap.model import DapType
from pydap.model import *


class TestDapType(unittest.TestCase):
    def test_dap_type_repr(self):
        var = DapType("test")
        self.assertEqual(repr(var), "DapType('test', {})")

        var = DapType("test", foo="bar", value=42)
        self.assertEqual(repr(var),
                "DapType('test', {'foo': 'bar', 'value': 42})")

    def test_attributes(self):
        var = DapType("test", foo="bar", value=42)

        self.assertEqual(var.foo, "bar")
        self.assertEqual(var.attributes["foo"], "bar")

        with self.assertRaises(AttributeError):
            var.baz

        with self.assertRaises(KeyError):
            var.attributes['baz']


class TestBaseType(unittest.TestCase):
    def test_base_type_repr(self):
        var = BaseType("test", 42, foo="bar")
        self.assertEqual(repr(var), "<BaseType with data 42>")

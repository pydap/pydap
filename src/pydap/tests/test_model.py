import unittest 

from pydap.model import *
from pydap.model import DapType


class TestQuote(unittest.TestCase):
    def test_unquoted(self):
        var = DapType('foo')
        self.assertEqual(var.name, 'foo')

    def test_quoted(self):
        var = DapType('foo.bar')
        self.assertEqual(var.name, 'foo%2Ebar')

    def test_no_double_quote(self):
        var = DapType('foo%2Ebar')
        self.assertEqual(var.name, 'foo%2Ebar')

    def test_bracket(self):
        var = DapType('foo[') 
        self.assertEqual(var.name, 'foo%5B')


class TestAttributes(unittest.TestCase):
    def setUp(self):
        self.var = DapType('foo', {'bar': 1}, baz=2)

    def test_assignment(self):
        self.assertEqual(self.var.attributes['bar'], 1)
        self.assertEqual(self.var.attributes['baz'], 2)

    def test_lazy_attribute(self):
        self.assertEqual(self.var.attributes['bar'], self.var.bar)
        self.assertEqual(self.var.attributes['baz'], self.var.baz)


class TestId(unittest.TestCase):
    def setUp(self):
        self.dataset = DatasetType(name='zero')
        self.dataset['one'] = StructureType(name='one')
        self.dataset['one']['two'] = BaseType(name='two')

    def test_dataset(self):
        self.assertEqual(self.dataset.id, self.dataset.name)

    def test_children(self):
        self.assertEqual(self.dataset['one'].id, 'one')
        self.assertEqual(self.dataset['one']['two'].id, 'one.two')


class TestDataset(unittest.TestCase):
    pass

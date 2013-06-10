import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from pydap.parsers import SimpleParser, parse_hyperslab


class TestParseHyperslab(unittest.TestCase):
    def test_point(self):
        self.assertEqual(parse_hyperslab('[0]'), (slice(0, 1, 1),))

    def test_start_stop(self):
        self.assertEqual(parse_hyperslab('[0:1]'), (slice(0, 2, 1),))

    def test_start_step_stop(self):
        self.assertEqual(parse_hyperslab('[0:2:9]'), (slice(0, 10, 2),))


class TestSimpleParser(unittest.TestCase):
    def test_peek(self):
        parser = SimpleParser("Hello, World!")
        self.assertEqual(parser.peek("\w+"), "Hello")
        
    def test_consume(self):
        parser = SimpleParser("Hello, World!")
        self.assertEqual(parser.consume("\w+"), "Hello")
        self.assertEqual(parser.consume(", "), ", ")
        self.assertEqual(parser.consume("\w+"), "World")
        self.assertEqual(parser.consume("!"), "!")

        with self.assertRaises(Exception):
            parser.consume("\w+")

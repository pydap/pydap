from webtest import TestApp
import unittest


def MyApp(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain; charset=utf-8')])
    yield 'foo\n'.encode('utf-8')
    yield 'bar\n'.encode('utf-8')
    yield 'baz\n'.encode('utf-8')


class MyTest(unittest.TestCase):
    def setUp(self):
        self.app = TestApp(MyApp)

    def test_webtest(self):
        expected = 'foo\nbar\nbaz\n'
        self.assertEqual(self.app.get('/').text, expected)

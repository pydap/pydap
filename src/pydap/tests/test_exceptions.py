import unittest

from pydap.exceptions import *


class TestExceptions(unittest.TestCase):
    def test_dap_error(self):
        exc = DapError("This is a test.")
        self.assertEqual(exc.value, "This is a test.")
        self.assertEqual(str(exc), repr("This is a test."))

    def test_client_error(self):
        exc = ClientError("")
        self.assertEqual(exc.code, 100)

    def test_server_error(self):
        exc = ServerError("")
        self.assertEqual(exc.code, 200)

    def test_ce_error(self):
        exc = ConstraintExpressionError("")
        self.assertEqual(exc.code, 201)

    def test_handler_error(self):
        exc = HandlerError("")
        self.assertEqual(exc.code, 300)

    def test_extension_error(self):
        exc = ExtensionNotSupportedError("")
        self.assertEqual(exc.code, 301)

    def test_open_file_error(self):
        exc = OpenFileError("")
        self.assertEqual(exc.code, 302)

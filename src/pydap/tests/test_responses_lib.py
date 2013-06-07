import unittest

from webtest import TestApp

from pydap.model import *
from pydap.responses.lib import BaseResponse


class DatasetClosed(Exception):
    """Use an exception to signal that the dataset was closed."""
    pass


class TestBaseResponse(unittest.TestCase):
    def setUp(self):
        dataset = DatasetType("test")
        self.response = BaseResponse(dataset)

    def test_iter(self):
        with self.assertRaises(NotImplementedError):
            body = iter(self.response)

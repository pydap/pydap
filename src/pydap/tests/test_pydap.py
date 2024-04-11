"""Test pydap namespace."""

import unittest

import pydap


class TestNamespace(unittest.TestCase):
    """Test pydap namespace."""

    def test_namespace(self):
        """Test the namespace."""
        self.assertEqual(pydap.__name__, "pydap")

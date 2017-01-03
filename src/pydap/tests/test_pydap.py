"""Test Pydap namespace."""

import pydap
import unittest


class TestNamespace(unittest.TestCase):

    """Test Pydap namespace."""

    def test_namespace(self):
        """Test the namespace."""
        self.assertEqual(pydap.__name__, "pydap")
        self.assertEqual(
            pydap.__doc__, "Declare the namespace ``pydap`` here.")

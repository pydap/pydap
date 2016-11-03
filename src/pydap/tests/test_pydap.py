"""Test Pydap namespace."""

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import pydap


class TestNamespace(unittest.TestCase):

    """Test Pydap namespace."""

    def test_namespace(self):
        """Test the namespace."""
        self.assertEqual(pydap.__name__, "pydap")
        self.assertEqual(
            pydap.__doc__, "Declare the namespace ``pydap`` here.")

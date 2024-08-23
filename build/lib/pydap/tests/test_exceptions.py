"""Test pydap base exception."""

import unittest

from pydap.exceptions import DapError


class TestExceptions(unittest.TestCase):
    """Test pydap base exception.

    Other exceptions behave exactly like the superclass, differing only by
    name, so no testing is required.

    """

    def test_dap_error(self):
        """Test the base exception."""
        exc = DapError("This is a test.")

        self.assertEqual(exc.value, "This is a test.")
        self.assertEqual(str(exc), repr("This is a test."))

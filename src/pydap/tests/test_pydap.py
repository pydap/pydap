"""Test pydap namespace."""

import importlib
import unittest
import warnings
from unittest.mock import patch

import pytest

import pydap


class TestNamespace(unittest.TestCase):
    """Test pydap namespace."""

    def test_namespace(self):
        """Test the namespace."""
        self.assertEqual(pydap.__name__, "pydap")


@pytest.fixture(autouse=True)
def restore_pydap():
    yield
    importlib.reload(pydap)


def test_warns_when_expat_too_old():
    with patch("pyexpat.version_info", new=(2, 3, 9)):
        with pytest.warns(RuntimeWarning, match="CVE-2022-23852"):
            importlib.reload(pydap)


def test_no_warning_when_expat_is_current():
    with patch("pyexpat.version_info", new=(2, 4, 8)):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            importlib.reload(pydap)

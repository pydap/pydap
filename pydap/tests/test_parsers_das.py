"""Test DAS parsing functions."""

import numpy as np
from pydap.parsers.das import add_attributes, parse_das
from pydap.parsers.dds import build_dataset
from pydap.tests.test_parsers_dds import DDS
import unittest

DAS = """Attributes {
    structure {
        b {
            Int value 1;
            Float32 missing nan;
            String foo "one", "two";
        }
    }
    structure.i {
        Int answer 42;
    }
    meta {
        String debug 1;
    }
    SPEH {
        Int debug 1;
        Int TIME 0;
        Float32 COADSX 1e20;
        String COADSY "zero";
    }
}"""

# It is important to add attributes that have the same
# name as the dimensions of SPEH. This is an edge
# case that can break the das parser.


class TestParseDAS(unittest.TestCase):

    """Test DAS parser."""

    def setUp(self):
        """Load a dataset and apply DAS to it."""
        self.dataset = build_dataset(DDS)
        attributes = parse_das(DAS)
        add_attributes(self.dataset, attributes)

    def test_basic(self):
        """Test a basic attribute."""
        self.assertEqual(self.dataset.structure.b.value, 1)

    def test_nan(self):
        """Test NaN."""
        self.assertTrue(np.isnan(self.dataset.structure.b.missing))

    def test_multiple_values(self):
        """Test attributes with multiple values."""
        self.assertEqual(self.dataset.structure.b.foo, ["one", "two"])

    def test_dot_attribute(self):
        """Test dotted attributes."""
        self.assertEqual(self.dataset.structure.i.answer, 42)

    def test_meta_attributes(self):
        """Test attributes not associated with any variables."""
        self.assertEqual(self.dataset.meta, {"debug": "1"})

    def test_SPEH_attributes(self):
        """Test attributes not associated with any variables."""
        self.assertEqual(self.dataset.SPEH.debug, 1)
        self.assertEqual(self.dataset.SPEH.attributes['TIME'], 0)
        self.assertEqual(self.dataset.SPEH.attributes['COADSX'], 1e20)
        self.assertEqual(self.dataset.SPEH.attributes['COADSY'], "zero")

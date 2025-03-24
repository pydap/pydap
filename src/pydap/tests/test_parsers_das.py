"""Test DAS parsing functions."""

import unittest

import numpy as np

from pydap.parsers.das import add_attributes, parse_das
from pydap.parsers.dds import dds_to_dataset
from pydap.tests.test_parsers_dds import DDS

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
    floats {
        Float64 a nan;
        Float64 b -inf;
        Float64 c inf;
        Float64 d 17;
    }
}"""

# It is important to add attributes that have the same
# name as the dimensions of SPEH. This is an edge
# case that can break the das parser.


class TestParseDAS(unittest.TestCase):
    """Test DAS parser."""

    def setUp(self):
        """Load a dataset and apply DAS to it."""
        self.dataset = dds_to_dataset(DDS)
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
        self.assertEqual(self.dataset.SPEH.attributes["TIME"], 0)
        self.assertEqual(self.dataset.SPEH.attributes["COADSX"], 1e20)
        self.assertEqual(self.dataset.SPEH.attributes["COADSY"], "zero")

    def test_float_attributes(self):
        """Test various values of float attributes."""
        self.assertTrue(np.isnan(self.dataset.floats["a"]))
        self.assertEqual(self.dataset.floats["b"], float("-inf"))
        self.assertEqual(self.dataset.floats["c"], float("inf"))
        self.assertEqual(self.dataset.floats["d"], 17.0)

    def test_global_attributes(self):
        """test that there are no global nor dods_extra attributes on dataset"""
        attrs = parse_das(DAS)
        dataset = dds_to_dataset(DDS)
        dataset = add_attributes(dataset, attrs)  # new dataset instance
        self.assertNotIn("NC_GLOBAL", dataset.attributes)
        self.assertNotIn("DODS_EXTRA", dataset.attributes)
        # self.assertTrue(all(not isinstance(v, dict) for v in attrs.values()))

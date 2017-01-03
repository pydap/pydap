"""Test DDS parsing functions."""

import numpy as np
from pydap.parsers.dds import build_dataset
from pydap.model import (BaseType,
                         StructureType)
import unittest


DDS = """Dataset {
    Structure {
        Byte b;
        Int i;
        Uint ui;
        Int16 i16;
        Uint16 ui16;
        Int32 i32;
        Uint32 ui32;
        Float32 f32;
        Float64 f64;
        String s;
        Url u;
    } structure;
    Sequence {
        Int32 a;
    } sequence;
    Int32 b[10];
    Int32 c[c = 10];
    Grid {
        Array:
            Float32 SPEH[TIME = 12][COADSY = 90][COADSX = 180];
        Maps:
            Float64 TIME[TIME = 12];
            Float64 COADSY[COADSY = 90];
            Float64 COADSX[COADSX = 180];
    } SPEH;
} d;"""


class TestBuildDataset(unittest.TestCase):

    """Test DDS parser."""

    def setUp(self):
        """Parse the whole dataset."""
        self.dataset = build_dataset(DDS)

    def test_structure(self):
        """Test the structure."""
        self.assertIsInstance(self.dataset.structure, StructureType)

    def test_byte(self):
        """Test byte parsing."""
        self.assertIsInstance(self.dataset.structure.b, BaseType)
        self.assertEqual(self.dataset.structure.b.dtype, np.dtype("B"))
        self.assertEqual(self.dataset.structure.b.shape, ())

    def test_integer(self):
        """Test integer parsing."""
        self.assertIsInstance(self.dataset.structure.i, BaseType)
        self.assertEqual(self.dataset.structure.i.dtype, np.dtype(">i"))
        self.assertEqual(self.dataset.structure.i.shape, ())

    def test_unsigned_integer(self):
        """Test unsigned integer parsing."""
        self.assertIsInstance(self.dataset.structure.ui, BaseType)
        self.assertEqual(self.dataset.structure.ui.dtype, np.dtype(">I"))
        self.assertEqual(self.dataset.structure.ui.shape, ())

    def test_integer_16(self):
        """Test integer 16 parsing."""
        self.assertIsInstance(self.dataset.structure.i16, BaseType)
        self.assertEqual(self.dataset.structure.i16.dtype, np.dtype(">i"))
        self.assertEqual(self.dataset.structure.i16.shape, ())

    def test_unsigned_integer_16(self):
        """Test unsigned integer 16 parsing."""
        self.assertIsInstance(self.dataset.structure.ui16, BaseType)
        self.assertEqual(self.dataset.structure.ui16.dtype, np.dtype(">I"))
        self.assertEqual(self.dataset.structure.ui16.shape, ())

    def test_integer_32(self):
        """Test integer 32 parsing."""
        self.assertIsInstance(self.dataset.structure.i32, BaseType)
        self.assertEqual(self.dataset.structure.i32.dtype, np.dtype(">i"))
        self.assertEqual(self.dataset.structure.i32.shape, ())

    def test_unsigned_integer_32(self):
        """Test unsigned integer 32 parsing."""
        self.assertIsInstance(self.dataset.structure.ui32, BaseType)
        self.assertEqual(self.dataset.structure.ui32.dtype, np.dtype(">I"))
        self.assertEqual(self.dataset.structure.ui32.shape, ())

    def test_float_32(self):
        """Test float 32 parsing."""
        self.assertIsInstance(self.dataset.structure.f32, BaseType)
        self.assertEqual(self.dataset.structure.f32.dtype, np.dtype(">f"))
        self.assertEqual(self.dataset.structure.f32.shape, ())

    def test_float_64(self):
        """Test float 64 parsing."""
        self.assertIsInstance(self.dataset.structure.f64, BaseType)
        self.assertEqual(self.dataset.structure.f64.dtype, np.dtype(">d"))
        self.assertEqual(self.dataset.structure.f64.shape, ())

    def test_string(self):
        """Test string parsing."""
        self.assertIsInstance(self.dataset.structure.s, BaseType)
        self.assertEqual(self.dataset.structure.s.dtype, np.dtype("|S128"))
        self.assertEqual(self.dataset.structure.s.shape, ())

    def test_url(self):
        """Test url parsing."""
        self.assertIsInstance(self.dataset.structure.u, BaseType)
        self.assertEqual(self.dataset.structure.u.dtype, np.dtype("|S128"))
        self.assertEqual(self.dataset.structure.u.shape, ())

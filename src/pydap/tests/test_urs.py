import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
from pydap.responses.urs import install_basic_client
from pydap.client import open_url
import logging

logging.basicConfig(filename='urs_test.log',level=logging.DEBUG)

class TestUrs(unittest.TestCase):

    def test_basic_urs_auth(self):
        """Set up PyDAP to use the URS request() function"""
        install_basic_client('https://urs.earthdata.nasa.gov','pydap', 'OPeNDAP1', False)
        self.assertIsNotNone(open_url('https://test.opendap.org/opendap/data/nc/coads_climatology.nc'))
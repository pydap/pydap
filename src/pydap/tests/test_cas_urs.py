from pydap.client import open_url
from pydap.cas import urs
import pydap.net
import requests
import os
from nose.plugins.attrib import attr
import unittest


@attr('auth')
@attr('prod_url')
class TestUrs(unittest.TestCase):
    url = ('https://goldsmr3.gesdisc.eosdis.nasa.gov/opendap/'
           'MERRA_MONTHLY/MAIMCPASM.5.2.0/1979/'
           'MERRA100.prod.assim.instM_3d_asm_Cp.197901.hdf')
    test_url = url + '.dods?SLP[0:1:0][0:1:10][0:1:10]'
    test_url_2 = url + '.dods?PS[0:1:0][0:1:10][0:1:10]'

    def test_basic_urs_auth(self):
        """
        Set up PyDAP to use the URS request() function.

        The intent here is to ensure that pydap.net is able to
        open and url if and only if requests is able to
        open the same url.
        """
        assert(os.environ.get('USERNAME_URS'))
        assert(os.environ.get('PASSWORD_URS'))
        session = urs.setup_session(os.environ.get('USERNAME_URS'),
                                    os.environ.get('PASSWORD_URS'),
                                    check_url=self.url)

        # Check that the requests library can access the link:
        res = requests.get(self.test_url, cookies=session.cookies)
        assert(res.status_code == 200)
        res.close()

        # Check that the pydap library can access the link:
        res = pydap.net.follow_redirect(self.test_url, session=session)
        assert(res.status_code == 200)

        # Check that the pydap library can access another link:
        res = pydap.net.follow_redirect(self.test_url_2, session=session)
        assert(res.status_code == 200)
        session.close()

    def test_basic_urs_query(self):
        assert(os.environ.get('USERNAME_URS'))
        assert(os.environ.get('PASSWORD_URS'))
        session = urs.setup_session(os.environ.get('USERNAME_URS'),
                                    os.environ.get('PASSWORD_URS'),
                                    check_url=self.url)
        # Ensure authentication:
        res = pydap.net.follow_redirect(self.test_url, session=session)
        assert(res.status_code == 200)
        dataset = open_url(self.url, session=session)
        expected_data = [[[99066.15625, 99066.15625, 99066.15625,
                           99066.15625, 99066.15625],
                          [98868.15625, 98870.15625, 98872.15625,
                           98874.15625, 98874.15625],
                          [98798.15625, 98810.15625, 98820.15625,
                           98832.15625, 98844.15625],
                          [98856.15625, 98828.15625, 98756.15625,
                           98710.15625, 98776.15625],
                          [99070.15625, 99098.15625, 99048.15625,
                           98984.15625, 99032.15625]]]
        assert((dataset['SLP'][0, :5, :5] == expected_data).all())
        session.close()

from pydap.client import open_url
import pydap.net
from pydap.cas import esgf
import requests
import numpy as np
import os
from nose.plugins.attrib import attr
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


@attr('auth')
@attr('prod_url')
class TestESGF(unittest.TestCase):
    url = ('http://cordexesg.dmi.dk/thredds/dodsC/cordex_general/'
           'cordex/output/EUR-11/DMI/ICHEC-EC-EARTH/historical/r3i1p1/'
           'DMI-HIRHAM5/v1/day/pr/v20131119/'
           'pr_EUR-11_ICHEC-EC-EARTH_historical_r3i1p1_'
           'DMI-HIRHAM5_v1_day_19960101-20001231.nc')

    def test_registration_esgf_auth(self):
        """
        Attempt to access a ESGF OPENDAP link for which
        the user has not yet selected a registration group.
        This procedure has to be completed only once per project
        over the lifetime of an ESGF OPENID

        Requires OPENID_ESGF_NO_REG and PASSWORD_ESGF_NO_REG
        environment variables. These must be associated with credentials
        where no group was selected.
        """
        with self.assertRaises(UserWarning):
            session = esgf.setup_session(os.environ.get('OPENID_ESGF_NO_REG'),
                                         os.environ.get('PASSWORD_ESGF_NO_REG'),
                                         check_url=self.url)

    def test_basic_esgf_auth(self):
        """
        Set up PyDAP to use the URS request() function.

        The intent here is to ensure that pydap.net is able to
        open and url if and only if requests is able to
        open the same url.
        """
        session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                     os.environ.get('PASSWORD_ESGF'),
                                     check_url=self.url)
        test_url = self.url + '.dods?pr[0:1:0][0:1:5][0:1:5]'
        res = requests.get(test_url, cookies=session.cookies,
                           verify=False)
        assert(res.status_code == 200)
        res.close()

        res = pydap.net.follow_redirect(test_url, session=session)
        assert(res.status_code == 200)

    def test_dimension_esgf_query(self):
        session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                     os.environ.get('PASSWORD_ESGF'),
                                     check_url=self.url)
        dataset = open_url(self.url, session=session)
        data = dataset['time'][:10]
        expected_data = np.array([16832.5, 16833.5, 16834.5, 16835.5, 16836.5,
                                  16837.5, 16838.5, 16839.5, 16840.5, 16841.5])
        assert(np.isclose(data, expected_data).all())

    @unittest.skip("This test should work but does not. "
                   "An issue should be raised.")
    def test_variable_esgf_query(self):
        session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                     os.environ.get('PASSWORD_ESGF'),
                                     check_url=self.url)
        dataset = open_url(self.url, session=session)
        data = dataset['pr'][0, 200:205, 100:105]
        expected_data = [[[5.23546005e-05,  5.48864300e-05,
                           5.23546005e-05,  6.23914966e-05,
                           6.26627589e-05],
                          [5.45247385e-05,  5.67853021e-05,
                           5.90458621e-05,  6.51041701e-05,
                           6.23914966e-05],
                          [5.57906533e-05,  5.84129048e-05,
                           6.37478297e-05,  5.99500854e-05,
                           5.85033267e-05],
                          [5.44343166e-05,  5.45247385e-05,
                           5.60619228e-05,  5.58810752e-05,
                           4.91898136e-05],
                          [5.09982638e-05,  4.77430549e-05,
                           4.97323490e-05,  5.43438946e-05,
                           5.26258664e-05]]]
        assert(np.isclose(data, expected_data).all())

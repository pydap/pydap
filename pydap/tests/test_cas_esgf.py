from pydap.client import open_url
import pydap.net
from pydap.cas import esgf
import requests
import numpy as np
import os
import pytest


url = ('http://aims3.llnl.gov/thredds/dodsC/'
       'cmip5_css02_data/cmip5/output1/CCCma/CanCM4/'
       'decadal1995/fx/atmos/fx/r0i0p0/orog/1/'
       'orog_fx_CanCM4_decadal1995_r0i0p0.nc')
test_url = url + '.dods?orog[0:1:4][0:1:4]'


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(not (os.environ.get('OPENID_ESGF_NO_REG') and
                         os.environ.get('PASSWORD_ESGF_NO_REG')),
                    reason=('Without auth credentials, '
                            'this test cannot work'))
def test_registration_esgf_auth():
    """
    Attempt to access a ESGF OPENDAP link for which
    the user has not yet selected a registration group.
    This procedure has to be completed only once per project
    over the lifetime of an ESGF OPENID

    Requires OPENID_ESGF_NO_REG and PASSWORD_ESGF_NO_REG
    environment variables. These must be associated with credentials
    where no group was selected.
    """
    with pytest.raises(UserWarning):
        esgf.setup_session(os.environ.get('OPENID_ESGF_NO_REG'),
                           os.environ.get('PASSWORD_ESGF_NO_REG'),
                           check_url=url)


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(not (os.environ.get('OPENID_ESGF') and
                         os.environ.get('PASSWORD_ESGF')),
                    reason=('Without auth credentials, '
                            'this test cannot work'))
def test_basic_esgf_auth():
    """
    Set up PyDAP to use the ESGF request() function.

    The intent here is to ensure that pydap.net is able to
    open and url if and only if requests is able to
    open the same url.
    """
    session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                 os.environ.get('PASSWORD_ESGF'),
                                 check_url=url)

    res = requests.get(test_url, cookies=session.cookies,
                       verify=False)
    assert(res.status_code == 200)
    res.close()

    res = pydap.net.follow_redirect(test_url, session=session)
    assert(res.status_code == 200)


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(not (os.environ.get('OPENID_ESGF') and
                         os.environ.get('PASSWORD_ESGF')),
                    reason=('Without auth credentials, '
                            'this test cannot work'))
def test_dimension_esgf_query():
    session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                 os.environ.get('PASSWORD_ESGF'),
                                 check_url=url)

    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert(res.status_code == 200)

    dataset = open_url(url, session=session)
    data = dataset['lon'][:5]
    expected_data = np.array([0.0, 2.8125, 5.625, 8.4375, 11.25])
    assert(np.isclose(data, expected_data).all())


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(not (os.environ.get('OPENID_ESGF') and
                         os.environ.get('PASSWORD_ESGF')),
                    reason=('Without auth credentials, '
                            'this test cannot work'))
def test_variable_esgf_query():
    session = esgf.setup_session(os.environ.get('OPENID_ESGF'),
                                 os.environ.get('PASSWORD_ESGF'),
                                 check_url=url)
    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert(res.status_code == 200)

    dataset = open_url(url, session=session, output_grid=False)
    data = dataset['orog'][50:55, 50:55]
    expected_data = [[197.70425, 16.319595, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [677.014, 628.29675, 551.06, 455.5758, 343.7354],
                     [1268.3304, 1287.9553, 1161.0402, 978.3153, 809.143]]
    assert(np.isclose(data, expected_data).all())


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(not (os.environ.get('OPENID_ESGF_CEDA') and
                         os.environ.get('USERNAME_ESGF_CEDA') and
                         os.environ.get('PASSWORD_ESGF_CEDA')),
                    reason=('Without auth credentials, '
                            'this test cannot work'))
def test_variable_esgf_query_ceda():
    session = esgf.setup_session(
                    os.environ.get('OPENID_ESGF_CEDA'),
                    os.environ.get('PASSWORD_ESGF_CEDA'),
                    check_url=url,
                    username=os.environ.get('USERNAME_ESGF_CEDA'))
    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert(res.status_code == 200)

    dataset = open_url(url, session=session, output_grid=False)
    data = dataset['orog'][50:55, 50:55]
    expected_data = [[197.70425, 16.319595, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [0.0, 0.0, 0.0, 0.0, 0.0],
                     [677.014, 628.29675, 551.06, 455.5758, 343.7354],
                     [1268.3304, 1287.9553, 1161.0402, 978.3153, 809.143]]
    assert(np.isclose(data, expected_data).all())

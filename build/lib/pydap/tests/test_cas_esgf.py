import os

import numpy as np
import pytest
import requests

import pydap.net
from pydap.cas import esgf
from pydap.client import open_url

url = (
    "http://esgf-data.ucar.edu/thredds/dodsC/cmip5/output1/"
    "NCAR/CCSM4/historical/fx/atmos/fx/r0i0p0/v20130312/orog/"
    "orog_fx_CCSM4_historical_r0i0p0.nc"
)
test_url = url + ".dods?orog[0:1:4][0:1:4]"


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(
    not (
        os.environ.get("OPENID_ESGF_NO_REG") and os.environ.get("PASSWORD_ESGF_NO_REG")
    ),
    reason=("Without auth credentials, " "this test cannot work"),
)
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
        esgf.setup_session(
            os.environ.get("OPENID_ESGF_NO_REG"),
            os.environ.get("PASSWORD_ESGF_NO_REG"),
            check_url=url,
        )


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(
    not (os.environ.get("OPENID_ESGF") and os.environ.get("PASSWORD_ESGF")),
    reason=("Without auth credentials, " "this test cannot work"),
)
def test_basic_esgf_auth():
    """
    Set up PyDAP to use the ESGF request() function.

    The intent here is to ensure that pydap.net is able to
    open and url if and only if requests is able to
    open the same url.
    """
    session = esgf.setup_session(
        os.environ.get("OPENID_ESGF"), os.environ.get("PASSWORD_ESGF"), check_url=url
    )

    res = requests.get(test_url, cookies=session.cookies)
    assert res.status_code == 200
    res.close()

    res = pydap.net.follow_redirect(test_url, session=session)
    assert res.status_code == 200


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(
    not (os.environ.get("OPENID_ESGF") and os.environ.get("PASSWORD_ESGF")),
    reason=("Without auth credentials, " "this test cannot work"),
)
def test_dimension_esgf_query():
    session = esgf.setup_session(
        os.environ.get("OPENID_ESGF"), os.environ.get("PASSWORD_ESGF"), check_url=url
    )

    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert res.status_code == 200

    dataset = open_url(url, session=session)
    data = dataset["lon"][:5]
    expected_data = np.array([0.0, 1.25, 2.5, 3.75, 5.0])
    assert np.isclose(data, expected_data).all()


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(
    not (os.environ.get("OPENID_ESGF") and os.environ.get("PASSWORD_ESGF")),
    reason=("Without auth credentials, " "this test cannot work"),
)
def test_variable_esgf_query():
    session = esgf.setup_session(
        os.environ.get("OPENID_ESGF"), os.environ.get("PASSWORD_ESGF"), check_url=url
    )
    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert res.status_code == 200

    dataset = open_url(url, session=session, output_grid=False)
    data = dataset["orog"][103:105, 100:102]
    expected_data = [[271.36645508, 166.85339355], [304.22286987, 178.85267639]]
    assert np.isclose(data, expected_data).all()


@pytest.mark.auth
@pytest.mark.prod_url
@pytest.mark.skipif(
    not (
        os.environ.get("OPENID_ESGF_CEDA")
        and os.environ.get("USERNAME_ESGF_CEDA")
        and os.environ.get("PASSWORD_ESGF_CEDA")
    ),
    reason=("Without auth credentials, " "this test cannot work"),
)
def test_variable_esgf_query_ceda():
    session = esgf.setup_session(
        os.environ.get("OPENID_ESGF_CEDA"),
        os.environ.get("PASSWORD_ESGF_CEDA"),
        check_url=url,
        username=os.environ.get("USERNAME_ESGF_CEDA"),
    )
    # Ensure authentication:
    res = pydap.net.follow_redirect(test_url, session=session)
    assert res.status_code == 200

    dataset = open_url(url, session=session, output_grid=False)
    data = dataset["orog"][103:105, 100:102]
    expected_data = [[271.36645508, 166.85339355], [304.22286987, 178.85267639]]
    assert np.isclose(data, expected_data).all()

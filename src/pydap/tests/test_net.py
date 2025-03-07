"""
Test the follow redirects and handling of more complex routing situations
"""

import pytest
import requests
import requests_mock
from webob.request import Request as webob_Request
from webob.response import Response as webob_Response

from pydap.handlers.lib import BaseHandler
from pydap.net import GET, create_request, get_response
from pydap.tests.datasets import SimpleGroup


def test_redirect():
    """Test that redirection is handled properly"""
    mock_url = "http://www.test.com/"
    # mock_url is redirected to https:
    redirect_url = "http://www.test2.com/"
    with requests_mock.Mocker() as m:
        m.register_uri(
            "GET", mock_url, status_code=302, headers={"Location": redirect_url}
        )
        m.register_uri("GET", redirect_url, text="Final Destination", status_code=200)
        req = create_request(mock_url)
        assert req.url == redirect_url
        assert req.status_code == 200
        assert req.text == "Final Destination"
        assert isinstance(req, requests.Response)

    # Without session:
    with requests_mock.Mocker() as m:
        m.register_uri(
            "GET",
            mock_url,
            text="resp1",
            status_code=301,
            headers={"Location": redirect_url},
        )
        m.register_uri("GET", redirect_url, text="resp2", status_code=200)
        req = create_request(mock_url)
        assert isinstance(req, requests.Response)
        # Ensure follow redirect:
        assert len(m.request_history) == 2
        assert req.url == redirect_url
        assert req.status_code == 200
        assert req.text == "resp2"

    # With session:
    with requests_mock.Mocker() as m:
        m.register_uri(
            "GET",
            mock_url,
            text="resp1",
            status_code=301,
            headers={"Location": redirect_url},
        )
        m.register_uri("GET", redirect_url, text="resp2", status_code=200)
        req = create_request(mock_url, session=requests.Session())
        # Ensure follow redirect:
        assert len(m.request_history) == 2
        assert isinstance(req, requests.Response)
        assert req.url == redirect_url
        assert req.status_code == 200
        assert req.text == "resp2"


@pytest.mark.parametrize(
    "use_cache",
    [False, True],
)
def test_cache(use_cache):
    """Test that caching is handled properly"""
    url = "http://test.opendap.org:8080/opendap/data/nc/123bears.nc"
    # cache_kwargs are being set, but only used when use_cache is True
    # thus - raise a warning if cache_kwargs are set and use_cache is False
    cache_kwargs = {
        "cache_name": "http_cache",
        "backend": "sqlite",
        "use_temp": True,
        "expire_after": 100,  # seconds
    }
    if not use_cache:
        with pytest.warns(UserWarning):
            create_request(url, use_cache=use_cache, cache_kwargs=cache_kwargs)
    else:
        r = create_request(url, use_cache=use_cache, cache_kwargs=cache_kwargs)
        assert r.status_code == 200


def test_raise_httperror():
    """test that raise_for_status raises the correct HTTPerror"""
    fake_url = "https://httpstat.us/404"  # this url will return a 404
    with pytest.raises(requests.exceptions.HTTPError):
        create_request(fake_url)


@pytest.fixture
def appGroup():
    """Creates an application from the SimpleGroup dataset"""
    return BaseHandler(SimpleGroup)


def test_GET_application(appGroup):
    """Test that local url are handled properly"""
    data_url = "http://localhost:8080/"
    r = GET(data_url + ".dmr", application=appGroup)
    assert r.status_code == 200


def test_create_request_application(appGroup):
    """Test that local url are handled properly"""
    req = create_request("/.dmr", application=appGroup, verify=True)
    assert isinstance(req, webob_Request)
    resp = get_response(req, application=appGroup, verify=True)
    assert isinstance(resp, webob_Response)
    assert resp.status_code == 200

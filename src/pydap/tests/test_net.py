"""
Test the follow redirects and handling of more complex routing situations
"""

import pytest
import requests
import requests_mock

from pydap.net import create_request


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


def test_httperror():
    """test that raise_for_status raises the correct HTTPerror"""
    fake_url = "https://httpstat.us/404"  # this url will return a 404
    with pytest.raises(requests.exceptions.HTTPError):
        create_request(fake_url)

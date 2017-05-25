"""
Test the follow redirects and handling of more complex routing situations
"""

import requests
from webob.request import Request
import requests_mock
from pydap.net import create_request


def test_redirect():
    """ Test that redirection is handled properly """
    mock_url = 'http://www.test.com/'
    # mock_url is redirected to https:
    redirect_url = 'http://www.test2.com/'
    with requests_mock.Mocker() as m:
        m.register_uri('HEAD', mock_url, text='resp2', status_code=200)
        req = create_request(mock_url)
        assert len(m.request_history) == 1
        assert isinstance(req, Request)
        assert req.headers['Host'] == 'www.test.com:80'

    # Without session:
    with requests_mock.Mocker() as m:
        m.register_uri('HEAD', mock_url, text='resp1', status_code=301,
                       headers={'Location': redirect_url})
        m.register_uri('HEAD', redirect_url, text='resp2', status_code=200)
        req = create_request(mock_url)
        # Ensure follow redirect:
        assert len(m.request_history) == 2
        assert isinstance(req, Request)
        assert req.headers['Host'] == 'www.test2.com:80'

    # With session:
    with requests_mock.Mocker() as m:
        m.register_uri('HEAD', mock_url, text='resp1', status_code=301,
                       headers={'Location': redirect_url})
        m.register_uri('HEAD', redirect_url, text='resp2', status_code=200)
        req = create_request(mock_url, session=requests.Session())
        # Ensure follow redirect:
        assert len(m.request_history) == 2
        assert isinstance(req, Request)
        assert req.headers['Host'] == 'www.test2.com:80'

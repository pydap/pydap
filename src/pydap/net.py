from webob.exc import HTTPError
from contextlib import closing
import requests
from requests.exceptions import MissingSchema
import wsgiadapter

from six.moves.urllib.parse import urlsplit, urlunsplit


def GET(url, application=None, session=None):
    """Open a remote URL returning a webob.response.Response object

    Optional parameters:
    session: a requests.Session() object (potentially) containing
             authentication cookies.

    Optionally open a URL to a local WSGI application
    """
    if application:
        _, _, path, query, fragment = urlsplit(url)
        url = urlunsplit(('WSGIapplication', '', path, query, fragment))

    with WSGISession(url, application, session) as wsgi:
        return wsgi.get(url)


def raise_for_status(response):
    if response.status_code >= 400:
        raise HTTPError(
            detail=response.status,
            headers=response.headers,
            comment=response.content
        )


class WSGISession():
    def __init__(self, url, application=None, session=None):
        self.session = session
        self._close_session = False
        if session is None:
            self.session = requests.Session()
            self._close_session = True

        scheme, netloc, path, query, fragment = urlsplit(url)
        self._domain = urlunsplit((scheme, netloc, '', '', ''))
        self.session.mount(self._domain, wsgiadapter.WSGIAdapter(application))

    def __enter__(self):
        return self.session

    def close(self):
        if self._close_session:
            self.session.close()
        else:
            session.mount(self._domain, requests.adapters.HTTPAdapter())

    def __exit__(self ,type, value, traceback):
        self.close()

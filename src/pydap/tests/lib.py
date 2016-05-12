"""Intercept HTTP requests and pass them directly to a WSGI app.

This module implements a function that will monkeypatch ``requests``, allowing
Pydap requests directly to the server without a network stack. Used for unit
testing.

"""

from webob.request import Request

def requests_intercept(app, location):
    """Intercept WSGI requests and pass them to ``webtest.TestApp``.
    
    Return a replacement for ``requests.get``:

        >>> import requests
        >>> old_get = requests.get
        >>> requests.get = requests_intercept(wsgi_app,
        ...     "http://localhost:8001/")  # doctest: +SKIP
    
    Requests for ``http://localhost:8001/`` will now be routed to the WSGI 
    application ``app``:

        >>> from pydap.client import open_url
        >>> dataset = open_url("http://localhost:8001/")  # doctest: +SKIP

    After using it, set it back:

        >>> requests.get = old_get
    
    """
    def new_get(url, **kwargs):
        path = url[len(location):]
        response = app.get('/%s' % path)
        return MockResponse(response)
    return new_get


class MockResponse(object):

    """Return a fake requests response.

    This class converts a webtest response to a requests response. It
    implements only the methods used by the Pydap client.

    """

    def __init__(self, response):
        self.response = response

        self.text = response.body
        self.content = response.body

    def raise_for_status(self):
        """Mock requests ``raise_for_status`` method."""
        pass

    def iter_content(self, blocksize):
        """Return the content as an iterator, emulating ``iter_content``."""
        i = self.response.app_iter
        if type(i) == list:
            return iter(i)
        else:
            return i

    def iter_lines(self):
        for line in self.content.splitlines():
            yield line + b'\n'

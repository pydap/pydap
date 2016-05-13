from webob.request import Request
from webob.exc import HTTPError

from six.moves.urllib.parse import urlsplit, urlunsplit

def GET(url, application=None):
    """Open a remote URL returning a webob.response.Response object

    Optionally open a URL to a local WSGI application
    """
    if application:
        _, _, path, query, fragment = urlsplit(url)
        url = urlunsplit(('', '', path, query, fragment))
    return Request.blank(url).get_response(application)

def raise_for_status(response):
    if response.status_code >= 400:
        raise HTTPError(
            detail=response.status,
            headers=response.headers,
            comment=response.body
        )

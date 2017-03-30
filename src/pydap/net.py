from webob.request import Request
from webob.exc import HTTPError
from contextlib import closing
from requests.exceptions import MissingSchema

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
        url = urlunsplit(('', '', path, query, fragment))

    return follow_redirect(url, application=application, session=session)


def raise_for_status(response):
    if response.status_code >= 400:
        raise HTTPError(
            detail=response.status,
            headers=response.headers,
            comment=response.body
        )


def follow_redirect(url, application=None, session=None):
    """
    This function essentially performs the following command:
    >>> Request.blank(url).get_response(application)

    It however makes sure that the request possesses the same cookies and
    headers as the passed session.
    """

    if session is None:
        session = requests.Session()
    scheme, netloc, path, query, fragment = urlsplit(url)
    domain = urlunsplit((scheme, netloc, '', '', ''))
    session.mount(domain, wsgiadapter.WSGIAdapter(application))
    resp = session.get(url)
    session.unmount(domain, requests.HTTPAdapter())
    return resp

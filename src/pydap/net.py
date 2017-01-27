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

    req = create_request(url, session=session)
    return req.get_response(application)


def create_request(url, session=None):
    if session is not None:
        try:
            # Use session to follow redirects:
            with closing(session.head(url)) as head:
                req = Request.blank(head.url)

                # Get cookies from head:
                cookies_dict = head.cookies.get_dict()

                # Set request cookies to the head cookies:
                req.headers['Cookie'] = ','.join(name + '=' +
                                                 cookies_dict[name]
                                                 for name in cookies_dict)
                # Set the headers to the session headers:
                for item in head.request.headers:
                    req.headers[item] = head.request.headers[item]
                return req
        except MissingSchema:
            # Missing schema can occur in tests when the url
            # is not pointing to any resource. Simply pass.
            pass
    return Request.blank(url)

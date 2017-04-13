from webob.request import Request
from webob.exc import HTTPError
from contextlib import closing
from requests.exceptions import MissingSchema

from six.moves.urllib.parse import urlsplit, urlunsplit

from .lib import DEFAULT_TIMEOUT


def GET(url, application=None, session=None, timeout=DEFAULT_TIMEOUT):
    """Open a remote URL returning a webob.response.Response object

    Optional parameters:
    session: a requests.Session() object (potentially) containing
             authentication cookies.

    Optionally open a URL to a local WSGI application
    """
    if application:
        _, _, path, query, fragment = urlsplit(url)
        url = urlunsplit(('', '', path, query, fragment))

    return follow_redirect(url, application=application, session=session,
                           timeout=timeout)


def raise_for_status(response):
    if response.status_code >= 400:
        raise HTTPError(
            detail=response.status,
            headers=response.headers,
            comment=response.body
        )


def follow_redirect(url, application=None, session=None,
                    timeout=DEFAULT_TIMEOUT):
    """
    This function essentially performs the following command:
    >>> Request.blank(url).get_response(application)  # doctest: +SKIP

    It however makes sure that the request possesses the same cookies and
    headers as the passed session.
    """

    req = create_request(url, session=session, timeout=timeout)
    return req.get_response(application)


def create_request(url, session=None, timeout=DEFAULT_TIMEOUT):
    req = Request.blank(url)
    if session is not None:
        # If session is set and cookies were loaded using pydap.cas.get_cookies
        # using the check_url option, then we can legitimately expect that
        # the connection will go through seamlessly. However, there might be
        # redirects that might want to modify the cookies. Webob is not
        # really up to the task here. The approach used here is to
        # piggy back on the requests library and use it to fetch the
        # head of the requested url. Requests will follow redirects and
        # adjust the cookies as needed. We can then use the final url and
        # the final cookies to set up a webob Request object that will
        # be guaranteed to have all the needed credentials:
        try:
            # Use session to follow redirects:
            with closing(session.head(url, timeout=timeout)) as head:
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
        except MissingSchema:
            # Missing schema can occur in tests when the url
            # is not pointing to any resource. Simply pass.
            pass
        except requests.exceptions.Timeout:
            raise HTTPError('Timeout')
    req.environ['webob.client.timeout'] = timeout
    return req

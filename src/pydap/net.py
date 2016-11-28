from webob.request import Request
from webob.exc import HTTPError

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


def follow_redirect(url, application=None, session=None,
                    cookies_dict=None):
    """
    This function essentially performs the following command:
    >>> Request.blank(url).get_response(application)

    It however makes sure that the request possesses the same cookies and
    headers as the passed session.

    It recursively follows 302 redirects.
    """
    req = Request.blank(url)

    if session is not None:
        # Get cookies from session:
        if cookies_dict is None:
            cookies_dict = session.cookies.get_dict()

        # Set request cookies to the session cookies:
        req.headers['Cookie'] = ','.join(name + '=' + cookies_dict[name]
                                         for name in cookies_dict)
        # Set the headers to the session headers:
        for item in session.headers:
            req.headers[item] = session.headers[item]

    res = req.get_response(application)

    if res.status_code == 302:
        # Follow redirect:
        new_cookies = dict(item.split(';')[0].split('=')
                           for name, item in res.headerlist
                           if name == 'Set-Cookie')
        if len(new_cookies) > 0:
            # If new cookies, keep only these ones:
            cookies_dict = new_cookies
        return follow_redirect(res.location,
                               application=application,
                               session=session,
                               cookies_dict=cookies_dict)
    else:
        return res

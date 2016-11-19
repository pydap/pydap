from webob.request import Request
from webob.exc import HTTPError

from six.moves.urllib.parse import urlsplit, urlunsplit

# Should HTTPS require a valid certificate? Setting this to True will cause
# sites with self-signed certificates to fail; False will enable HTTPS to 
#  work with those sites. jhrg 4/22/15
SSL_VALIDATE = True

def GET(url, application=None, ssl_validate=True):
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

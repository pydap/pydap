import re
from urlparse import urlsplit, urlunsplit
import logging

import httplib2
from pydap.util import socks
httplib2.socks = socks

import pydap.lib
from pydap.exceptions import ServerError


log = logging.getLogger('pydap')


def request(url):
    """
    Open a given URL and return headers and body.

    This function retrieves data from a given URL, returning the headers
    and the response body. Authentication can be set by adding the
    username and password to the URL; this will be sent as clear text
    only if the server only supports Basic authentication.

    """
    h = httplib2.Http(cache=pydap.lib.CACHE,
            timeout=pydap.lib.TIMEOUT,
            proxy_info=pydap.lib.PROXY)
    scheme, netloc, path, query, fragment = urlsplit(url)
    if '@' in netloc:
        credentials, netloc = netloc.split('@', 1)  # remove credentials from netloc
        username, password = credentials.split(':', 1)
        h.add_credentials(username, password)

    url = urlunsplit((
            scheme, netloc, path, query, fragment
            )).rstrip('?&')

    log.info('Opening %s' % url)
    resp, data = h.request(url, "GET", headers = {
        'user-agent': pydap.lib.USER_AGENT,
        'connection': 'close'})

    # When an error is returned, we parse the error message from the
    # server and return it in a ``ClientError`` exception.
    if resp.get("content-description") in ["dods_error", "dods-error"]:
        m = re.search('code = (?P<code>[^;]+);\s*message = "(?P<msg>.*)"',
                data, re.DOTALL | re.MULTILINE)
        msg = 'Server error %(code)s: "%(msg)s"' % m.groupdict()
        raise ServerError(msg)

    return resp, data

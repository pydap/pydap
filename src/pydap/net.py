import ssl

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, Timeout
from requests.utils import urlparse, urlunparse
from urllib3 import Retry
from webob.request import Request

from .lib import DEFAULT_TIMEOUT, _quote


def GET(url, application=None, session=None, timeout=DEFAULT_TIMEOUT, verify=True):
    """Open a remote URL returning a webob.response.Response object

    Optional parameters:
    session: a requests.Session() object (potentially) containing
             authentication cookies.

    Optionally open a URL to a local WSGI application
    """
    if application:
        _, _, path, _, query, fragment = urlparse(url)
        url = urlunparse(("", "", path, "", _quote(query), fragment))

    if session is None:
        session = requests.Session()

    req = create_request(
        url, application=application, session=session, timeout=timeout, verify=verify
    )
    response = get_response(req, application, verify=verify)
    # # Decode request response (i.e. gzip)
    # response.decode_content()
    return response


def get_response(req, application=None, verify=True):
    """
    If verify=False, use the ssl library to temporarily disable
    ssl verification.
    """
    if verify:
        if application:
            resp = req.get_response(application)
        else:
            # this is a remote request
            return req
    else:
        # Here, we use monkeypatching. Webob does not provide a way
        # to bypass SSL verification.
        # This approach is never ideal but it appears to be the only option
        # here.
        # This only works in python 2.7 and >=3.5. Python 3.4
        # does not require it because by default contexts are not
        # verified.
        try:
            _create_default_https_ctx = ssl._create_default_https_context
            _create_unverified_ctx = ssl._create_unverified_context
            ssl._create_default_https_context = _create_unverified_ctx
        except AttributeError:
            _create_default_https_ctx = None

        try:
            if application:
                # local dataset, webob request.
                resp = req.get_response(application)
            else:
                # this is a remote request
                return req
        finally:
            if _create_default_https_ctx is not None:
                # Restore verified context
                ssl._create_default_https_context = _create_default_https_ctx
    return resp


def create_request(
    url,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
):
    """
    Creates a requests.get request object for a local or remote url.
    If application is set, then we are dealing with a local application
    and we need to create a webob request object. Otherwise, we
    are dealing with a remote url and we need to create a requests
    request object.

    If session is set and cookies were loaded using pydap.cas.get_cookies
    using the check_url option, then we can legitimately expect that
    the connection will go through seamlessly. The request library handles
    redirects automatically and adjust the cookies as needed. We can then use
    the final url and the final cookies to set up a requests's Request object
    that will be guaranteed to have all the needed credentials:
    """
    try:
        if application:
            # local dataset, webob request.
            req = Request.blank(url)
            req.environ["webob.client.timeout"] = timeout
        else:
            # we pass any cookies, headers, if session has these attrs
            keys = ["cookies", "headers"]
            kwargs = {k: getattr(session, k) for k in keys if hasattr(session, k)}
            args = {**kwargs, "timeout": timeout, "verify": verify}
            session = requests.Session()

            retries = Retry(
                total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            req = session.get(url, **args)
            try:
                req.raise_for_status()
            except HTTPError as e:
                raise e
        return req
    except Timeout:
        raise HTTPError("Timeout")
    except ConnectionError as ce:
        print(ce)

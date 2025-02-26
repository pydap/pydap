import ssl

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from requests.utils import urlparse, urlunparse
from urllib3 import Retry
from webob.request import Request as webob_Request
from webob.response import Response as webob_Response

from .lib import DEFAULT_TIMEOUT, _quote


def GET(
    url,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    **retry_args,
):
    """Open a remote URL returning a requests.GET object

    Parameters:
    -----------
        url: str
            open a remote URL
        application: a WSGI application object | None
            When set, we are dealing with a local application, and a webob.response is
            returned. When None, a requests.Response object is returned.
        session: requests.Session() | None
            object (potentially) containing authentication cookies.
        timeout: int | None (default: 512)
            timeout in seconds.
        verify: bool (default: True)
            verify SSL certificates
        retry_args: dict
            retry arguments passed to HTTPAdapter

    Returns:
        response: requests.Response object | webob.Response object
    """
    if application:
        _, _, path, _, query, fragment = urlparse(url)
        url = urlunparse(("", "", path, "", _quote(query), fragment))

    res = create_request(
        url,
        application=application,
        session=session,
        timeout=timeout,
        verify=verify,
        **retry_args,
    )
    if isinstance(res,  webob_Request):
        res = get_response(res, application, verify=verify)
        # requests library automatically decodes the response
        res.decode_content()
    return res


def get_response(req, application=None, verify=True):
    """
    If verify=False, use the ssl library to temporarily disable
    ssl verification.
    """
    if verify:
        resp = req.get_response(application)
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
            resp = req.get_response(application)
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
    **retry_args,
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

    if application:
        # local dataset, webob request.
        req = webob_Request.blank(url)
        req.environ["webob.client.timeout"] = timeout
        return req
    else:
        # we pass any cookies, headers, if session has these attrs
        args = {"timeout": timeout, "verify": verify}
        if session:
            # get any cookies and headers from previous session
            keys = ["cookies", "headers"]
            kwargs = {k: getattr(session, k) for k in keys if hasattr(session, k)}
            args = {**kwargs, **args}
        else:
            args = {"headers": {"Connection": "close"}, **args}
        # parse any retry arguments passed to HTTPAdapter
        # and create a Retry object.
        # Create some default values in case NONE are passed:
        if "total" not in retry_args:
            retry_args["total"] = 5
        if "status_forcelist" not in retry_args:
            retry_args["status_forcelist"] = [500, 502, 503, 504]
        if "backoff_factor" not in retry_args:
            retry_args["backoff_factor"] = 0.1
        if "allows_methods" not in retry_args:
            retry_args["allowed_methods"] = ["GET"]
        retries = Retry(**retry_args)
        adapter = HTTPAdapter(max_retries=retries)
        # create new session
        session = requests.Session()
        # mount the adapter to the session
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        # move session get into try
        # otherwise it does not get the last exception
        req = session.get(url, **args, allow_redirects=True)
        try:
            req.raise_for_status()
            return req
        except HTTPError as http_err:
            raise HTTPError(
                f"HTTP Error occurred {http_err} - Failed to fetch data from `{url}`"
            ) from http_err

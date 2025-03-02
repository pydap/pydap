import ssl

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from requests.utils import urlparse, urlunparse
from urllib3 import Retry
from webob.request import Request as webob_Request

from .lib import DEFAULT_TIMEOUT, _quote


def GET(
    url,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    **kwargs,
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
        kwargs: dict
            additional keyword arguments passed to `requests.get`. Optional arguments
            include `retry_args` and `session_kwargs`, which are only passed to the
            session object iff session is None.

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
        **kwargs,
    )
    if isinstance(res, webob_Request):
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
    **kwargs,
):
    """
    Creates a requests.get request object for a local or remote url.
    If application is set, then we are dealing with a local application
    and we need to create a webob request object. Otherwise, we
    are dealing with a remote url and we need to create a requests
    request object.

    Parameters:
    -----------
        url: str
            open a remote URL
        application: a WSGI application object | None
            When set, we are dealing with a local application, and a webob.response is
            returned. When None, a requests.Response object is returned.
        session: requests.Session() | None
        timeout: int | None (default: 512)
            timeout in seconds.
        verify: bool (default: True)
            verify SSL certificates
        kwargs: dict
            additional keyword arguments passed to `requests.get`. Optional arguments
            include `retry_args` and `session_kwargs`, which are only passed to the
            session object iff session is None.
    """

    if application:
        # local dataset, webob request.
        req = webob_Request.blank(url)
        req.environ["webob.client.timeout"] = timeout
        return req
    else:
        session_kwargs = kwargs.pop(
            "session_kwargs", {}
        )  # Extract session-specific kwargs
        if session is None:
            # Create a new session with user-specified kwargs
            session = requests.Session()
            for key, value in session_kwargs.items():
                setattr(session, key, value)

            # Handle retry arguments separately
            retry_args = kwargs.pop("retry_args", {})
            retry_args.setdefault("total", 5)
            retry_args.setdefault("status_forcelist", [500, 502, 503, 504])
            retry_args.setdefault("backoff_factor", 0.1)
            retry_args.setdefault("allowed_methods", ["GET"])

            retries = Retry(**retry_args)
            adapter = HTTPAdapter(max_retries=retries)

            # Mount the adapter to the session
            session.mount("http://", adapter)
            session.mount("https://", adapter)
        req = session.get(
            url, timeout=timeout, verify=verify, allow_redirects=True, **kwargs
        )
        try:
            req.raise_for_status()
            return req
        except HTTPError as http_err:
            raise HTTPError(
                f"HTTP Error occurred {http_err} - Failed to fetch data from `{url}`"
            ) from http_err

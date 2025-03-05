import ssl
import warnings

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from requests.utils import urlparse, urlunparse
from requests_cache import CachedSession
from urllib3 import Retry
from webob.request import Request as webob_Request

from .lib import DEFAULT_TIMEOUT, _quote


def GET(
    url,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    **get_kwargs,
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
        session_kwargs: dict | None
            keyword arguments used to create a new session object. Only used if
            session is None.
        cache_kwargs: dict | None
            keyword arguments used to create a new cache object. Only used if
            use_cache is True.
        get_kwargs: dict
            additional keyword arguments passed to `requests.get`.

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
        use_cache=use_cache,
        session_kwargs=session_kwargs,
        cache_kwargs=cache_kwargs,
        **get_kwargs,
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
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    **get_kwargs,
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
        use_cache: bool (default: False)
            use cache to store requests. Uses the `requests_cache` library.
        session_kwargs: dict | None
            keyword arguments used to create a new session object. Only used if
            session is None.
        cache_kwargs: dict | None
            keyword arguments used to create a new cache object. Only used if
            use_cache is True.
        get_kwargs: dict
            additional keyword arguments passed to `requests.get`.
    """

    if application:
        # local dataset, webob request.
        req = webob_Request.blank(url)
        req.environ["webob.client.timeout"] = timeout
        return req
    else:
        # remote dataset, requests request.
        if session is None:
            session_kwargs = session_kwargs or {}
            cache_kwargs = cache_kwargs or {}
            if use_cache:
                session = CachedSession(**{**session_kwargs, **cache_kwargs})
            else:
                if len(cache_kwargs) > 0:
                    warnings.warn(
                        "`cache_kwargs` are being set, but use_cache is `False`. "
                        " when `use_cache` is `False`, `cache_kwargs` are ignored."
                        " set `use_cache` to `True` to use `cache_kwargs`, or remove "
                        "`cache_kwargs`. ",
                        category=UserWarning,
                        stacklevel=1,
                    )
                # Create a new session with user-specified kwargs
                session = requests.Session()
                for key, value in session_kwargs.items():
                    setattr(session, key, value)
            # Handle retry arguments separately
            retry_args = session_kwargs.pop("retry_args", {})
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
            url, timeout=timeout, verify=verify, allow_redirects=True, **get_kwargs
        )
        try:
            req.raise_for_status()
            return req
        except HTTPError as http_err:
            raise HTTPError(
                f"HTTP Error occurred {http_err} - Failed to fetch data from `{url}`"
            ) from http_err

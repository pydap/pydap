import ssl
from contextlib import closing

import requests
from requests.exceptions import InvalidSchema, MissingSchema, Timeout
from requests.utils import urlparse, urlunparse
from webob.exc import HTTPError
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

    response = follow_redirect(
        url, application=application, session=session, timeout=timeout, verify=verify
    )
    # Decode request response (i.e. gzip)
    response.decode_content()
    return response


def raise_for_status(response):
    # Raise error if status is above 300:
    if response.status_code >= 400:
        raise HTTPError(
            detail=response.status + "\n" + response.text,
            headers=response.headers,
            comment=response.body,
        )
    elif response.status_code >= 300:
        try:
            text = response.text
        except AttributeError:
            # With this status_code, response.text could
            # be ill-defined. If the redirect does not set
            # an encoding (i.e. response.charset is None).
            # Set the text to empty string:
            text = ""
        raise HTTPError(
            detail=(
                response.status
                + "\n"
                + text
                + "\n"
                + "This is redirect error. These should not usually raise "
                + "an error in pydap beacuse redirects are handled "
                + "implicitly. If it failed it is likely due to a "
                + "circular redirect."
            ),
            headers=response.headers,
            comment=response.body,
        )


def follow_redirect(
    url, application=None, session=None, timeout=DEFAULT_TIMEOUT, verify=True
):
    """
    This function essentially performs the following command:
    >>> Request.blank(url).get_response(application)  # doctest: +SKIP

    It however makes sure that the request possesses the same cookies and
    headers as the passed session.
    """

    req = create_request(url, session=session, timeout=timeout, verify=verify)
    return get_response(req, application, verify=verify)


def get_response(req, application, verify=True):
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


def create_request(url, session=None, timeout=DEFAULT_TIMEOUT, verify=True):
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
        return create_request_from_session(url, session, timeout=timeout, verify=verify)
    else:
        # If a session object was not passed, we simply pass a new
        # requests.Session() object. The requests library allows the
        # handling of redirects that are not naturally handled by Webob.
        return create_request_from_session(
            url, requests.Session(), timeout=timeout, verify=verify
        )


def create_request_from_session(url, session, timeout=DEFAULT_TIMEOUT, verify=True):
    try:
        # Use session to follow redirects:
        with closing(
            session.head(url, allow_redirects=True, timeout=timeout, verify=verify)
        ) as head:
            req = Request.blank(head.url)
            req.environ["webob.client.timeout"] = timeout

            # Get cookies from head:
            cookies_dict = head.cookies.get_dict()

            # Set request cookies to the head cookies:
            req.headers["Cookie"] = ",".join(
                name + "=" + cookies_dict[name] for name in cookies_dict
            )
            # Set the headers to the session headers:
            for item in head.request.headers:
                req.headers[item] = head.request.headers[item]
            return req
    except (MissingSchema, InvalidSchema):
        # Missing schema can occur in tests when the url
        # is not pointing to any resource. Simply pass.
        req = Request.blank(url)
        req.environ["webob.client.timeout"] = timeout
        return req
    except Timeout:
        raise HTTPError("Timeout")

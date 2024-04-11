from . import get_cookies


def setup_session(username, password, **EARTHDATA_kwargs):
    """
    A special call to get_cookies.setup_session that is tailored for
    URS EARTHDATA at NASA credentials.

    Parameters:
    ----------
    username: str
    password: str
    check_url: str, None (default)
    session: `requests.session`
    verify: bool, True (default)

    Example:
    see `https://opendap.github.io/documentation/tutorials/`

    """
    check_url, session, verify = None, None, None
    if check_url in EARTHDATA_kwargs.keys():
        check_url = EARTHDATA_kwargs.pop("check_url", None)
    if session in EARTHDATA_kwargs.keys():
        session = EARTHDATA_kwargs.pop("session", None)
    if verify in EARTHDATA_kwargs.keys():
        verify = EARTHDATA_kwargs.pop("verify", None)

    if session is not None:
        # URS connections cannot be kept alive at the moment.
        session.headers.update({"Connection": "close"})
    session = get_cookies.setup_session(
        "https://urs.earthdata.nasa.gov",
        username=username,
        password=password,
        session=session,
        check_url=check_url,
        verify=verify,
    )
    return session

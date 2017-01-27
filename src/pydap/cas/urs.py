from . import get_cookies


def setup_session(username, password, check_url=None,
                  session=None, verify=True):
    """
    A special call to get_cookies.setup_session that is tailored for
    URS EARTHDATA at NASA credentials.

    """
    if session is not None:
        # URS connections cannot be kept alive at the moment.
        session.headers.update({'Connection': 'close'})
    session = get_cookies.setup_session('https://urs.earthdata.nasa.gov',
                                        username=username,
                                        password=password,
                                        session=session,
                                        check_url=check_url,
                                        verify=verify)
    return session

from . import get_cookies


def setup_session(username, password, check_url=None,
                  session=None):
    """
    A special call to get_cookies.setup_session that is tailored for
    URS EARTHDATA at NASA credentials.

    """
    return get_cookies.setup_session('https://urs.earthdata.nasa.gov',
                                     username=username,
                                     password=password,
                                     session=session,
                                     check_url=check_url)

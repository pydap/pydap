from . import get_cookies


def setup_session(username, password, check_url=None):
    """
    A special call to get_cookies.setup_session that is tailored for
    URS EARTHDATA at NASA credentials.

    """
    return get_cookies.setup_session('https://urs.earthdata.nasa.gov',
                                     username,
                                     password,
                                     check_url=check_url)

from . import get_cookies


def setup_session(
    username=None, password=None, check_url=None, session=None, verify=True, netrc=True
):
    """
    A special call to get_cookies.setup_session that is tailored for
    URS EARTHDATA at NASA credentials. By default, a .netrc file is
    expected for authentication credentials. Auth credentials in a
    .netrc fule take precedence over any manually defined ones.

    Parameters:
    ----------
    username: str | None (default)
    password: str | None (default)
    check_url: str, None (default)
    session: `requests.session`, None (default)
    verify: bool, True (default)
    netrc: bool, True (default)

    Example Data Access and Authentification in:
    see `https://opendap.github.io/documentation/tutorials/`

    """

    if netrc:
        credentials = get_cookies.read_netrc()
        try:
            machine = "urs.earthdata.nasa.gov"
            login, passw = (
                credentials[machine]["username"],
                credentials[machine]["password"],
            )
        except KeyError:
            if isinstance(username, str) and isinstance(password, str):
                login, passw = username, password
            else:
                raise ValueError

    else:
        if isinstance(username, str) and isinstance(password, str):
            login, passw = username, password
        else:
            raise ValueError

    if session is not None:
        # URS connections cannot be kept alive at the moment.
        session.headers.update({"Connection": "close"})

    session = get_cookies.setup_session(
        "https://urs.earthdata.nasa.gov",
        username=login,
        password=passw,
        session=session,
        check_url=check_url,
        verify=verify,
    )
    return session

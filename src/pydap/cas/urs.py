from warnings import warn


def setup_session(username, password, check_url=None, session=None, verify=True):
    """
    This function is deprecated and will be removed in version 1.0.0.
    Please use new_function instead.
    """
    warn(
        "`urs.setup_session` is deprecated. "
        "Instead, use a `.netrc` file instead for your EDL authentication credentials."
        "With the `.netrc file`, authentication with URS EARTHDATA at NASA credentials"
        "is now handled automatically by requests.session object. "
        "See: \n"
        "https://opendap.github.io/documentation/tutorials/ClientAuthentication.html",
        DeprecationWarning,
        stacklevel=2,
    )
    pass

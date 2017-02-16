import mechanicalsoup
import warnings
import requests
from requests.packages.urllib3.exceptions import (InsecureRequestWarning,
                                                  InsecurePlatformWarning)
import copy
from ..lib import __version__ as pydap__version__

ssl_verify_categories = [InsecureRequestWarning,
                         InsecurePlatformWarning]


def setup_session(uri,
                  username=None,
                  password=None,
                  check_url=None,
                  session=None,
                  verify=True,
                  username_field='username',
                  password_field='password'):
    '''
    A general function to set-up requests session with cookies
    using mechanicalsoup and by calling the right url.
    '''

    if session is None:
        # Connections must be closed since some CAS
        # will cough when connections are kept alive:
        headers = [('User-agent', 'Pydap/{}'.format(pydap__version__)),
                   ('Connection', 'close')]
        session = requests.Session()
        session.headers.update(headers)

    if uri is None:
        return session

    if not verify:
        verify_flag = session.verify
        session.verify = False
    br = mechanicalsoup.Browser(session=session)

    if isinstance(uri, str):
        url = uri
    else:
        url = uri(check_url)

    if password is None or password == '':
        warnings.warn('password was not set. '
                      'this was likely unintentional '
                      'but will result is much fewer datasets.')
        if not verify:
            session.verify = verify_flag
        return session

    # Allow for several subsequent security layers:
    full_url = copy.copy(uri)
    if isinstance(full_url, list):
        url = full_url[0]

    with warnings.catch_warnings():
        if not verify:
            # Catch warnings. It is assumed that the
            # user that explicitly uses verify=False
            # is either fully aware of the risks
            # or cannot avoid the risks because of
            # an improperly configured server.
            # This error will usually occur with
            # ESGF authentication.
            for category in ssl_verify_categories:
                warnings.filterwarnings("ignore",
                                        category=category)

        response = mechanicalsoup_login(br, url, username, password,
                                        username_field=username_field,
                                        password_field=password_field)

        # If there are further security levels.
        # At the moment only used for CEDA OPENID:
        if (isinstance(full_url, list) and
           len(full_url) > 1):
            for url in full_url[1:]:
                response = mechanicalsoup_login(br, response.url,
                                                username, password,
                                                username_field=username_field,
                                                password_field=password_field)
        response.close()

        if check_url:
            if (username is not None and
               password is not None):
                res = session.get(check_url, auth=(username, password))
                if res.status_code == 401:
                    res = session.get(res.url, auth=(username, password))
                res.close()
            raise_if_form_exists(check_url, session)

    if not verify:
        session.verify = verify_flag
    return session


def raise_if_form_exists(url, session):
    """
    This function raises a UserWarning if the link has forms
    """

    user_warning = ('Navigate to {0}, '.format(url) +
                    'login and follow instructions. '
                    'It is likely that you have to perform some one-time'
                    'registration steps before acessing this data.')

    # This is important for the python 2.6 build:
    try:
        from six.moves.html_parser import HTMLParseError
    except ImportError:
        # HTMLParseError is removed in Python 3.5. Since it can never be
        # thrown in 3.5, we can just define our own class as a placeholder.
        # *from bs4/builder/_htmlparser.py
        class HTMLParseError(Exception):
            pass

    br = mechanicalsoup.Browser(session=session)
    try:
        login_page = br.get(url)
    except HTMLParseError:
        # This is important for the python 2.6 build:
        raise UserWarning(user_warning)

    if ((hasattr(login_page, 'soup') and
       len(login_page.soup.select('form')) > 0)):
        raise UserWarning(user_warning)


def mechanicalsoup_login(br, url, username, password,
                         username_field='username',
                         password_field='password'):
    login_page = br.get(url)

    if not hasattr(login_page, 'soup'):
        return login_page

    try:
        login_form = login_page.soup.select('form')[0]
    except IndexError:
        # There are no login form.
        # Assume that we are logged-in
        return login_page

    try:
        login_form.select('#' + username_field)[0]['value'] = username
    except IndexError:
        # There might not need a username (e.g. ESGF)
        pass

    try:
        login_form.select('#' + password_field)[0]['value'] = password
    except IndexError:
        # If there is no password_field, it might be because
        # something should be handled in the browser
        # for the first attempt. This is common when using
        # pydap with the ESGF for the first time.
        raise Exception('Navigate to {0}. '
                        'If you are unable to '
                        'login, you must either '
                        'wait or use authentication '
                        'from another service.'
                        .format(url))

    # This is specific for CEDA OPENID:
    try:
        login_form.find("remember").items[0].selected = True
    except AttributeError:
        pass
    return br.submit(login_form, login_page.url)

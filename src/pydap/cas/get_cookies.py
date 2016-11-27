import mechanicalsoup
import warnings
import requests
from requests.packages.urllib3.exceptions import (InsecureRequestWarning,
                                                  InsecurePlatformWarning)
import copy
import pydap.lib

ssl_verify_categories = [InsecureRequestWarning,
                         InsecurePlatformWarning]


def setup_session(uri, username, password, check_url=None,
                  session=None, verify=True,
                  username_field='username',
                  password_field='password'):
    '''
    A general function to set-up requests session with cookies
    using mechanicalsoup and by calling the right url.
    '''

    if session is None:
        headers = [('User-agent', pydap.lib.__version__)]
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
        if (isinstance(full_url, list) and
           len(full_url) > 1):
            # If there are further security levels:
            for url in full_url[1:]:
                response = mechanicalsoup_login(br, response.url,
                                                username, password,
                                                username_field=username_field,
                                                password_field=password_field)
        response.close()

        if check_url:
            res = session.get(check_url, auth=(username, password))
            if res.status_code == 401:
                res = session.get(res.url, auth=(username, password))
        res.close()
    if not verify:
        session.verify = verify_flag
    return session


def mechanicalsoup_login(br, url, username, password,
                         username_field='username',
                         password_field='password'):
    login_page = br.get(url)

    login_form = login_page.soup.select('form')[0]

    try:
        login_form.select('#' + username_field)[0]['value'] = username
    except IndexError:
        pass

    try:
        login_form.select('#' + password_field)[0]['value'] = password
    except IndexError:
        pass
    #    if url is not None:
    #        br.close()
        raise Exception('Navigate to {0}. '
                        'If you are unable to '
                        'login, you must either '
                        'wait or use authentication '
                        'from another service.'
                        .format(url))
    #    else:
    #        pass

    try:
        login_form.find("remember").items[0].selected = True
    except AttributeError:
        pass
    return br.submit(login_form, login_page.url)

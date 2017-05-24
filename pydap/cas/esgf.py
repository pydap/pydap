from six.moves.urllib.parse import quote_plus
from . import get_cookies


def setup_session(openid, password, username=None,
                  check_url=None,
                  session=None, verify=False):
    """
    A special call to get_cookies.setup_session that is tailored for
    ESGF credentials.

    username should only be necessary for a CEDA openid.
    """
    session = get_cookies.setup_session(_uri(openid),
                                        username=username,
                                        password=password,
                                        check_url=check_url,
                                        session=session,
                                        verify=verify)
    # Connections can be kept alive on the ESGF:
    session.headers.update([('Connection', 'keep-alive')])
    return session


def _uri(openid):
    '''
    Create ESGF authentication url.
    This function might be sensitive to a
    future evolution of the ESGF security.
    '''
    def generate_url(dest_url):
        dest_node = _get_node(dest_url)

        try:
            url = (dest_node +
                   '/esg-orp/j_spring_openid_security_check.htm?'
                   'openid_identifier=' +
                   quote_plus(openid))
        except TypeError:
            raise UserWarning('OPENID was not set. '
                              'ESGF connection cannot succeed.')
        if _get_node(openid) == 'https://ceda.ac.uk':
            return [url, None]
        else:
            return url
    return generate_url


def _get_node(url):
        return '/'.join(url.split('/')[:3]).replace('http:', 'https:')

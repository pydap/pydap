"""
LGPL License
Copyright (c) 2015
All rights reserved.

PyDAP extension to enable access to OpenDAP servers that 
require login using NASA URS. This code will actually provide
credentials to any server that uses a 401 response to ask for
them. Of course, HTTP Basic authentication sends the information
in the clear, so HTTPS should always be used by the server.

@author: James Gallagher <jgallagher@opendap.org>

"""

import cookielib
import netrc
import urllib2
import re

import pydap.lib
from pydap.exceptions import ClientError

import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Set the debug level for urllib2.
debuglevel=1

def install_basic_client(uri='', user='', passwd='', use_netrc=True):
    """
    Based on the CAS authentication example at
    http://pydap.org/client.html#authentication

    Handle URS/OAuth2, and HTTP Basic authentication over https.
    
    To use this, you must run this function before importing the open_url()
    function contained in pydap.client. One run, the pydap.http.request()
    function will search a password manager for username/password pairs using
    information passed to this function and/or from the caller's .netrc file.
    When a HTTP request returns a authentication challenge response (401 
    response code), this new request() function will search for credentials
    that match the request's hostname (i.e., 'uri').
    
    This code knows how to follow the redirects associated with the NASA URS
    system, an implementation of OAuth2.

    :param uri: If all of uri, user and passwd are not empty, add them to the password manager.
    :param user: See uri
    :param passwd: See uri
    :param netrc: If True, the default, read login credentials from the .netrc file
    
    """

    # Create special opener with support for Cookies
    cj = cookielib.CookieJar()
    
    # Create the password manager and load with the credentials using 
    pwMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

    # Get passwords from the .netrc file nless use_netrc is False    
    if use_netrc:
        logins = netrc.netrc()
        accounts = logins.hosts # a dist of hosts and tuples
        for host, info in accounts.iteritems():
            login, account, password = info
            log.debug('Host: %s; login: %s; account: %s; password: %s' % (host, login, account, password))
            pwMgr.add_password(None, host, login, password)
        
    if uri and user and passwd:
        pwMgr.add_password(None, uri, user, passwd)
    
    opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(pwMgr),
                                  urllib2.HTTPCookieProcessor(cj))
    
    opener.addheaders = [('User-agent', pydap.lib.USER_AGENT)]

    urllib2.install_opener(opener)

    def new_request(url):
        log.debug('Opening %s (install_basic_client)' % url)
        r = urllib2.urlopen(url)
        
        resp = r.headers.dict
        resp['status'] = str(r.code)
        data = r.read()

        # When an error is returned, we parse the error message from the
        # server and return it in a ``ClientError`` exception.
        if resp.get("content-description") == "dods_error":
            m = re.search('code = (?P<code>\d+);\s*message = "(?P<msg>.*)"',
                    data, re.DOTALL | re.MULTILINE)
            msg = 'Server error %(code)s: "%(msg)s"' % m.groupdict()
            raise ClientError(msg)

        return resp, data

    from pydap.util import http
    http.request = new_request


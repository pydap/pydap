"""Pydap error response.

Pydap will capture exceptions returned by the system and return them properly
formated as a DAP error response.

"""

from traceback import print_exception

from webob import Response
from six import StringIO, text_type

from pydap.lib import encode, __version__


class ErrorResponse(object):

    """A specialized response for errors.

    This is a special response used when an exception is captured and passed to
    the user as an Opendap error message:

    """

    def __init__(self, info):
        # get exception message
        buf = StringIO()
        print_exception(*info, file=buf)
        message = encode(buf.getvalue())

        # build error message
        code = getattr(info[0], 'code', -1)
        self.body = text_type('''Error {{
    code = {0};
    message = {1};
}}''').format(code, message)

    def __call__(self, environ, start_response):
        res = Response()
        res.text = self.body
        res.status = '500 Internal Error'
        res.content_type = 'text/plain'
        res.charset = 'utf-8'
        res.headers.add('Content-description', 'dods_error')
        res.headers.add('XDODS-Server', 'pydap/%s' % __version__)

        return res(environ, start_response)

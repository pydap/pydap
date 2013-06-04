from traceback import print_exception
from StringIO import StringIO

from webob import Response

from pydap.lib import encode, __version__


class ErrorResponse(object):
    r"""
    A specialized response for errors.

    This is a special response used when an exception is captured and passed to
    the user as an Opendap error message:

        >>> import sys
        >>> try:
        ...     1/0
        ... except:
        ...     error = ErrorResponse(sys.exc_info())

        >>> from webob import Request
        >>> req = Request.blank('/')
        >>> res = req.get_response(error)
        >>> print res.status
        500 Internal Error
        >>> print res.content_type
        text/plain
        >>> print res.charset
        utf-8
        >>> print res.headers
        ResponseHeaders([('Content-Length', '207'), ('Content-Type', 'text/plain; charset=utf-8'), ('Content-description', 'dods_error'), ('XDODS-Server', 'dods/2.0')])
        >>> print res.body
        Error {
            code = -1;
            message = "Traceback (most recent call last):
          File \"<doctest __main__.ErrorResponse[1]>\", line 2, in <module>
            1/0
        ZeroDivisionError: integer division or modulo by zero
        ";
        }

    """
    def __init__(self, info):
        # get exception message
        buf = StringIO()
        print_exception(*info, file=buf)
        message = encode(buf.getvalue())

        # build error message
        code = getattr(info[0], 'code', -1)
        self.body = r'''Error {{
    code = {};
    message = {};
}}'''.format(code, message)

    def __call__(self, environ, start_response):
        res = Response()
        res.body = self.body
        res.status='500 Internal Error'
        res.content_type = 'text/plain'
        res.charset = 'utf-8'
        res.headers.add('Content-description', 'dods_error')
        res.headers.add('XDODS-Server', 'pydap/%s' % __version__)

        return res(environ, start_response)


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

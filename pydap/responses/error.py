import traceback
from StringIO import StringIO

from pydap.lib import __dap__, INDENT, escape


class ErrorResponse(object):
    def __init__(self, dataset=None, info=None):
        self.info = info 

    def __call__(self, environ, start_response):
        headers = [('Content-description', 'dods_error'),
                   ('XDODS-Server', 'dods/%s' % '.'.join(str(d) for d in __dap__)),
                   ('Content-type', 'text/plain')]

        type_, value, traceback_ = self.info
        f = StringIO()
        traceback.print_exception(type_, value, traceback_, file=f)
        msg = f.getvalue()

        output = ['Error {\n',
                  INDENT, 'code = %s;\n' % getattr(type_, 'code', -1),
                  INDENT, 'message = %s;\n' % escape(msg),
                  '}']

        start_response('500 Internal Error', headers, self.info)
        return output

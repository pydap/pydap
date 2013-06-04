import re
import operator
import ast

from webob import Request
from pkg_resources import iter_entry_points
import numpy as np

from pydap.model import *
from pydap.parsers import parse_ce
from pydap.lib import walk, fix_shorthand
from pydap.handlers.lib import BaseHandler, apply_projection


FUNCTION = re.compile(r'([^(]*)\((.*)\)') 
RELOP = re.compile(r'(<=|<|>=|>|=|!=)')


class ServerSideFunctions(object):

    functions = dict((r.name, r.load())
            for r in iter_entry_points('pydap.function'))

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # specify that we want the parsed dataset
        environ['x-wsgiorg.want_parsed_response'] = True
        req = Request(environ)
        original_query = req.query_string
        projection, selection = parse_ce(req.query_string)

        # apply selection without any function calls
        req.query_string = '&'.join(expr for expr in selection if not FUNCTION.match(expr))
        res = req.get_response(self.app)

        # ignore DAS requests
        path, response = req.path.rsplit('.', 1)
        if response == 'das':
            return self.app(environ, start_response)

        # get the dataset
        method = getattr(res.app_iter, 'x_wsgiorg_parsed_response', False)
        if not method:
            environ['QUERY_STRING'] = original_query
            return self.app(environ, start_response)
        dataset = method(DatasetType)

        # apply selection containing server-side functions
        selection = (expr for expr in selection if FUNCTION.match(expr))
        for expr in selection:
            if RELOP.search(expr):
                call, op, other = RELOP.split(expr)
                op = {
                        '<' : operator.lt,
                        '>' : operator.gt,
                        '!=': operator.ne,
                        '=' : operator.eq,
                        '>=': operator.ge,
                        '<=': operator.le,
                        '=~': lambda a, b: re.match(b, a),
                }[op]
                other = ast.literal_eval(other)
            else:
                call, op, other = expr, operator.eq, 1

            # evaluate the function call
            sequence = eval_function(dataset, call, self.functions)

            # is this an inplace call?
            for var in walk(dataset, SequenceType):
                if sequence is var:
                    break
            else:
                # get the data from the resulting variable, and use it to 
                # constrain the original dataset
                data = np.fromiter(sequence)
                print data.shape
                valid = op(data, other)

                for sequence in walk(dataset, SequenceType):
                    data = np.asarray(list(sequence), 'O')[valid]
                    sequence.data = np.asarray(list(sequence), 'O')[valid]
                dataset = out

        # now apply projection
        if projection:
            projection = fix_shorthand(projection, dataset)
            base = [p for p in projection if not isinstance(p, basestring)] 
            func = [p for p in projection if isinstance(p, basestring)] 

            # apply non-function projection
            out = apply_projection(base, dataset)

            # apply function projection
            for call in func:
                var = eval_function(dataset, call, self.functions)
                for child in walk(var):
                    parent = reduce(operator.getitem, [out] + child.id.split('.')[:-1])
                    if child.name not in parent.keys():
                        parent[child.name] = child
                        break
            dataset = out

        # Return the original response (DDS, DAS, etc.)
        path, response = req.path.rsplit('.', 1)
        res = BaseHandler.responses[response](dataset)

        return res(environ, start_response)


def eval_function(dataset, function, functions):
    name, args = FUNCTION.match(function).groups()

    def tokenize(input):
        start = pos = count = 0
        for char in input:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            elif char == ',' and count == 0:
                yield input[start:pos]
                start = pos+1
            pos += 1
        yield input[start:]

    def parse(token):
        if FUNCTION.match(token):
            return eval_function(dataset, token, functions)
        else:
            try:
                names = [dataset] + re.sub('\[.*?\]', '', str(token)).split('.')
                return reduce(operator.getitem, names)
            except:
                try:
                    return ast.literal_eval(token)
                except:
                    return token

    args = map(parse, tokenize(args))
    func = functions[name]

    return func(dataset, *args)


if __name__ == '__main__':
    import sys
    from paste.httpserver import serve
    #from pydap.handlers.sql import SQLHandler
    from pydap.handlers.netcdf import NetCDFHandler

    #application = SQLHandler(sys.argv[1])
    application = NetCDFHandler(sys.argv[1])
    application = ServerSideFunctions(application)
    serve(application, port=8001)

"""An implementation of server-side functions.

Pydap implements DAP server-side functions throught a custom WSGI middleware.
This simplifies writing custom handlers, since they don't need to parse and
apply the function calls themselves.

"""

import re
import operator
import ast

from webob import Request
from pkg_resources import iter_entry_points
import numpy as np
from six.moves import reduce, map
from six import string_types

from pydap.model import DatasetType, SequenceType
from pydap.parsers import parse_ce
from pydap.lib import walk, fix_shorthand
from pydap.handlers.lib import BaseHandler, apply_projection
from pydap.exceptions import ServerError


FUNCTION = re.compile(r'([^(]*)\((.*)\)')
RELOP = re.compile(r'(<=|<|>=|>|=~|=|!=)')


class ServerSideFunctions(object):

    """A WebOb based middleware for handling server-side function calls.

    The middleware works by removing function calls from the request,
    forwarding the request to Pydap, and then applying the functions calls to
    the returned dataset.

    """

    def __init__(self, app, **kwargs):
        self.app = app

        self.functions = {}
        for r in iter_entry_points("pydap.function"):
            self.functions[r.name] = r.load()
        self.functions.update(kwargs)

    def __call__(self, environ, start_response):
        # specify that we want the parsed dataset
        environ['x-wsgiorg.want_parsed_response'] = True
        req = Request(environ)
        projection, selection = parse_ce(req.query_string)

        # check if there are any functions calls in the request
        called = (
            any(s for s in selection if FUNCTION.match(s)) or
            any(p for p in projection if isinstance(p, string_types)))

        # ignore DAS requests and requests without functions
        path, response = req.path.rsplit('.', 1)
        if response == 'das' or not called:
            return self.app(environ, start_response)

        # apply selection without any function calls
        req.query_string = '&'.join(
            s for s in selection if not FUNCTION.match(s))
        res = req.get_response(self.app)

        # get the dataset
        method = getattr(res.app_iter, 'x_wsgiorg_parsed_response', False)
        if not method:
            raise ServerError("Unable to call server-side function!")
        dataset = method(DatasetType)

        # apply selection containing server-side functions
        selection = (s for s in selection if FUNCTION.match(s))
        for expr in selection:
            if RELOP.search(expr):
                call, op, other = RELOP.split(expr)
                op = {
                    '<':  operator.lt,
                    '>':  operator.gt,
                    '!=': operator.ne,
                    '=':  operator.eq,
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
                child = list(sequence.children())[0]
                data = np.fromiter(child.data, child.dtype)
                if data.dtype.char == "S":
                    valid = np.array(
                        list(map(lambda v: op(str(v), str(other)), data)),
                        bool)
                else:
                    valid = op(data, other)

                for sequence in walk(dataset, SequenceType):
                    sequence.data = np.rec.fromrecords(
                        [tuple(row) for row in sequence],
                        names=sequence.keys())[valid]

        # now apply projection
        if projection:
            projection = fix_shorthand(projection, dataset)
            base = [p for p in projection if not isinstance(p, string_types)]
            func = [p for p in projection if isinstance(p, string_types)]

            # apply non-function projection
            out = apply_projection(base, dataset)

            # apply function projection
            for call in func:
                var = eval_function(dataset, call, self.functions)
                for child in walk(var):
                    parent = reduce(
                        operator.getitem, [out] + child.id.split('.')[:-1])
                    if child.name not in parent.keys():
                        parent[child.name] = child
                        break
            dataset = out

        # Return the original response (DDS, DAS, etc.)
        path, response = req.path.rsplit('.', 1)
        res = BaseHandler.responses[response](dataset)

        return res(environ, start_response)


def eval_function(dataset, function, functions):
    """Evaluate a given function on a dataset.

    This function parses and evaluates a (possibly nested) function call,
    returning its result.

    """
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
                names = re.sub('\[.*?\]', '', str(token)).split('.')
                return reduce(operator.getitem, [dataset] + names)
            except:
                try:
                    return ast.literal_eval(token)
                except:
                    return token

    args = map(parse, tokenize(args))
    func = functions[name]

    return func(dataset, *args)

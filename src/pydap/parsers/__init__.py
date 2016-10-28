"""Parsing related functions.

This module defines functions to parse DAP objects, including a base parser for
DDS and DAS responses.

"""

import re
import operator
import ast

from six.moves.urllib.parse import unquote
from six.moves import map

from pydap.exceptions import ConstraintExpressionError
from pydap.lib import get_var


def parse_projection(input):
    """Split a projection into items.

    The function takes into account server-side functions, and parse slices
    into Python slice objects.

    Returns a list of names and slices.

    """
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
        if '(' not in token:
            token = token.split('.')
            token = [
                re.match('(.*?)(\[.*\])?$', part).groups()
                for part in token]
            token = [
                (name, parse_hyperslab(slice_ or ''))
                for (name, slice_) in token]
        return token

    return list(map(parse, tokenize(input)))


def parse_selection(expression, dataset):
    """Parse a selection expression into its elements.

    This function will parse a selection expression into three tokens: two
    variables or values and a comparison operator. Variables are returned as
    Pydap objects from a given dataset, while values are parsed using
    ``ast.literal_eval``.

    """
    id1, op, id2 = re.split('(<=|>=|!=|=~|>|<|=)', expression, 1)

    op = {
        '<=': operator.le,
        '>=': operator.ge,
        '!=': operator.ne,
        '=': operator.eq,
        '>': operator.gt,
        '<': operator.lt,
    }[op]

    try:
        id1 = get_var(dataset, id1)
    except:
        id1 = ast.literal_eval(id1)

    try:
        id2 = get_var(dataset, id2)
    except:
        id2 = ast.literal_eval(id2)

    return id1, op, id2


def parse_ce(query_string):
    """Extract the projection and selection from the QUERY_STRING.

        >>> parse_ce('a,b[0:2:9],c&a>1&b<2')  # doctest: +NORMALIZE_WHITESPACE
        ([[('a', ())], [('b', (slice(0, 10, 2),))], [('c', ())]],
                ['a>1', 'b<2'])
        >>> parse_ce('a>1&b<2')
        ([], ['a>1', 'b<2'])

    This function can also handle function calls in the URL, according to the
    DAP specification:

        >>> ce = 'time&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'
        >>> print(parse_ce(ce))  # doctest: +NORMALIZE_WHITESPACE
        ([[('time', ())]],
                ['bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'])

        >>> ce = 'time,bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'
        >>> print(parse_ce(ce))  # doctest: +NORMALIZE_WHITESPACE
        ([[('time', ())],
            'bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'], [])
        >>> parse_ce('mean(g,0)')
        (['mean(g,0)'], [])
        >>> parse_ce('mean(mean(g.a,1),0)')
        (['mean(mean(g.a,1),0)'], [])

    Returns a tuple with the projection and the selection.

    """
    tokens = [token for token in unquote(query_string).split('&') if token]
    if not tokens:
        projection = []
        selection = []
    elif re.search('<=|>=|!=|=~|>|<|=', tokens[0]):
        projection = []
        selection = tokens
    else:
        projection = parse_projection(tokens[0])
        selection = tokens[1:]

    return projection, selection


def parse_hyperslab(hyperslab):
    """Parse a hyperslab, returning a Python tuple of slices."""
    exprs = [expr for expr in hyperslab[1:-1].split('][') if expr]

    out = []
    for expr in exprs:
        tokens = list(map(int, expr.split(':')))
        start = tokens[0]
        step = 1

        if len(tokens) == 1:
            stop = start + 1
        elif len(tokens) == 2:
            stop = tokens[1] + 1
        elif len(tokens) == 3:
            step = tokens[1]
            stop = tokens[2] + 1
        else:
            raise ConstraintExpressionError("Invalid hyperslab %s" % hyperslab)

        out.append(slice(start, stop, step))

    return tuple(out)


class SimpleParser(object):

    """A very simple parser."""

    def __init__(self, input, flags=0):
        self.buffer = input
        self.flags = flags

    def peek(self, regexp):
        """Check if a token is present and return it."""
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m:
            token = m.group()
        else:
            token = ''
        return token

    def consume(self, regexp):
        """Consume a token from the buffer and return it."""
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m:
            token = m.group()
            self.buffer = self.buffer[len(token):]
        else:
            raise Exception("Unable to parse token: %s" % self.buffer[:10])
        return token

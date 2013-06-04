import re
from urllib import quote, unquote


def parse_projection(input):
    """
    Split a projection into items, taking into account server-side functions,
    and parse slices.

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
            token = [ re.match('(.*?)(\[.*\])?$', part).groups() 
                for part in token ]
            token = [ (quote(name), parse_hyperslab(slice_ or '')) 
                for (name, slice_) in token ]
        return token

    return map(parse, tokenize(input))


def parse_ce(query_string):
    """
    Extract the projection and selection from the QUERY_STRING.

        >>> parse_ce('a,b[0:2:9],c&a>1&b<2')
        ([[('a', ())], [('b', (slice(0, 10, 2),))], [('c', ())]], ['a>1', 'b<2'])
        >>> parse_ce('a>1&b<2')
        ([], ['a>1', 'b<2'])

    This function can also handle function calls in the URL, according to the
    DAP specification:

        >>> parse_ce('time&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)')
        ([[('time', ())]], ['bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'])
        >>> parse_ce('time,bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)')
        ([[('time', ())], 'bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'], [])
        >>> parse_ce('mean(g,0)')
        (['mean(g,0)'], [])
        >>> parse_ce('mean(mean(g.a,1),0)')
        (['mean(mean(g.a,1),0)'], [])

    """
    tokens = [ token for token in unquote(query_string).split('&') if token ]
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
    """
    Parse a hyperslab into a Python tuple of slices.

    """
    exprs = [expr for expr in hyperslab[1:-1].split('][') if expr]

    out = []
    for expr in exprs:
        tokens = map(int, expr.split(':'))
        start = tokens[0]
        step = 1

        if len(tokens) == 1:
            stop = start + 1
        elif len(tokens) == 2:
            stop = tokens[1] + 1
        elif len(tokens) == 3:
            step = tokens[1]
            stop = tokens[2] + 1

        out.append(slice(start, stop, step))

    return tuple(out)


class SimpleParser(object):
    """
    A very simple parser.

    """
    def __init__(self, input, flags=0):
        self.buffer = input
        self.flags = flags

    def peek(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
        else:
            token = ''
        return token

    def consume(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
            self.buffer = self.buffer[len(token):]
        else:
            raise Exception("Unable to parse token: %s" % self.buffer[:10])
        return token

    def __nonzero__(self):
        return len(self.buffer)


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

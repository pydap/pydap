import sys
import re
import string
import urllib

import numpy

from pydap.exceptions import ConstraintExpressionError


__author__  = 'Roberto De Almeida <rob@pydap.org>'
__version__ = (3,1,1)       # pydap version
__dap__     = (2,15)       # protocol version


# Global variables -- I know we should try to avoid them, but we need
# a place to put module configuration. These two shouldn't normally
# be altered.
USER_AGENT = 'pydap/%s' % '.'.join(str(d) for d in __version__)
INDENT = ' ' * 4

# A directory where the client should store cache information/data.
CACHE = None

# Socket level timeout (in seconds).
TIMEOUT = None

# A ``ProxyInfo`` instance. To use a proxy @ http://localhost:8000/::
#
# >>> import httplib2, pydap.util.socks, pydap.lib
# >>> pydap.lib.PROXY = httplib2.ProxyInfo(pydap.util.socks.PROXY_TYPE_HTTP, 'localhost', 8000)
PROXY = None


def isiterable(obj):
    """
    Check if an object is iterable (strings don't count).

        >>> isiterable("string")
        False
        >>> isiterable(1)
        False
        >>> isiterable([1])
        True

    """
    if isinstance(obj, basestring): return False

    try:
        iter(obj)
        return True
    except TypeError:
        return False


def quote(name):
    """
    Extended quote for the DAP spec.

    The period MUST be escaped in names (DAP 2.0 spec, item 5.1):

        >>> quote("White space")
        'White%20space'
        >>> urllib.quote("Period.")
        'Period.'
        >>> quote("Period.")
        'Period%2E'

    """
    def escape_(c):
        if c == '.':
            c = '%2E'
        elif c not in string.letters + string.digits + '''_!~*'-"''' + '%':
            c = urllib.quote(c)
        return c
    return ''.join(map(escape_, name))


def escape(s):
    r"""
    Escape a string, which may contain quotes.

        >>> print escape('test')
        "test"
        >>> print escape('this is a "simple" test')
        "this is a \"simple\" test"

    """
    s = s.replace(r'\\', r'\\\\')
    s = s.replace(r'"', r'\"')
    s = '"%s"' % s
    return s


def encode_atom(atom):
    """
    Encode an atom, according to the DAP spec.

        >>> print encode_atom(None)
        NaN
        >>> print encode_atom('string')
        "string"
        >>> print encode_atom(1)
        1
        >>> print encode_atom(1/3.)
        0.333333

    """
    if atom is None:
        return 'NaN'
    elif isinstance(atom, basestring):
        return escape(atom)
    elif isinstance(atom, (int, long)):
        return '%d' % atom
    try:
        return '%.6g' % atom
    except TypeError:
        return escape(str(atom))


def walk(var, type_=object):
    """
    Yield all variables of a given type from a dataset.

    The iterator returns also the parent variable.

    """
    if isinstance(var, type_):
        yield var
    for child in var.walk():
        for subvar in walk(child, type_):
            yield subvar


def hyperslab(slices):
    """
    Build an Opendap representation of a multidimensional slice object.

        >>> print hyperslab( (slice(None),) )
        <BLANKLINE>
        >>> print hyperslab( (slice(0, 10, 2),) )
        [0:2:9]

    Note that in Opendap the stop is included, while in Python it's
    exluded, as we can see on the last example. More examples::

        >>> print hyperslab( (slice(0, 10, 2), slice(1, 20, 2)) )
        [0:2:9][1:2:19]
        >>> print hyperslab( (slice(0, 10, 2), slice(None), slice(1, 20, 2)) )
        [0:2:9][0:1:%d][1:2:19]
        >>> print hyperslab( (slice(0, 10, 2), slice(1, 20, 2), slice(None)) )
        [0:2:9][1:2:19]

    For 1D slices we can omit the tuple::

        >>> print hyperslab(slice(0, 10, 2))
        [0:2:9]

    """ % sys.maxint

    if not isinstance(slices, tuple): slices = [slices]
    else: slices = list(slices)

    # Remove unnecessary slices from the end.
    while slices and slices[-1] == slice(None):
        slices.pop()

    return ''.join('[%d:%d:%d]' % (
            slice_.start or 0,
            slice_.step or 1,
            (slice_.stop or sys.maxint)-1)
            for slice_ in slices)


def fix_slice(slices, shape):
    """
    Fix a slice, handling ``None``s and integers.

        >>> fix_slice(0, (10,))
        (slice(0, 1, 1),)
        >>> fix_slice(-5, (10,))
        (slice(5, 6, 1),)
        >>> fix_slice( (0, slice(None), -1), (4, 4, 4, 4) )
        (slice(0, 1, 1), slice(0, 4, 1), slice(3, 4, 1), slice(0, 4, 1))
        >>> fix_slice( (0, Ellipsis, -1), (4, 4, 4, 4) )
        (slice(0, 1, 1), slice(0, 4, 1), slice(0, 4, 1), slice(3, 4, 1))

    """
    if not isinstance(slices, tuple): slices = (slices,)
    n = len(shape)-len(slices)
    if [s for s in slices if s is Ellipsis]:  # ``Ellipsis in slices`` fails due to numpy comparison problem
        i = list(slices).index(Ellipsis)
        slices = slices[:i] + (slice(None),)*(n+1) + slices[i+1:]
    else:
        slices = slices + (slice(None),)*n

    out = []
    for slice_, length in zip(slices, shape):
        if isinstance(slice_, numpy.ndarray):
            start = slice_.nonzero()[0][0]
            stop = slice_.nonzero()[0][-1] + 1
            slice_ = slice(start, stop, 1)
        elif isinstance(slice_, (int, long)):
            if slice_ < 0: slice_ += length
            slice_ = slice(slice_, slice_+1, 1)
        else:
            if slice_.start is None:
                start = 0
            else:
                start = slice_.start
            if start < 0: start += length
            if slice_.step is None:
                step = 1
            else:
                step = slice_.step
            if slice_.stop is None:
                stop = length
            else:
                stop = slice_.stop
            if stop < 0: stop += length
            slice_ = slice(start, stop, step)
        out.append(slice_)
    return tuple(out)


def combine_slices(slices1, slices2):
    """
    Combine two multidimensional slices together.

    """
    out = []
    for slice1, slice2 in zip(slices1, slices2):
        if slice1.start is None and slice2.start is None:
            start = None
        else:
            start = (slice1.start or 0) + (slice2.start or 0)
        if slice1.step is None and slice2.step is None:
            step = None
        else:
            step = (slice1.step or 1) * (slice2.step or 1)
        if slice1.stop is None and slice2.stop is None:
            stop = None
        else:
            stop1 = slice1.stop or sys.maxint
            stop2 = slice2.stop or sys.maxint
            stop = min(stop1, (slice1.start or 0) + stop2)
        out.append(slice(start, stop, step))
    return tuple(out)


def get_slice(hyperslab):
    """
    Parse a hyperslab into a Python tuple of slices.

    """
    output = []
    dimslices = [ds for ds in hyperslab[1:-1].split('][') if ds]
    for dimslice in dimslices:
        tokens = dimslice.split(':')
        start = int(tokens[0])
        step = 1
        stop = start
        if len(tokens) == 2:
            stop = int(tokens[1])
        elif len(tokens) == 3:
            step = int(tokens[1])
            stop = int(tokens[2])
        output.append(slice(start, stop+1, step))
    return tuple(output)


def parse_qs(query):
    """
    Parse the constraint expression.

    """
    projection = []
    selection = [token for token in urllib.unquote(query).split('&') if token]
    if selection and not re.search('<=|>=|!=|=~|>|<|=', selection[0]): 
        projection = [p for p in selection.pop(0).split(',') if p]

    fields = []
    for var in projection:
        tokens = var.split('.')
        tokens = [re.match('(.*?)(\[.*\])?$', token).groups() for token in tokens]
        tokens = [(urllib.quote(token), get_slice(slice_ or '')) for (token, slice_) in tokens]
        fields.append(tokens)

    return fields, selection


def fix_shn(projection, dataset):
    """
    Fix shorthand notation for variables.
    
    Shorthand notation is the syntax some clients use to retrieve data
    using the variable name instead of its fully qualified id.

    Here ``projection`` is a list as returned by ``parse_qs``.

    """
    out = []
    for var in projection:
        if len(var) == 1 and var[0][0] not in dataset:
            token, slice_ = var.pop(0)
            for child in walk(dataset):
                if token == child.name:
                    if var: raise ConstraintExpressionError(
                            "Ambiguous shorthand notation request: %s" % token)
                    var = [(parent, ()) 
                            for parent in child.id.split('.')[:-1]] + [(token, slice_)]
        out.append(var)
    return out


def escape_dods(dods, pad=''):
    """
    Escape a DODS response.

    This is useful for debugging. You're probably spending too much time
    with pydap if you need to use this.

    """
    dds, dods = dods.split('\nData:\n', 1)

    out = []
    for i, char in enumerate(dods):
        char = hex(ord(char))
        char = char.replace('0x', '\\x')
        if len(char) < 4: char = char.replace('\\x', '\\x0')
        out.append(char)
        if pad and (i%4 == 3): out.append(pad)
    out = ''.join(out)
    out = out.replace(r'\x5a\x00\x00\x00', '<start of sequence>')
    out = out.replace(r'\xa5\x00\x00\x00', '<end of sequence>')
    return dds + '\nData:\n' + out

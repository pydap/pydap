import sys
import urllib
import itertools
import operator

import pkg_resources

from pydap.exceptions import ConstraintExpressionError


__dap__ = '2.15'
__version__ = pkg_resources.get_distribution("Pydap").version


START_OF_SEQUENCE = '\x5a\x00\x00\x00'
END_OF_SEQUENCE = '\xa5\x00\x00\x00'


def quote(name):
    """
    According to the DAP specification a variable name MUST contain only upper
    or lower case letters, numbers, or characters from the set 

        _ ! ~ * ' - "

    All other characters must be escaped. This includes the period, which is
    normally not quoted by `urllib.quote`.

        >>> quote("White space")
        'White%20space'
        >>> urllib.quote("Period.")
        'Period.'
        >>> quote("Period.")
        'Period%2E'

    """
    safe = '%_!~*\'-"'
    return urllib.quote(name.encode('utf-8'), safe=safe).replace('.', '%2E')


def encode(obj):
    """
    Encode an object to its DAP representation.

    """
    try:
        return '%.6g' % obj
    except:
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        return '"%s"' % obj.replace('"', r'\"')


def fix_slice(slice_, shape):
    """
    Normalize a slice so that it has the same length of `shape`, and no negative
    indexes, if possible.

    This is based on this document: http://docs.scipy.org/doc/numpy/reference/arrays.indexing.html

        >>> import numpy as np
        >>> x = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        >>> slice_ = slice(-2, 10)
        >>> print x[slice_]
        [8 9]
        >>> print fix_slice(slice_, x.shape)
        (slice(8, 10, 1),)
        >>> assert (x[fix_slice(slice_, x.shape)] == x[slice_]).all()

        >>> slice_ = slice(-3, 3, -1)
        >>> print x[slice_]
        [7 6 5 4]
        >>> print fix_slice(slice_, x.shape)
        (slice(7, 3, -1),)
        >>> assert (x[fix_slice(slice_, x.shape)] == x[slice_]).all()

        >>> slice_ = slice(5, None)
        >>> print x[slice_]
        [5 6 7 8 9]
        >>> print fix_slice(slice_, x.shape)
        (slice(5, 10, 1),)
        >>> assert (x[fix_slice(slice_, x.shape)] == x[slice_]).all()

        >>> x = np.array([[[1],[2],[3]], [[4],[5],[6]]])
        >>> print x.shape
        (2, 3, 1)
        >>> slice_ = slice(1, 2)
        >>> print x[slice_]
        [[[4]
          [5]
          [6]]]
        >>> print fix_slice(slice_, x.shape)
        (slice(1, 2, 1), slice(0, 3, 1), slice(0, 1, 1))
        >>> assert (x[fix_slice(slice_, x.shape)] == x[slice_]).all()

        >>> slice_ = (Ellipsis, 0)
        >>> print x[slice_]
        [[1 2 3]
         [4 5 6]]
        >>> print fix_slice(slice_, x.shape)
        (slice(0, 2, 1), slice(0, 3, 1), 0)
        >>> assert (x[fix_slice(slice_, x.shape)] == x[slice_]).all()

    """
    # convert `slice_` to a tuple
    if not isinstance(slice_, tuple):
        slice_ = (slice_,)

    # expand Ellipsis and make `slice_` at least as long as `shape`
    expand = len(shape) - len(slice_)
    out = []
    for s in slice_:
        if s is Ellipsis:
            out.extend( (slice(None),) * (expand+1) )
            expand = 0
        elif isinstance(s, int):
            out.append(slice(s, s+1, 1))
        else:
            out.append(s)
    slice_ = tuple(out) + (slice(None),) * expand

    out = []
    for s, n in zip(slice_, shape):
        if isinstance(s, int):
            if s < 0:
                try:
                    s += n
                except TypeError:
                    raise Exception('Negative indexes can not be applied when size is unknown!')
            out.append(s)
        else:
            k = s.step or 1

            i = s.start
            if i is None:
                if k > 0:
                    i = 0
                else:
                    i = n
            elif i < 0:
                try:
                    i += n
                except TypeError:
                    raise Exception('Negative indexes can not be applied when size is unknown!')

            j = s.stop
            if j is None:
                if k > 0:
                    j = n
                else:
                    j = -1
            elif j < 0:
                try:
                    j += n
                except TypeError:
                    raise Exception('Negative indexes can not be applied when size is unknown!')

            out.append(slice(i, j, k))

    return tuple(out)


def combine_slices(slice1, slice2):
    """
    Combine two tuples of slices sequentially.

    These two should be equal:

        x[ combine_slices(s1, s2) ] == x[s1][s2]

    """
    out = []
    for exp1, exp2 in itertools.izip_longest(slice1, slice2, fillvalue=slice(None)):
        if isinstance(exp1, int):
            exp1 = slice(exp1, exp1+1)
        if isinstance(exp2, int):
            exp2 = slice(exp2, exp2+1)

        start = (exp1.start or 0) + (exp2.start or 0)
        step = (exp1.step or 1) * (exp2.step or 1)

        if exp1.stop is None and exp2.stop is None:
            stop = None
        elif exp1.stop is not None:
            stop = exp1.stop
        elif exp2.stop is not None:
            stop = (exp1.start or 0) + exp2.stop
        else:
            stop = min(exp1.stop, (exp1.start or 0) + exp2.stop)

        out.append(slice(start, stop, step))
    return tuple(out)


def hyperslab(slice_):
    """
    Build an Opendap representation of a multidimensional slice.

    """
    if not isinstance(slice_, tuple):
        slice_ = [slice_]
    else:
        slice_ = list(slice_)

    while slice_ and slice_[-1] == slice(None):
        slice_.pop(0)

    return ''.join('[%s:%s:%s]' % (
        s.start or 0, s.step or 1, (s.stop or sys.maxint)-1) for s in slice_)


def walk(var, type=object):
    """
    Yield all variables of a given type from a dataset.

    The iterator returns also the parent variable.

    """
    if isinstance(var, type):
        yield var
    for child in var.children():
        for var in walk(child, type):
            yield var


def fix_shorthand(projection, dataset):
    """
    Fix shorthand notation in the projection.

    Some clients request variables by their name, not by the id. This is called
    the "shorthand notation", and it has to be fixed.

    """
    out = []
    for var in projection:
        if len(var) == 1 and var[0][0] not in dataset.keys():
            token, slice_ = var.pop(0)
            for child in walk(dataset):
                if token == child.name:
                    if var: raise ConstraintExpressionError(
                            'Ambiguous shorthand notation request: %s' % token)
                    var = [(parent, ()) for parent in
                            child.id.split('.')[:-1]] + [(token, slice_)]
        out.append(var)
    return out


def get_var(dataset, id_):
    """
    Given an id, return the corresponding variable from the dataset.

    """
    tokens = id_.split('.')
    return reduce(operator.getitem, [dataset] + tokens)


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

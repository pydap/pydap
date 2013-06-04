import sys
import re
from urlparse import urlsplit, urlunsplit
import copy
import warnings 

from pydap.model import *
from pydap.model import SequenceData
from pydap.lib import hyperslab, combine_slices, fix_slice, walk, isiterable, encode_atom
from pydap.util.http import request
from pydap.parsers.dds import DDSParser
from pydap.xdr import DapUnpacker


__all__ = ['VariableProxy', 'ArrayProxy', 'SequenceProxy']


class VariableProxy(object):
    """
    A proxy object pointing to an Opendap variable.

    The Opendap client works by defining proxy objects that point to
    specific variables in specific datasets. The object implements a
    typical interface (like an ndarray from Numpy) on the user-side,
    and downloads data on-the-fly from the server as necessary.

    This particular class is just an abstract implementation.

    """
    def __init__(self, id, url, slice_=None):
        self.id = id
        self.url = url
        self._slice = slice_ or (slice(None),)

    def __repr__(self):
        return '<%s pointing to variable "%s%s" at "%s">' % (
                self.__class__.__name__, self.id, hyperslab(self._slice), self.url)

    def __deepcopy__(self, memo=None, _nil=[]):
        out = self.__class__(self.id, self.url, self._slice)
        return out


class ConstraintExpression(object):
    """
    An object representing a given constraint expression.

    These objects are used to build the constraint expression used when
    downloading data. They are produced when a SequenceProxy is compared
    to something::

        >>> from pydap.model import *
        >>> s = SequenceType(name='s')
        >>> s['x'] = BaseType(name='x')
        >>> s.data = SequenceProxy('s', 'http://example.com/dataset')
        >>> s.x.data = SequenceProxy('s.x', 'http://example.com/dataset')
        >>> print type(s.x > 10)
        <class 'pydap.proxy.ConstraintExpression'>
        
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __and__(self, other):
        """Join two CEs together."""
        return self.__class__('%s&%s' % (self.value, other))

    def __or__(self, other):
        raise Exception('OR constraints not allowed in the Opendap specification.')


class ArrayProxy(VariableProxy):
    """
    Proxy to an Opendap basetype.

    """
    def __init__(self, id, url, shape, slice_=None):
        self.id = id
        self.url = url
        self._shape = shape

        if slice_ is None:
            self._slice = (slice(None),) * len(shape)
        else:
            self._slice = slice_ + (slice(None),)*(len(shape)-len(slice_))

    @property
    def shape(self):
        return self._shape

    @property
    def __array_interface__(self):
        data = self[:]
        return {
                'version': 3,
                'shape': data.shape,
                'typestr': data.dtype.str,
                'data': data,
                }

    def __iter__(self):
        return iter(self[:])

    def __getitem__(self, index):
        slice_ = combine_slices(self._slice, fix_slice(index, self.shape))
        scheme, netloc, path, query, fragment = urlsplit(self.url)
        url = urlunsplit((
                scheme, netloc, path + '.dods',
                self.id + hyperslab(slice_) + '&' + query,
                fragment))

        resp, data = request(url)
        dds, xdrdata = data.split('\nData:\n', 1)
        dataset = DDSParser(dds).parse()
        data = data2 = DapUnpacker(xdrdata, dataset).getvalue()

        # Retrieve the data from any parent structure(s).
        for var in walk(dataset):
            if type(var) in (StructureType, DatasetType):
                data = data[0]
            elif var.id == self.id: 
                return data

        # Some old servers return the wrong response. :-/
        # I found a server that would return an array to a request
        # for an array inside a grid (instead of a structure with
        # the array); this will take care of it.
        for var in walk(dataset):
            if type(var) in (StructureType, DatasetType):
                data2 = data2[0]
            elif self.id.endswith(var.id):
                return data2
            
    # Comparisons return a boolean array
    def __eq__(self, other): return self[:] == other 
    def __ne__(self, other): return self[:] != other
    def __ge__(self, other): return self[:] >= other
    def __le__(self, other): return self[:] <= other
    def __gt__(self, other): return self[:] > other
    def __lt__(self, other): return self[:] < other


class SequenceProxy(VariableProxy, SequenceData):
    """
    Proxy to an Opendap Sequence.

    This class simulates the behavior of a Numpy record array, proxying
    the data in an Opendap Sequence object (or a child variable inside
    a Sequence)::

        >>> from pydap.model import *
        >>> s = SequenceType(name='s')
        >>> s['id'] = BaseType(name='id')
        >>> s['x'] = BaseType(name='x')
        >>> s['y'] = BaseType(name='y')
        >>> s.data = SequenceProxy('s', 'http://example.com/dataset')
        >>> print s.data
        <SequenceProxy pointing to variable "s" at "http://example.com/dataset">
        >>> print s.x.data
        <SequenceProxy pointing to variable "s.x" at "http://example.com/dataset">

    We can use the same methods we would use if the data were local::

        >>> print s[0].x.data
        <SequenceProxy pointing to variable "s[0:1:0].x" at "http://example.com/dataset">
        >>> print s[10:20][2].y.data
        <SequenceProxy pointing to variable "s[12:1:12].y" at "http://example.com/dataset">
        >>> print s[ (s['id'] > 1) & (s.x > 10) ].data
        <SequenceProxy pointing to variable "s" at "http://example.com/dataset?s.id>1&s.x>10&">
        >>> print s[ ('y', 'x') ].data
        <SequenceProxy pointing to variable "s.y,s.x" at "http://example.com/dataset">
        >>> s2 = s[ ('y', 'x') ]
        >>> print s2[ s2.x > 10 ].x.data
        <SequenceProxy pointing to variable "s.x" at "http://example.com/dataset?s.x>10&">
        >>> print s[ ('y', 'x') ][0].data
        <SequenceProxy pointing to variable "s.y,s.x[0:1:0]" at "http://example.com/dataset">

    (While the last line may look strange, it's equivalent to
    ``s.y[0:1:0],s.x[0:1:0]`` -- at least on Hyrax).

    """
    def __init__(self, id, url, slice_=None, children=None):
        VariableProxy.__init__(self, id, url, slice_)
        self.children = children or ()

    def __repr__(self):
        id_ = ','.join('%s.%s' % (self.id, child) for child in self.children) or self.id
        return '<%s pointing to variable "%s%s" at "%s">' % (
                self.__class__.__name__, id_, hyperslab(self._slice), self.url)

    def __iter__(self):
        scheme, netloc, path, query, fragment = urlsplit(self.url)
        id_ = ','.join('%s.%s' % (self.id, child) for child in self.children) or self.id
        url = urlunsplit((
                scheme, netloc, path + '.dods',
                id_ + hyperslab(self._slice) + '&' + query,
                fragment))

        resp, data = request(url)
        dds, xdrdata = data.split('\nData:\n', 1)
        dataset = DDSParser(dds).parse()
        dataset.data = DapUnpacker(xdrdata, dataset).getvalue()
        dataset._set_id()

        # Strip any projections from the request id.
        id_ = re.sub('\[.*?\]', '', self.id)
        # And return the proper data.
        for var in walk(dataset):
            if var.id == id_:
                data = var.data
                if isinstance(var, SequenceType):
                    order = [var.keys().index(k) for k in self.children]
                    data = reorder(order, data, var._nesting_level)
                return iter(data)

    def __len__(self):
        return len(list(self.__iter__()))

    def __getitem__(self, key):
        out = copy.deepcopy(self)
        if isinstance(key, ConstraintExpression):
            scheme, netloc, path, query, fragment = urlsplit(self.url)
            out.url = urlunsplit((
                    scheme, netloc, path, str(key & query), fragment))

            if out._slice != (slice(None),):
                warnings.warn('Selection %s will be applied before projection "%s".' % (
                        key, hyperslab(out._slice)))
        elif isinstance(key, basestring):
            out._slice = (slice(None),)
            out.children = ()
            parent = self.id
            if ',' in parent:
                parent = parent.split(',', 1)[0].rsplit('.', 1)[0]
            out.id = '%s%s.%s' % (parent, hyperslab(self._slice), key)
        elif isinstance(key, tuple):
            out.children = key[:]
        else:
            out._slice = combine_slices(self._slice, fix_slice(key, (sys.maxint,)))
        return out

    def __deepcopy__(self, memo=None, _nil=[]):
        out = self.__class__(self.id, self.url, self._slice, self.children[:])
        return out

    # Comparisons return a ``ConstraintExpression`` object
    def __eq__(self, other): return ConstraintExpression('%s=%s' % (self.id, encode_atom(other)))
    def __ne__(self, other): return ConstraintExpression('%s!=%s' % (self.id, encode_atom(other)))
    def __ge__(self, other): return ConstraintExpression('%s>=%s' % (self.id, encode_atom(other)))
    def __le__(self, other): return ConstraintExpression('%s<=%s' % (self.id, encode_atom(other)))
    def __gt__(self, other): return ConstraintExpression('%s>%s' % (self.id, encode_atom(other)))
    def __lt__(self, other): return ConstraintExpression('%s<%s' % (self.id, encode_atom(other)))


def reorder(order, data, level):
    """
    Reorder Sequence data according to the request.

    """
    if not (order and isiterable(data)):
        return data
    if level == 0:
        return tuple(data[i] for i in order)
    else:
        return [reorder(order, value, level-1) for value in data]


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

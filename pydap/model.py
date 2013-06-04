from operator import attrgetter, itemgetter
import copy
import itertools
from new import classobj

import numpy

from pydap.lib import quote, walk, fix_slice
from pydap.util.odict import odict


__all__ = ['StructureType', 'SequenceType', 'DatasetType', 'GridType',
           'BaseType', 'Float32', 'Float64', 'Int16', 'Int32', 'UInt16',
           'UInt32', 'Byte', 'String', 'Url', 'typemap']


# Define the basic Opendap types as classes. Each class has a correspondent
# Numpy typecode and item size. Instead of explicitly defining classes we
# can use the ``classobj`` function, since the classes are basically just
# placeholders for attributes.
def TypeFactory(name, typecode, size):
    return classobj(name, (object,),
            {'typecode': typecode, 'size': size, 'descriptor': name})

Float64 = TypeFactory('Float64', 'f', 8)
Float32 = TypeFactory('Float32', 'f', 4)
Int32 = TypeFactory('Int32', 'i', 4)
Int16 = TypeFactory('Int16', 'i', 4)
UInt32 = TypeFactory('UInt32', 'I', 4)
UInt16 = TypeFactory('UInt16', 'I', 4)
Byte = TypeFactory('Byte', 'B', 1)
String = TypeFactory('String', 'S', None)
Url = TypeFactory('Url', 'S', None)
basetypes = [Float64, Float32, Int32, Int16, Byte, UInt32, UInt16, String, Url]

# A simple map to convert between commonly used identifiers
# and our classes.
typemap = {
    # type.__name__.lower()
    'float64': Float64,
    'float32': Float32,
    'int32': Int32,
    'int16': Int16,
    'uint32': UInt32,
    'uint16': UInt16,
    'byte': Byte,
    'string': String,
    'url': Url,

    # numpy
    'd': Float64,
    'f': Float32,
    'h': Int16,
    'i': Int32, 'l': Int32, 'q': Int32,
    'b': Byte,
    'H': UInt16,
    'I': UInt32, 'L': UInt32, 'Q': UInt32,
    'B': Byte,
    'S': String,

    # extra from the stdlib array module
    'c': String,
    'u': String,

    # Scientific.IO.NetCDF uses this
    's': String,
}


class DapType(object):
    """
    The common Opendap type.

    This class is an abstract class, defining common methods and
    attributes for other all classes in the Opendap data model.

    """
    def __init__(self, name='nameless', attributes=None, nesting_level=0):
        self.name = name
        self._id = self.name
        self.attributes = attributes or {}
        self._nesting_level = nesting_level

    # DAP variables' names cannot have special characters like
    # [, ] or %. Here we automatically escape them when the name
    # is set.
    def _get_name(self):
        return self._name
    def _set_name(self, name):
        self._name = quote(name)
    name = property(_get_name, _set_name)

    def __getattr__(self, attr):
        """
        Attribute shortcut.

        The data classes have their attributes stored in the 
        ``attributes`` attribute, which is a dictionary. Access
        to these values can be shortcutted by accessing the 
        attribute directly::

            >>> var = DapType()
            >>> var.attributes['foo'] = 'bar'
            >>> print var.foo
            bar

        """
        try:
            return self.attributes[attr]
        except (KeyError, TypeError):
            raise AttributeError(
                    "'%s' object has no attribute '%s'"
                    % (self.__class__, attr))
    
    def walk(self):
        """
        Iterate over children.

        This method is used in constructor variables to iterate
        over the variable's children. The default behavior is to
        return and empty iterable (ie, no children).

        """
        return ()

    def _set_id(self, parent=None):
        """
        Set the variable id.

        The id of a variable is a representation of its hierarchy
        in the dataset, using dots to join the variable names.

        """
        if parent:
            self._id = '%s.%s' % (parent, self.name)
        else:
            self._id = self.name

        # Propagate id to children.
        for var in self.walk():
            var._set_id(self._id)
    id = property(attrgetter('_id'))  # read-only


class BaseType(DapType):
    """
    The base Opendap type.

    This class represents basic Opendap types, which contain data.
    Variables can be scalars or multi-dimensional arrays, of one of
    the basic Opendap types (Int32, String, etc.)::

        >>> a = BaseType(name='a', data=1, type=Int32)
        >>> b = BaseType(name='b', data=range(5), shape=(5,),
        ...         dimensions=('time',), type=UInt16)
        >>> print b.attributes
        {}
        >>> b.attributes['units'] = 'days since 1980-1-1'

    Comparisons and other operators are usually applied to the ``data``
    attribute::

        >>> print b[1]
        1
        >>> print len(b)
        5
        >>> print a > 0
        True
        >>> data = numpy.arange(4)
        >>> data.shape = (2, 2)
        >>> c = BaseType(name='c', data=data)
        >>> for block in c:
        ...     print block
        [0 1]
        [2 3]

    """
    def __init__(self, name='nameless', data=None, shape=None,
            dimensions=None, type=Int32, attributes=None):
        DapType.__init__(self, name, attributes)
        self.type = type in basetypes and type or typemap[type]
        self.data = data
        self.shape = shape or ()
        self.dimensions = dimensions or ()

    def __str__(self):
        return """%s
    with data
%s""" % (self.__class__, self.data)

    def __getitem__(self, index):
        return self.data[index]

    @property
    def __array_interface__(self):
        data = numpy.asarray(self.data)
        return {
                'version': 3,
                'shape': data.shape,
                'typestr': data.dtype.str,
                'data': data,
                }

    # Comparisons and other operations are applied directly to
    # the ``data`` attribute.
    def __eq__(self, other): return self.data == other
    def __ne__(self, other): return self.data != other
    def __ge__(self, other): return self.data >= other
    def __le__(self, other): return self.data <= other
    def __gt__(self, other): return self.data > other
    def __lt__(self, other): return self.data < other
    def __iter__(self): return iter(self.data)
    def __len__(self): return len(self.data)

    def __copy__(self):
        out = self.__class__(self.name, self.data, self.shape,
                self.dimensions, self.type, self.attributes)
        out._id = self._id
        return out

    def __deepcopy__(self, memo=None, _nil=[]):
        """
        Return a copy of the object, with a copy of the data too.

        """
        out = self.__class__(self.name, copy.copy(self.data),
                self.shape[:], self.dimensions[:], self.type,
                self.attributes.copy())
        out._id = self._id
        return out


class StructureType(odict, DapType):
    """
    An Opendap Structure.

    A StructureType is simply a fancy dictionary, used to hold groups of
    variables that share common characteristics (in theory).  They work
    exactly like Python dictionaries::

        >>> s = StructureType(name='s')
        >>> s['a'] = BaseType(name='a')
        >>> s['b'] = BaseType(name='b')
        >>> print s.keys()
        ['a', 'b']
        >>> print [var.name for var in s]
        ['a', 'b']

    """
    def __init__(self, name='nameless', attributes=None):
        odict.__init__(self)
        DapType.__init__(self, name, attributes)

    def __getattr__(self, attr):
        """
        Allow lazy access to children.

        We override ``__getattr__`` to allow children variables
        to be accessed using a lazy syntax::

            >>> s = StructureType(name='s')
            >>> s['a'] = BaseType(name='a')
            >>> print s.a.id
            s.a

        """
        if attr in self:
            return self[attr]
        else:
            return DapType.__getattr__(self, attr)

    # Walk returns each stored variable.
    walk = __iter__ = odict.itervalues

    def __setitem__(self, key, item):
        if key != item.name:
            raise KeyError('Key "%s" is different from variable name "%s"!' %
                    (key, item.name))
        odict.__setitem__(self, key, item)

        # Fix id in item.
        item._set_id(self._id)

    # Propagate to and collect data from children.
    def _get_data(self):
        data = [ var.data for var in self.walk() ]
        return tuple(
                combine_rows(data, self._nesting_level))
    def _set_data(self, data):
        data = [get_row(data, i, self._nesting_level) for
                i, k in enumerate(self.keys())]
        for col, var in itertools.izip(data, self):
            var.data = col
    data = property(_get_data, _set_data)

    def __copy__(self):
        out = self.__class__(self.name, self.attributes)
        out._id = self._id

        # Stored variables are not copied.
        out.update(self)
        return out

    def __deepcopy__(self, memo=None, _nil=[]):
        out = self.__class__(self.name, self.attributes.copy())
        out._id = self._id

        # Make copies of the stored variables.
        for k, v in self.items():
            out[k] = copy.deepcopy(v, memo)
        return out


class DatasetType(StructureType):
    """
    An Opendap Dataset.

    A DatasetType works pretty much like a Structure; the major
    difference is that its name is not used when composing the id of
    stored variables::

        >>> dataset = DatasetType(name='dataset')
        >>> dataset['a'] = BaseType(name='a', attributes={'foo': 'bar'})
        >>> print dataset.a.foo
        bar

    """
    def __setitem__(self, key, item):
        if key != item.name:
            raise KeyError('Key "%s" is different from variable name "%s"!' %
                    (key, item.name))
        odict.__setitem__(self, key, item)

        # Do not propagate id.
        item._set_id(None)

    def _set_id(self, parent=None):
        self._id = self.name

        for var in self.walk():
            var._set_id(None)


class SequenceType(StructureType):
    """
    An Opendap Sequence.

    Sequences are a special kind of constructor, holding records for
    the stored variables. They are somewhat similar to record arrays
    in Numpy::

        >>> s = SequenceType(name='s')
        >>> s['id'] = BaseType(name='id', type=Int32)
        >>> s['x'] = BaseType(name='x', type=Float64)
        >>> s['y'] = BaseType(name='y', type=Float64)
        >>> s['foo'] = BaseType(name='foo', type=Int32)

        >>> s.data = [(1, 10, 100, 42), (2, 20, 200, 43), (3, 30, 300, 44)]
        >>> for struct_ in s: print struct_.data
        (1, 10, 100, 42)
        (2, 20, 200, 43)
        (3, 30, 300, 44)
        >>> del s['foo']
        >>> print s.data
        [[1 10 100]
         [2 20 200]
         [3 30 300]]
        >>> print s['id'].data
        [1 2 3]

    Note that we had to use ``s['id']`` to refer to the variable ``id``,
    since ``s.id`` already points to the id of the Sequence.
    
    (An important point is that the ``data`` attribute must be copiable,
    so don't use consumable iterables like older versions of Pydap
    allowed.)

    Sequences are quite versatile; they can be indexed::

        >>> print s[0].data
        [[1 10 100]]
        >>> print s[0].x.data
        [10]

    Or filtered::

        >>> print s[ (s['id'] > 1) & (s.x > 10) ].data
        [[2 20 200]
         [3 30 300]]

    Or even both::

        >>> print s[ s['id'] > 1 ][1].x.data
        [30]

    If you mix indexing and filtering, be sure to use the right Sequence
    on the filter::

        >>> print s[ s['id'] > 1 ][1].x.data
        [30]
        >>> print s[1][ s['id'] > 1 ].x.data
        Traceback (most recent call last):
            ...
        IndexError: index (1) out of range (0<=index<0) in dimension 0
        >>> print s[1][ s[1]['id'] > 1 ].x.data
        [20]

    (Note that there's a difference between filtering first and then
    slicing, and slicing first and then indexing. This might not be the
    case always, since an Opendap server will always apply the filter
    first, while in this case we're working locally with the data. Don't
    worry, though: when this happens while accessing an Opendap server
    a warning will be issued by the client.)
    
    When filtering a Sequence, don't use the Python extended comparison
    syntax of ``1 < a < 2``, otherwise bad things will happen.

    And of course, slices are also used to access children::

        >>> print s['x'] is s.x
        True

    """
    def __init__(self, name='nameless', attributes=None, data=None):
        StructureType.__init__(self, name, attributes)
        self._nesting_level = 1
        self._data = None
        self.data = data

    def __setitem__(self, key, item):
        StructureType.__setitem__(self, key, item)

        # Increment ``_nesting_level`` in nested sequences.
        def increase_level(var):
            for child in var.walk():
                child._nesting_level = var._nesting_level
                if isinstance(child, SequenceType):
                    child._nesting_level += 1
                increase_level(child)
        increase_level(self)

        if self._data is not None:
            self.data = self.data[ tuple([var.name for var in self.walk()]) ]

    def __delitem__(self, key):
        StructureType.__delitem__(self, key)

        if self._data is not None:
            self.data = self.data[ tuple([var.name for var in self.walk()]) ]

    # When we set the Sequence data we also set the data for its children.
    def _set_data(self, data):
        if isinstance(data, SequenceData):
            self._data = data
            for var in walk(self, (BaseType, SequenceType)):
                if var is not self:
                    id_ = var.id[len(self.id)+1:]
                    var.data = data[id_]
        else:
            self._data = None
            for i, var in enumerate(self.walk()):
                var.data = numpy.asarray(
                        get_row(data, i, self._nesting_level), 'O')
    def _get_data(self):
        if self._data is not None:
            return self._data
        else:
            # Combine the data using the children's data.
            data = [ var.data for var in self.walk() ]
            return numpy.asarray(
                    combine_rows(data, self._nesting_level), 'O')
    data = property(_get_data, _set_data)

    def __getitem__(self, key):
        """
        Fancy Sequence slicing.

        The basic rule for Sequence slices is that it always return a new
        variable -- either a child or a new Sequence. To select a child,
        just use the common dictionary syntax::

            >>> s = SequenceType(name='s')
            >>> s['a'] = BaseType(name='a')
            >>> print s['a'].id
            s.a

        A Sequence can also be filtered or indexed using the slice::

            >>> s['b'] = BaseType(name='b')
            >>> s['c'] = BaseType(name='c')
            >>> s.data = [(1, 10, 100), (2, 20, 200), (3, 30, 300)]
            >>> print s[0].data
            [[1 10 100]]
            >>> print s[2:10].data
            [[3 30 300]]
            >>> print s[ s.a > 10 ].data
            []

        These will return new Sequence objects with the appropriate data.

        """
        if isinstance(key, basestring) and key in self:
            return odict.__getitem__(self, key)
        else:
            out = copy.deepcopy(self)
            if isinstance(key, tuple):
                # return a new sequence with selected children
                out._keys = list(key)
                if out._data is not None:
                    out.data = out.data[key]  # SequenceData protocol
            else:
                if isinstance(key, (int, long)): key = slice(key, key+1, 1)
                out.data = out.data[key]
            return out

    def __iter__(self):
        """
        Return a Structure for each record in the Sequence.

        When a Sequence is iterated it returns Structure objects
        containing each record.

        """
        data = copy.deepcopy(self.data)
        for row in data:
            row = [get_row(row, i, self._nesting_level-1) for i, k in enumerate(self.keys())]
            struct_ = StructureType(self.name, self.attributes.copy())
            for col, name in zip(row, self.keys()):
                var = struct_[name] = copy.deepcopy(self[name])
                if isinstance(var, SequenceType):
                    var._nesting_level -= 1
                var.data = col
            yield struct_

    def __deepcopy__(self, memo=None, _nil=[]):
        out = StructureType.__deepcopy__(self, memo, _nil)
        out._nesting_level = self._nesting_level
        out._data = copy.copy(self._data)
        return out


class SequenceData(object):
    """
    An extended Numpy record array.

    The so-called ``SequenceData`` protocol extends the behavior of record
    arrays from Numpy so that tuples passed to ``_getitem__`` return a new
    object with only those children.

    """
    def __init__(self, data, keys):
        self.data = data
        self.keys = keys

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            col = self.keys.index(key)
            return SequenceData(self.data[:,col], ())
        elif isinstance(key, tuple):
            return SequenceData(
                numpy.dstack([self.data[:, self.keys.index(k)] for k in key]),
                key)
        else:
            return SequenceData(self.data[key], self.keys)

    # comparison are passed to the data object
    def __eq__(self, other): return self.data == other
    def __ne__(self, other): return self.data != other
    def __ge__(self, other): return self.data >= other
    def __le__(self, other): return self.data <= other
    def __gt__(self, other): return self.data > other
    def __lt__(self, other): return self.data < other


def get_row(data, col, level):
    if level == 0:
        return data[col]
    else:
        return [ get_row(value, col, level-1) for value in data ]


def combine_rows(data, level):
    if level == 0:
        return data
    else:
        return [ combine_rows(value, level-1) for value in zip(*data) ]


class GridType(StructureType):
    """
    An Opendap Grid.

    A Grid works both like an array and a Structure. The Grid is basically
    a Structure containing an array and more variables describing its
    axes; the first defined variable is the multi-dimensional array,
    while later each individual axis should be defined::

        >>> g = GridType(name='g')
        >>> data = numpy.arange(6.)
        >>> data.shape = (2, 3)
        >>> g['a'] = BaseType(name='a', data=data, shape=data.shape, type=Float32, dimensions=('x', 'y'))
        >>> g['x'] = BaseType(name='x', data=numpy.arange(2.), shape=(2,), type=Float64)
        >>> g['y'] = BaseType(name='y', data=numpy.arange(3.), shape=(3,), type=Float64)
        >>> print g.array.data
        [[ 0.  1.  2.]
         [ 3.  4.  5.]]
    
    We can treat the Grid like an array and slice it. This will return a new
    grid object with the proper data and axes::

        >>> print g[:,0]
        <class 'pydap.model.GridType'>
            with data
        [[ 0.]
         [ 3.]]
            and axes
        [ 0.  1.]
        [ 0.]

    We can also use a shortcut notation for maps and the array::

        >>> print g['y'][0]
        0.0
        >>> print g.y[:]
        [ 0.  1.  2.]

    A nice thing about Grids is that we can slice them by the maps::

        >>> print g[ :,(g.y > 0) ]
        <class 'pydap.model.GridType'>
            with data
        [[ 1.  2.]
         [ 4.  5.]]
            and axes
        [ 0.  1.]
        [ 1.  2.]

    Though for remote Grids (ie, on Opendap servers) this only works
    for continuous conditions, ie, with a start and an end index.

    """
    def __str__(self):
        return """%s
    with data
%s
    and axes
%s""" % (self.__class__, self.data[0], '\n'.join(map(str, self.data[1:])))

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return StructureType.__getitem__(self, key)
        else:
            key = fix_slice(key, self.shape)
            out = copy.deepcopy(self)
            for var, slice_ in zip(out.walk(), [key] + list(key)):
                var.data = var.data[slice_]
                var.shape = var.data.shape
            return out

    @property
    def __array_interface__(self):
        data = numpy.asarray(self.array.data)
        return {
                'version': 3,
                'shape': data.shape,
                'typestr': data.dtype.str,
                'data': data,
                }

    @property
    def array(self):
        return self[self._keys[0]]

    @property
    def maps(self):
        return odict((k, self[k]) for k in self._keys[1:])

    @property
    def dimensions(self):
        return tuple(self._keys[1:])

    # These attributes all come from the array object.
    def __len__(self): return len(self.array)
    @property
    def type(self): return self.array.type
    def _get_shape(self): return self.array.shape
    def _set_shape(self, shape): self.array.shape = shape
    shape = property(_get_shape, _set_shape)
    


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

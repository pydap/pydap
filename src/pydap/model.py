"""This is the Pydap data model, an implementation of the Data Access Protocol
data model written in Python.

The model is composed of a base object which represents data, the `BaseType`,
and by objects which can hold other objects, all derived from `StructureType`.
Here's a simple example of a `BaseType` variable::

    >>> import numpy as np
    >>> foo = BaseType('foo', np.arange(4, dtype='i'))
    >>> bar = BaseType('bar', np.arange(4, dtype='i'))
    >>> foobar = BaseType('foobar', np.arange(4, dtype='i'))
    >>> foo[-2:]
    <BaseType with data array([2, 3], dtype=int32)>
    >>> foo[-2:].data
    array([2, 3], dtype=int32)
    >>> foo.data[-2:]
    array([2, 3], dtype=int32)
    >>> foo.dtype
    dtype('int32')
    >>> foo.shape
    (4,)
    >>> for record in foo.iterdata():
    ...     print(record)
    0
    1
    2
    3

It is also possible to iterate directly over a `BaseType`::
    >>> for record in foo:
    ...     print(record)
    0
    1
    2
    3

This is however discouraged because this approach will soon be deprecated
for the `SequenceType` where only the ``.iterdata()`` will continue to be
supported.

The `BaseType` is simply a thin wrapper over Numpy arrays, implementing the
`dtype` and `shape` attributes, and the sequence and iterable protocols. Why
not use Numpy arrays directly then? First, `BaseType` can have additional
metadata added to them; this include names for its dimensions and also
arbitrary attributes::

    >>> foo.attributes
    {}
    >>> foo.attributes['units'] = 'm/s'
    >>> foo.units
    'm/s'

    >>> foo.dimensions
    ()
    >>> foo.dimensions = ('time',)

Second, `BaseType` can hold data objects other than Numpy arrays. There are
more complex data objects, like `pydap.handlers.dap.BaseProxy`, which acts as a
transparent proxy to a remote dataset, exposing it through the same interface.

Now that we have some data, we can organize it using containers::

    >>> dataset = DatasetType('baz')
    >>> dataset['s'] = StructureType('s')
    >>> dataset['s']['foo'] = foo
    >>> dataset['s']['bar'] = bar
    >>> dataset['s']['foobar'] = foobar

`StructureType` and `DatasetType` are very similar; the only difference is that
`DatasetType` should be used as the root container for a dataset. They behave
like ordered Python dictionaries::

    >>> list(dataset.s.keys())
    ['foo', 'bar', 'foobar']

Slicing these datasets with a list of keywords yields a `StructureType`
or `DatasetType` with only a subset of the children::

    >>> dataset.s['foo', 'foobar']
    <StructureType with children 'foo', 'foobar'>
    >>> list(dataset.s['foo', 'foobar'].keys())
    ['foo', 'foobar']

In the same way, the ``.items()`` and ``.values()`` methods are like in python
dictionaries and they iterate over sliced values.

Selecting only one child returns the child::

    >>> dataset.s['foo']
    <BaseType with data array([0, 1, 2, 3], dtype=int32)>

A `GridType` is a special container where the first child should be an
n-dimensional `BaseType`. This children should be followed by `n` additional
vector `BaseType` objects, each one describing one of the axis of the
variable::

    >>> rain = GridType('rain')
    >>> rain['rain'] = BaseType(
    ...     'rain', np.arange(6).reshape(2, 3), dimensions=('y', 'x'))
    >>> rain['x'] = BaseType('x', np.arange(3), units='degrees_east')
    >>> rain['y'] = BaseType('y', np.arange(2), units='degrees_north')
    >>> rain.array  #doctest: +ELLIPSIS
    <BaseType with data array([[0, 1, 2],
           [3, 4, 5]])>
    >>> type(rain.maps)
    <class 'collections.OrderedDict'>
    >>> for item in rain.maps.items():
    ...     print(item)
    ('x', <BaseType with data array([0, 1, 2])>)
    ('y', <BaseType with data array([0, 1])>)

There a last special container called `SequenceType`. This data structure is
analogous to a series of records (or rows), with one column for each of its
children::

    >>> cast = SequenceType('cast')
    >>> cast['depth'] = BaseType('depth', positive='down', units='m')
    >>> cast['temperature'] = BaseType('temperature', units='K')
    >>> cast['salinity'] = BaseType('salinity', units='psu')
    >>> cast['id'] = BaseType('id')
    >>> cast.data = np.array([(10., 17., 35., '1'), (20., 15., 35., '2')],
    ...     dtype=np.dtype([('depth', np.float32), ('temperature', np.float32),
    ...     ('salinity', np.float32), ('id', np.dtype('|S1'))]))

Note that the data in this case is attributed to the `SequenceType`, and is
composed of a series of values for each of the children.  Pydap `SequenceType`
obects are very flexible. Data can be accessed by iterating over the object::

    >>> for record in cast.iterdata():
    ...     print(record)
    (10.0, 17.0, 35.0, '1')
    (20.0, 15.0, 35.0, '2')

It is possible to select only a few variables::

    >>> for record in cast['salinity', 'depth'].iterdata():
    ...     print(record)
    (35.0, 10.0)
    (35.0, 20.0)

    >>> cast['temperature'].dtype
    dtype('float32')
    >>> cast['temperature'].shape
    (2,)

When sliced, it yields the underlying array:
    >>> type(cast['temperature'][-1:])
    <class 'pydap.model.BaseType'>
    >>> for record in cast['temperature'][-1:].iterdata():
    ...     print(record)
    15.0

When constrained, it yields the SequenceType:
    >>> type(cast[ cast['temperature'] < 16 ])
    <class 'pydap.model.SequenceType'>
    >>> for record in cast[ cast['temperature'] < 16 ].iterdata():
    ...     print(record)
    (20.0, 15.0, 35.0, '2')

As mentioned earlier, it is still possible to iterate directly over data::

    >>> for record in cast[ cast['temperature'] < 16 ]:
    ...     print(record)
    (20.0, 15.0, 35.0, '2')

But this is discouraged as this will be deprecated soon. The ``.iterdata()`` is
therefore highly recommended.
"""

import operator
import copy
from six.moves import reduce, map
from six import string_types
import numpy as np
from collections import OrderedDict, Mapping
import warnings

from .lib import quote, decode_np_strings


__all__ = [
    'BaseType', 'StructureType', 'DatasetType', 'SequenceType', 'GridType']


class DapType(object):

    """The common Opendap type.

    This is a base class, defining common methods and attributes for all other
    classes in the data model.

    """

    def __init__(self, name='nameless', attributes=None, **kwargs):
        self.name = quote(name)
        self.attributes = attributes or {}
        self.attributes.update(kwargs)

        # Set the id to the name.
        self._id = self.name

    def __repr__(self):
        return 'DapType(%s)' % ', '.join(
            map(repr, [self.name, self.attributes]))

    # The id.
    def _set_id(self, id):
        self._id = id

        # Update children id.
        for child in self.children():
            child.id = '%s.%s' % (id, child.name)

    def _get_id(self):
        return self._id

    id = property(_get_id, _set_id)

    def __getattr__(self, attr):
        """Attribute shortcut.

        Data classes have their attributes stored in the `attributes`
        attribute, a dictionary. For convenience, access to attributes can be
        shortcut by accessing the attributes directly::

            >>> var = DapType('var')
            >>> var.attributes['foo'] = 'bar'
            >>> var.foo
            'bar'

        This will return the value stored under `attributes`.

        """
        try:
            return self.attributes[attr]
        except (KeyError, TypeError):
            raise AttributeError(
                "'%s' object has no attribute '%s'"
                % (type(self), attr))

    def children(self):
        """Return iterator over children."""
        return ()


class BaseType(DapType):

    """A thin wrapper over Numpy arrays."""

    def __init__(self, name='nameless', data=None, dimensions=None,
                 attributes=None, **kwargs):
        super(BaseType, self).__init__(name, attributes, **kwargs)
        self.data = data
        self.dimensions = dimensions or ()

        # these are set when not data is present (eg, when parsing a DDS)
        self._dtype = None
        self._shape = ()

    def __repr__(self):
        return '<%s with data %s>' % (type(self).__name__, repr(self.data))

    @property
    def dtype(self):
        """Property that returns the data dtype."""
        return self.data.dtype

    @property
    def shape(self):
        """Property that returns the data shape."""
        return self.data.shape

    def reshape(self, *args):
        """Method that reshapes the data:"""
        self.data = self.data.reshape(*args)
        return self

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def size(self):
        return int(np.prod(self.shape))

    def __copy__(self):
        """A lightweight copy of the variable.

        This will return a new object, with a copy of the attributes,
        dimensions, same name, and a view of the data.

        """
        out = type(self)(self.name, self.data, self.dimensions[:],
                         self.attributes.copy())
        out.id = self.id
        return out

    # Comparisons are passed to the data.
    def __eq__(self, other):
        return self.data == other

    def __ne__(self, other):
        return self.data != other

    def __ge__(self, other):
        return self.data >= other

    def __le__(self, other):
        return self.data <= other

    def __gt__(self, other):
        return self.data > other

    def __lt__(self, other):
        return self.data < other

    # Implement the sequence and iter protocols.
    def __getitem__(self, index):
        out = copy.copy(self)
        out.data = self._get_data_index(index)
        return out

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        if self._is_string_dtype:
            for item in self.data:
                yield np.vectorize(decode_np_strings)(item)
        else:
            for item in self.data:
                yield item

    @property
    def _is_string_dtype(self):
        return hasattr(self._data, 'dtype') and self._data.dtype.char == 'S'

    def iterdata(self):
        """ This method was added to mimic new SequenceType method."""
        return iter(self)

    def __array__(self):
        return self._get_data_index()

    def _get_data_index(self, index=Ellipsis):
        if self._is_string_dtype:
            return np.vectorize(decode_np_strings)(self._data[index])
        else:
            return self._data[index]

    def _get_data(self):
        return self._data

    def _set_data(self, data):
        self._data = data
        if np.isscalar(data):
            # Convert scalar data to
            # numpy scalar, otherwise
            # ``.dtype`` and ``.shape``
            # methods will fail.
            self._data = np.array(data)
    data = property(_get_data, _set_data)


class StructureType(DapType, Mapping):
    """A dict-like object holding other variables."""

    def __init__(self, name='nameless', attributes=None, **kwargs):
        super(StructureType, self).__init__(name, attributes, **kwargs)

        # allow some keys to be hidden:
        self._visible_keys = []
        self._dict = OrderedDict()

    def __repr__(self):
        return '<%s with children %s>' % (
            type(self).__name__, ', '.join(map(repr, self._visible_keys)))

    def __getattr__(self, attr):
        """Lazy shortcut return children."""
        try:
            return self[attr]
        except:
            return DapType.__getattr__(self, attr)

    def __contains__(self, key):
        return (key in self._visible_keys)

    # __iter__, __getitem__, __len__ are required for Mapping
    # From these, keys, items, values, get, __eq__,
    # and __ne__ are obtained.
    def __iter__(self):
        for key in self._dict.keys():
            if key in self._visible_keys:
                yield key

    def _all_keys(self):
        # used in ..handlers.lib
        return iter(self._dict.keys())

    def _getitem_string(self, key):
        """ Assume that key is a string type """
        try:
            return self._dict[quote(key)]
        except KeyError:
            splitted = key.split('.')
            if len(splitted) > 1:
                try:
                    return self[splitted[0]]['.'.join(splitted[1:])]
                except KeyError:
                    return self['.'.join(splitted[1:])]
            else:
                raise

    def _getitem_string_tuple(self, key):
        """ Assume that key is a tuple of strings """
        out = type(self)(self.name, data=self.data,
                         attributes=self.attributes.copy())
        for name in key:
            out[name] = copy.copy(self._getitem_string(name))
        return out

    def __getitem__(self, key):
        if isinstance(key, string_types):
            return self._getitem_string(key)
        elif (isinstance(key, tuple) and
              all(isinstance(name, string_types)
                  for name in key)):
            out = copy.copy(self)
            out._visible_keys = list(key)
            return out
        else:
            raise KeyError(key)

    def __len__(self):
        return len(self._visible_keys)

    def children(self):
        # children method always yields an
        # iterator on visible children:
        for key in self._visible_keys:
            yield self[key]

    def __setitem__(self, key, item):
        key = quote(key)
        if key != item.name:
            raise KeyError(
                'Key "%s" is different from variable name "%s"!' %
                (key, item.name))

        if key in self:
            del self[key]
        self._dict[key] = item
        # By default added keys are visible:
        self._visible_keys.append(key)

        # Set item id.
        item.id = '%s.%s' % (self.id, item.name)

    def __delitem__(self, key):
        del self._dict[key]
        try:
            self._visible_keys.remove(key)
        except ValueError:
            pass

    def _get_data(self):
        return [var.data for var in self.children()]

    def _set_data(self, data):
        for col, var in zip(data, self.children()):
            var.data = col
    data = property(_get_data, _set_data)

    def __copy__(self):
        """Return a lightweight copy of the Structure.

        The method will return a new Structure with cloned children, but any
        data object are not copied.

        """
        out = type(self)(self.name, self.attributes.copy())
        out.id = self.id

        # Clone all children too.
        for child in self._dict.values():
            out[child.name] = copy.copy(child)
        return out


class DatasetType(StructureType):

    """A root Dataset.

    The Dataset is a Structure, but it names does not compose the id hierarchy:

        >>> dataset = DatasetType("A")
        >>> dataset["B"] = BaseType("B")
        >>> dataset["B"].id
        'B'

    """

    def __setitem__(self, key, item):
        StructureType.__setitem__(self, key, item)

        # The dataset name does not goes into the children ids.
        item.id = item.name

    def _set_id(self, id):
        """The dataset name is not included in the children ids."""
        self._id = id

        for child in self.children():
            child.id = child.name


class SequenceType(StructureType):

    """A container that stores data in a Numpy array.

    Here's a standard dataset for testing sequential data:

        >>> import numpy as np
        >>> data = np.array([
        ... (10, 15.2, 'Diamond_St'),
        ... (11, 13.1, 'Blacktail_Loop'),
        ... (12, 13.3, 'Platinum_St'),
        ... (13, 12.1, 'Kodiak_Trail')],
        ... dtype=np.dtype([
        ... ('index', np.int32), ('temperature', np.float32),
        ... ('site', np.dtype('|S14'))]))
        ...
        >>> seq = SequenceType('example')
        >>> seq['index'] = BaseType('index')
        >>> seq['temperature'] = BaseType('temperature')
        >>> seq['site'] = BaseType('site')
        >>> seq.data = data

    Iteraring over the sequence returns data:

        >>> for line in seq.iterdata():
        ...     print(line)
        (10, 15.2, 'Diamond_St')
        (11, 13.1, 'Blacktail_Loop')
        (12, 13.3, 'Platinum_St')
        (13, 12.1, 'Kodiak_Trail')

    The order of the variables can be changed:

        >>> for line in seq['temperature', 'site', 'index'].iterdata():
        ...     print(line)
        (15.2, 'Diamond_St', 10)
        (13.1, 'Blacktail_Loop', 11)
        (13.3, 'Platinum_St', 12)
        (12.1, 'Kodiak_Trail', 13)

    We can iterate over children:

        >>> for line in seq['temperature'].iterdata():
        ...     print(line)
        15.2
        13.1
        13.3
        12.1

    We can filter the data:

        >>> for line in seq[ seq.index > 10 ].iterdata():
        ...     print(line)
        (11, 13.1, 'Blacktail_Loop')
        (12, 13.3, 'Platinum_St')
        (13, 12.1, 'Kodiak_Trail')

        >>> for line in seq[ seq.index > 10 ]['site'].iterdata():
        ...     print(line)
        Blacktail_Loop
        Platinum_St
        Kodiak_Trail

        >>> for line in (seq['site', 'temperature'][seq.index > 10]
        ...              .iterdata()):
        ...     print(line)
        ('Blacktail_Loop', 13.1)
        ('Platinum_St', 13.3)
        ('Kodiak_Trail', 12.1)

    Or slice it:

        >>> for line in seq[::2].iterdata():
        ...     print(line)
        (10, 15.2, 'Diamond_St')
        (12, 13.3, 'Platinum_St')

        >>> for line in seq[ seq.index > 10 ][::2]['site'].iterdata():
        ...     print(line)
        Blacktail_Loop
        Kodiak_Trail

        >>> for line in seq[ seq.index > 10 ]['site'][::2]:
        ...     print(line)
        Blacktail_Loop
        Kodiak_Trail

    """

    def __init__(self, name='nameless', data=None, attributes=None, **kwargs):
        super(SequenceType, self).__init__(name, attributes, **kwargs)
        self._data = data

    def _set_data(self, data):
        self._data = data
        for child in self.children():
            tokens = child.id[len(self.id)+1:].split('.')
            child.data = reduce(operator.getitem, [data] + tokens)

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)

    def iterdata(self):
        for line in self.data:
            yield tuple(map(decode_np_strings, line))

    def __iter__(self):
        # This method should be removed in Pydap 3.4
        warnings.warn('Starting with Pydap 3.4 '
                      '``for val in sequence: ...`` '
                      'will give children names. '
                      'To iterate over data the construct '
                      '``for val in sequence.iterdata(): ...``'
                      'is available now and will be supported in the'
                      'future to iterate over data.',
                      PendingDeprecationWarning)
        return self.iterdata()

    def __len__(self):
        # This method should be removed in Pydap 3.4
        warnings.warn('Starting with Pydap 3.4, '
                      '``len(sequence)`` will give '
                      'the number of children and not the '
                      'length of the data.',
                      PendingDeprecationWarning)
        return len(self.data)

    def items(self):
        # This method should be removed in Pydap 3.4
        for key in self._visible_keys:
            yield (key, self[key])

    def values(self):
        # This method should be removed in Pydap 3.4
        for key in self._visible_keys:
            yield self[key]

    def keys(self):
        # This method should be removed in Pydap 3.4
        return iter(self._visible_keys)

    def __contains__(self, key):
        # This method should be removed in Pydap 3.4
        return (key in self._visible_keys)

    def __getitem__(self, key):
        # If key is a string, return child with the corresponding data.
        if isinstance(key, string_types):
            return self._getitem_string(key)

        # If it's a tuple, return a new `SequenceType` with selected children.
        elif isinstance(key, tuple):
            out = self._getitem_string_tuple(key)
            # copy.copy() is necessary here because a view will be returned in
            # the future:
            out.data = copy.copy(self.data[list(key)])
            return out

        # Else return a new `SequenceType` with the data sliced.
        else:
            out = copy.copy(self)
            out.data = self.data[key]
            return out

    def __copy__(self):
        """Return a lightweight copy of the Sequence.

        The method will return a new Sequence with cloned children, but any
        data object are not copied.

        """
        out = type(self)(self.name, self.data, self.attributes.copy())
        out.id = self.id

        # Clone children too.
        for child in self.children():
            out[child.name] = copy.copy(child)
        return out


class GridType(StructureType):

    """A Grid container.

    The Grid is a Structure with an array and the corresponding axes.

    """

    def __init__(self, name='nameless', attributes=None, **kwargs):
        super(GridType, self).__init__(name, attributes, **kwargs)
        self._output_grid = True

    def __repr__(self):
        return '<%s with array %s and maps %s>' % (
            type(self).__name__,
            repr(list(self.keys())[0]),
            ', '.join(map(repr, list(self.keys())[1:])))

    def __getitem__(self, key):
        # Return a child.
        if isinstance(key, string_types):
            return self._getitem_string(key)

        # Return a new `GridType` with part of the data.
        elif (isinstance(key, tuple) and
              all(isinstance(name, string_types)
                  for name in key)):
            out = self._getitem_string_tuple(key)
            for var in out.children():
                var.data = self[var.name].data
            return out
        else:
            if not self.output_grid:
                return self.array[key]

            if not isinstance(key, tuple):
                key = (key,)

            out = copy.copy(self)
            for var, slice_ in zip(out.children(), [key] + list(key)):
                var.data = self[var.name].data[slice_]
            return out

    @property
    def dtype(self):
        """Return the first children dtype."""
        return self.array.dtype

    @property
    def shape(self):
        """Return the first children shape."""
        return self.array.shape

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def size(self):
        return int(np.prod(self.shape))

    @property
    def output_grid(self):
        return self._output_grid

    def set_output_grid(self, key):
        self._output_grid = bool(key)

    @property
    def array(self):
        """Return the first children."""
        return self[list(self.keys())[0]]

    def __array__(self):
        return self.array.data

    @property
    def maps(self):
        """Return the axes in an ordered dict."""
        return OrderedDict([(k, self[k]) for k in self.keys()][1:])

    @property
    def dimensions(self):
        """Return the name of the axes."""
        return tuple(list(self.keys())[1:])

"""This is the pydap data model, an implementation of the Data Access Protocol
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

    >>> foo.dims
    []
    >>> foo.dims = ['time',]

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
    ...     'rain', np.arange(6).reshape(2, 3), dims=['y', 'x'])
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
composed of a series of values for each of the children.  pydap `SequenceType`
obects are very flexible. Data can be accessed by iterating over the object::

    >>> for record in cast.iterdata():
    ...     print(record)
    (np.float32(10.0), np.float32(17.0), np.float32(35.0), '1')
    (np.float32(20.0), np.float32(15.0), np.float32(35.0), '2')

It is possible to select only a few variables::

    >>> for record in cast['salinity', 'depth'].iterdata():
    ...     print(record)
    (np.float32(35.0), np.float32(10.0))
    (np.float32(35.0), np.float32(20.0))

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
    (np.float32(20.0), np.float32(15.0), np.float32(35.0), '2')

As mentioned earlier, it is still possible to iterate directly over data::

    >>> for record in cast[ cast['temperature'] < 16 ]:
    ...     print(record)
    (np.float32(20.0), np.float32(15.0), np.float32(35.0), '2')

But this is discouraged as this will be deprecated soon. The ``.iterdata()`` is
therefore highly recommended.
"""

import copy
import operator
import re
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from functools import reduce
from typing import Optional, Union

import numpy as np
import requests
import requests_cache

from .lib import _quote, decode_np_strings, tree, walk

__all__ = [
    "BaseType",
    "StructureType",
    "DatasetType",
    "SequenceType",
    "GridType",
    "GroupType",
]


class DapType(object):
    """The common Opendap type.

    This is a base class, defining common methods and attributes for all other
    classes in the data model.

    """

    def __init__(self, name="nameless", attributes=None, **kwargs):
        self.name = _quote(name)
        self.attributes = attributes or {}
        self.attributes.update(kwargs)

        # Set the id to the name.
        self._id = self.name

    def __repr__(self):
        return "DapType(%s)" % ", ".join(map(repr, [self.name, self.attributes]))

    # The id.
    def _set_id(self, id):
        self._id = id

        # Update children id.
        for child in self.children():
            # pass
            child.id = "%s.%s" % (id, child.name)

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
                "'%s' object has no attribute '%s'" % (type(self), attr)
            )

    def children(self):
        """Return iterator over children."""
        return ()


class BaseType(DapType):
    """A thin wrapper over Numpy arrays."""

    def __init__(
        self, name="nameless", data=None, dims=None, attributes=None, **kwargs
    ):
        super(BaseType, self).__init__(name, attributes, **kwargs)
        self.data = data
        self.dims = dims or []
        # these are set when not data is present (eg, when parsing a DDS)
        self._dtype = None
        self._shape = ()
        self._itemsize = None
        self._nbytes = None

    def __repr__(self):
        return "<%s with data %s>" % (type(self).__name__, repr(self.data))

    @property
    def path(self):
        try:
            return self.data.path
        except AttributeError:
            return None

    @property
    def dtype(self):
        """Property that returns the data dtype."""
        return self.data.dtype

    @property
    def shape(self):
        """Property that returns the data shape."""
        try:
            return self.data.shape
        except AttributeError:
            return self._shape

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

    @property
    def itemsize(self):
        return np.asarray([], dtype=self.data.dtype).itemsize

    @property
    def nbytes(self):
        return self.itemsize * self.size

    def __copy__(self):
        """A lightweight copy of the variable.

        This will return a new object, with a copy of the attributes,
        dimensions, same name, and a view of the data.

        """
        out = type(self)(self.name, self.data, self.dims[:], self.attributes.copy())
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
        if type(self.data).__name__ == "BaseProxyDap4":
            out.attributes["checksum"] = self.data.checksum
            out.attributes["Maps"] = self.Maps
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
        return hasattr(self._data, "dtype") and self._data.dtype.char == "S"

    def iterdata(self):
        """This method was added to mimic new SequenceType method."""
        return iter(self)

    def __array__(self):
        return self._get_data_index()

    def _get_data_index(self, index=Ellipsis):
        if self._is_string_dtype and isinstance(self._data, np.ndarray):
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

    def __init__(self, name="nameless", attributes=None, **kwargs):
        super(StructureType, self).__init__(name, attributes, **kwargs)

        # allow some keys to be hidden:
        self._visible_keys = []
        self._dict = OrderedDict()

    def __repr__(self):
        return "<%s with children %s>" % (
            type(self).__name__,
            ", ".join(map(repr, self._visible_keys)),
        )

    def __getattr__(self, attr):
        """Lazy shortcut return children."""
        try:
            return self[attr]
        except Exception:
            return DapType.__getattr__(self, attr)

    def __contains__(self, key):
        return key in self._visible_keys

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
        """Assume that key is a string type"""
        try:
            return self._dict[_quote(key)]
        except KeyError:
            splitted = key.split(".")
            if len(splitted) > 1:
                try:
                    return self[splitted[0]][".".join(splitted[1:])]
                except (KeyError, IndexError):
                    return self[".".join(splitted[1:])]
            else:
                raise

    def _getitem_string_tuple(self, key):
        """Assume that key is a tuple of strings"""
        out = type(self)(self.name, data=self.data, attributes=self.attributes.copy())
        for name in key:
            out[name] = copy.copy(self._getitem_string(name))
        return out

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._getitem_string(key)
        elif isinstance(key, tuple) and all(isinstance(name, str) for name in key):
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

    def tree(self):
        return tree(self)

    def __setitem__(self, key, item):
        key = _quote(key)
        if key != item.name:
            raise KeyError(
                'Key "%s" is different from variable name "%s"!' % (key, item.name)
            )

        if key in self:
            del self[key]
        self._dict[key] = item
        # By default added keys are visible:
        self._visible_keys.append(key)

        # Set item id.
        item.id = "%s.%s" % (self.id, item.name)

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

    def __shallowcopy__(self):
        out = type(self)(self.name, self.attributes.copy())
        out.id = self.id
        return out

    def __copy__(self):
        """Return a lightweight copy of the Structure.

        The method will return a new Structure with cloned children, but any
        data object are not copied.

        """
        out = self.__shallowcopy__()

        # Clone all children too.
        for child in self._dict.values():
            out[child.name] = copy.copy(child)
        return out

    @property
    def type(self):
        return "Structure"

    def structures(self) -> dict:
        out = {}
        Gs = [key for key in self.children() if isinstance(key, StructureType)]
        Strs = [key for key in Gs if key.type == "Structure"]
        for var in Strs:
            out.update({var.name: [key.name for key in var.children()]})
        return out

    def groups(self) -> dict:
        """Returns fqn for all (nested) groups"""
        out = {}
        for var in walk(self, GroupType):
            if var.type == "Group":
                out.update({var.name: var.path})
        return out

    def sequences(self) -> dict:
        "returns all (nested) sequences"
        out = {}
        for var in walk(self, SequenceType):
            if var.type == "Sequence":
                out.update({var.name: [key.name for key in var.children()]})
        return out

    def grids(self) -> dict:
        """returns all GridType (DAP2) objects in a"""
        out = {}
        for var in walk(self, GridType):
            out.update({var.name: {"shape": var.shape, "maps": list(var.maps)}})
        return out

    def variables(self) -> dict:
        """returns all variables at the present hierarcy"""
        out = {}
        Bcs = [key for key in self.children() if isinstance(key, BaseType)]
        for var in Bcs:
            if "dims" in var.attributes:
                dims = var.dims
            else:
                dims = []
            out.update(
                {var.name: {"dtype": var.dtype, "shape": var.shape, "dims": dims}}
            )
        return out


class DatasetType(StructureType):
    """A root Dataset.

    The Dataset is a Structure, but it names does not compose the id hierarchy:

        >>> dataset = DatasetType("A")
        >>> dataset["B"] = BaseType("B")
        >>> dataset["B"].id
        'B'
    """

    def __init__(
        self,
        name="nameless",
        attributes=None,
        session: Optional[Union[requests.Session, requests_cache.CachedSession]] = None,
        **kwargs,
    ):
        super().__init__(name, attributes, **kwargs)
        # Explicit type checking to enforce the allowed types
        if session is not None and not isinstance(
            session, (requests.Session, requests_cache.CachedSession)
        ):
            raise TypeError(
                "`session` must be a `requests.Session` or "
                "`requests_cache.CachedSession` instance"
            )
        self._session = session

    @property
    def session(self):
        """Read-only property for session."""
        return self._session

    @session.setter
    def session(self, value):
        """Prevent re-assignment of session."""
        if self.session:
            raise AttributeError("Cannot modify `session` after it has been set.")
        else:
            if isinstance(value, (requests.Session, requests_cache.CachedSession)):
                self._session = value
            else:
                raise TypeError(
                    "`session` must be a `requests.Session` or "
                    "`requests_cache.CachedSession` instance"
                )

    def __setitem__(self, key, item):
        # key a path-like only in DAP4
        split_by = " "
        if len(self.groups()) > 0:
            if key[0] == "/":
                key = key[1:]
            split_by += "/"
        if len(self.sequences()) > 0 or len(self.structures()) > 0:
            split_by += "."
        parts = re.split("[" + split_by + "]", key)
        N = len(parts)
        if N > 1:
            # add parent container type if not there
            if parts[0] not in self._dict:
                self._visible_keys.append(parts[0])
            #  iterate over all groups to reach DAP object
            current = self._dict
            for j in range(N - 1):
                if parts[j] not in current:  # and Flat is not None
                    #     # This current approach works when parsing a DMR
                    #     # with only Groups and arrays. Need to enable
                    #     # Sequences and Structures. This works with all
                    #     # DAP4 when creating Dataset manally.
                    current[parts[j]] = GroupType(parts[j])
                current = current[parts[j]]
            current[parts[-1]] = item
        else:
            if key[0] == "/" and len(self.groups()) > 0:
                key = key[1:]
            key = _quote(key)
            if key != item.name:
                raise KeyError(
                    'Key "%s" is different from variable name "%s"!' % (key, item.name)
                )

            if key in self:
                del self[key]

            self._dict[key] = item
            # By default added keys are visible:
            self._visible_keys.append(key)
        key = key.replace("%2E", ".")
        if len(key.split(".")) == 1:
            # The parent name does not go into the children ids.
            item.id = item.name
        else:
            parts = key.split("/")[-1]
            item.id = (".").join(parts.split("."))
            # Set item id.
            # item.id  = "%s.%s" % (parent_name, item.name)

    def _getitem_string(self, key):
        """Assume that key is a string type"""
        try:
            return self._dict[_quote(key)]
        except KeyError:
            parts = key.split("/")
            Np = len(parts)
            if Np <= 2 and set(parts) == set([""]):
                return self
            elif Np > 1 and set(parts) != set([""]):
                if parts[0] == "":
                    parts = parts[1:]
                    Np = len(parts)
                current = self
                if Np == 1:
                    return self[parts[0]]
                else:
                    for j in range(Np):
                        key_c = ("/").join(parts[j:])
                        splitted = key_c.split(".")
                        if key_c in current.keys():
                            return current[key_c]
                        elif len(splitted) > 1 and splitted[0] in current.keys():
                            return current[key_c]
                        else:
                            current = current[parts[j]]
            else:
                splitted = key.split(".")
                if len(splitted) > 1:
                    try:
                        return self[splitted[0]][".".join(splitted[1:])]
                    except (KeyError, IndexError):
                        return self[".".join(splitted[1:])]
                else:
                    raise

    def _set_id(self, id):
        """The dataset name is not included in the children ids."""
        self._id = id

        for child in self.children():
            child.id = child.name

    def to_netcdf(self, *args, **kwargs):
        try:
            from .apis.netcdf4 import NetCDF

            return NetCDF(self, *args, **kwargs)
        except ImportError:
            raise NotImplementedError(".to_netcdf requires the netCDF4 " "package.")

    def change_order(self, order):
        self._dict = OrderedDict((k, self._dict[k]) for k in order)

    @property
    def type(self):
        return ()

    @property
    def nbytes(self):
        """Returns the number of bytes occupied in aggregation by all
        uncompressed, BaseType data in the DatasetType. Attributes are
        not included in the computation of value"""
        nbytes = 0
        for var in walk(self, BaseType):
            nbytes += var.nbytes
        return nbytes

    def createDapType(self, daptype, name, **attrs):
        # Creates a temporal quasi FQN by replacing all `.` with `/`
        # since these are safe to escape. This catches all cases
        # much more cleanly. User specifies FQN but DAPtype is defined
        # within the method so OK.
        split_by = " "
        if len(self.groups()) > 0:  # true
            split_by += "/"
        else:
            if name[0] == "/":
                name = name[1:]
        if len(self.sequences()) > 0 or len(self.structures()) > 0:
            split_by += "."
        parts = re.split("[" + split_by + "]", name)
        item = daptype(name=parts[-1], **attrs)
        DatasetType.__setitem__(self, name, item)

    def createGroup(self, name, **attrs):
        """
        Creates a Group from `root`, even in the presence of nested Groups.
        Uses the `Fully Qualifying Name`. Parent `Group` must exist.

        Also: https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1
        """
        path = "/"
        if name[0] != "/":
            name = "/" + name
        if len(name.split("/")) > 2:
            path = ("/").join(name.split("/")[:-1]) + "/"
        parts = re.split(r"[/]", name)
        try:
            for i in range(1, len(parts)):
                self[("/").join(parts[:i])]
        except KeyError:
            warnings.warn(
                """Failed to create `{}` because parent `{}` does not exist!
                """.format(
                    parts[-1], parts[-2]
                )
            )
            return None
        if "path" in attrs:
            del attrs["path"]
        return self.createDapType(GroupType, name, path=path, **attrs)

    def createVariable(self, name, **attrs):
        """
        Creates a Variable (`BaseType`) from `root`, even in the presence of nested
        DAPTypes (i.e. `GroupType`, `SequenceType`, `StructureType`). Uses the
        `Fully Qualifying Name`. Parent `DAPType` must exist!

        Also: https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1

        """
        return self.createDapType(BaseType, name, **attrs)

    def createSequence(self, name, **attrs):
        """
        Creates a Sequence (`SequenceType`) from `root`, even in the presence of nested
        DAPTypes (i.e. `GroupType`, `SequenceType`, `StructureType`).
        Uses the `Fully Qualifying Name`. Parent `DAPType` must exist!

        Also: https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1
        """
        return self.createDapType(SequenceType, name, **attrs)

    def createStructure(self, name, **attrs):
        """
        Creates a Structure (`StructureType`) from `root`, even in the presence of
        nested DAPTypes (i.e. `GroupType`, `SequenceType`, `StructureType`).
        Uses the `Fully Qualifying Name`. Parent `DAPType` must exist!

        Also: https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1
        """
        return self.createDapType(StructureType, name, **attrs)


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
        (np.int32(10), np.float32(15.2), 'Diamond_St')
        (np.int32(11), np.float32(13.1), 'Blacktail_Loop')
        (np.int32(12), np.float32(13.3), 'Platinum_St')
        (np.int32(13), np.float32(12.1), 'Kodiak_Trail')

    The order of the variables can be changed:

        >>> for line in seq['temperature', 'site', 'index'].iterdata():
        ...     print(line)
        (np.float32(15.2), 'Diamond_St', np.int32(10))
        (np.float32(13.1), 'Blacktail_Loop', np.int32(11))
        (np.float32(13.3), 'Platinum_St', np.int32(12))
        (np.float32(12.1), 'Kodiak_Trail', np.int32(13))

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
        (np.int32(11), np.float32(13.1), 'Blacktail_Loop')
        (np.int32(12), np.float32(13.3), 'Platinum_St')
        (np.int32(13), np.float32(12.1), 'Kodiak_Trail')

        >>> for line in seq[ seq.index > 10 ]['site'].iterdata():
        ...     print(line)
        Blacktail_Loop
        Platinum_St
        Kodiak_Trail

        >>> for line in (seq['site', 'temperature'][seq.index > 10]
        ...              .iterdata()):
        ...     print(line)
        ('Blacktail_Loop', np.float32(13.1))
        ('Platinum_St', np.float32(13.3))
        ('Kodiak_Trail', np.float32(12.1))

    Or slice it:

        >>> for line in seq[::2].iterdata():
        ...     print(line)
        (np.int32(10), np.float32(15.2), 'Diamond_St')
        (np.int32(12), np.float32(13.3), 'Platinum_St')

        >>> for line in seq[ seq.index > 10 ][::2]['site'].iterdata():
        ...     print(line)
        Blacktail_Loop
        Kodiak_Trail

        >>> for line in seq[ seq.index > 10 ]['site'][::2]:
        ...     print(line)
        Blacktail_Loop
        Kodiak_Trail

    """

    def __init__(self, name="nameless", data=None, attributes=None, **kwargs):
        super(SequenceType, self).__init__(name, attributes, **kwargs)
        self._data = data

    def _set_data(self, data):
        self._data = data
        for child in self.children():
            tokens = child.id[len(self.id) + 1 :].split(".")
            child.data = reduce(operator.getitem, [data] + tokens)

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)

    def iterdata(self):
        for line in self.data:
            yield tuple(map(decode_np_strings, line))

    def __iter__(self):
        return self.iterdata()

    def __len__(self):
        return len(self.data)

    def items(self):
        # This method should be removed in pydap 3.4
        for key in self._visible_keys:
            yield (key, self[key])

    def values(self):
        # This method should be removed in pydap 3.4
        for key in self._visible_keys:
            yield self[key]

    def keys(self):
        # This method should be removed in pydap 3.4
        return iter(self._visible_keys)

    def __contains__(self, key):
        # This method should be removed in pydap 3.4
        return key in self._visible_keys

    def __getitem__(self, key):
        # If key is a string, return child with the corresponding data.
        if isinstance(key, str):
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

    def __shallowcopy__(self):
        out = type(self)(self.name, self.data, self.attributes.copy())
        out.id = self.id
        return out

    @property
    def type(self):
        return "Sequence"


class GridType(StructureType):
    """A Grid container.

    The Grid is a Structure with an array and the corresponding axes.

    """

    def __init__(self, name="nameless", attributes=None, **kwargs):
        super(GridType, self).__init__(name, attributes, **kwargs)
        self._output_grid = True

    def __repr__(self):
        return "<%s with array %s and maps %s>" % (
            type(self).__name__,
            repr(list(self.keys())[0]),
            ", ".join(map(repr, list(self.keys())[1:])),
        )

    def __getitem__(self, key):
        # Return a child.
        if isinstance(key, str):
            return self._getitem_string(key)

        # Return a new `GridType` with part of the data.
        elif isinstance(key, tuple) and all(isinstance(name, str) for name in key):
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
                if type(self.data).__name__ == "BaseProxyDap4":
                    pass
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

    @property
    def type(self):
        return "Grid"


class GroupType(StructureType):
    """A Group container.

    A folder-like DAP container which may have other DAP types like
    Sequences, Structures, DataArrays, and other Groups, as children.

    Groups in OPeNDAP:
        - There is at least the root Group `/`.
        - Must have a name.
        - There is a single parent to a Group (tree hierarchy).
        - Attributes are Global at the Group level.
        - Can have share dimensions, which are scoped to all children (not to parent)

    Examples:

    """

    def __setitem__(self, key, item):
        StructureType.__setitem__(self, key, item)

        # The Group name does (not) go into the children ids.

        item.id = item.name
        # self._dict[key] = item

        # # # By default added keys are visible:
        # self._visible_keys.append(key)

    def _set_id(self, id):
        """The dataset name is (not) included in the children ids."""
        self._id = id

        for child in self.children():
            child.id = child.name

    @property
    def type(self):
        return "Group"

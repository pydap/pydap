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
    <BaseType with data array(shape=(2,), dtype=int32)>
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
    <BaseType with data array(shape=(4,), dtype=int32)>

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
    <BaseType with data array(shape=(2, 3), dtype=int64)>
    >>> type(rain.maps)
    <class 'collections.OrderedDict'>
    >>> for item in rain.maps.items():
    ...     print(item)
    ('x', <BaseType with data array(shape=(3,), dtype=int64)>)
    ('y', <BaseType with data array(shape=(2,), dtype=int64)>)

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
import threading
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from functools import reduce
from typing import Optional, Union

import numpy as np
import requests
import requests_cache

from pydap.lib import _quote, decode_np_strings, tree, walk
from pydap.net import GET

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
        self._name = _quote(name)
        self.attributes = attributes or {}
        self.attributes.update(kwargs)

        # Set parent and dataset to keep track of parent references
        self.parent = None
        self.dataset = None
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

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def assign_dataset_recursive(self, dataset=None, path=""):
        if dataset is None:
            dataset = self
            path = ""

        self.dataset = dataset
        self.id = path or "/"  # <-- KEY LINE!

        if isinstance(self, BaseType):
            if not self.parent:
                self.parent = self.dataset
            if type(self._data).__name__ == "BaseProxyDap4" and not hasattr(
                self, "_original_data_args"
            ):
                # Store the original data for later use
                self._original_data_args = (
                    self._data.baseurl,
                    self._data.id,
                    self._data.dtype,
                    self._data.shape,
                    self._data.application,
                    self._data.session,
                    self._data.timeout,
                    self._data.verify,
                    self._data.checksums,
                    self._data.user_charset,
                    self._data.get_kwargs,
                )
        for child in self.children():
            child_path = f"{path}/{child.name}" if path else f"/{child.name}"
            child.assign_dataset_recursive(dataset, child_path)


class BatchPromise:
    def __init__(self):
        self._event = threading.Event()
        self._results = {}

    def set_results(self, results):
        self._results = results
        self._event.set()

    def wait_for_result(self, var_id):
        self._event.wait()
        return self._results[var_id]

    def is_resolved(self):
        return self._event.is_set()


class SelfClearingArray:
    def __init__(self, array):
        self._array = array

    def _consume(self):
        if self._array is None:
            raise RuntimeError("This array has already been cleared.")
        arr = self._array
        self._array = None
        return arr

    def __array__(self, dtype=None):
        arr = self._consume()
        return arr.astype(dtype) if dtype else arr

    def __getitem__(self, key):
        arr = self._consume()
        return arr[key]

    def __len__(self):
        arr = self._consume()
        return len(arr)

    # def __repr__(self):
    #     return f"<SelfClearingArray: {type(self._array)}>"

    def __iter__(self):
        arr = self._consume()
        return iter(arr)


class DapDecodedArray:
    def __init__(self, array: np.ndarray):
        self.array = array

    def __array__(self, dtype=None):
        return np.asarray(self.array, dtype=dtype)

    def __getitem__(self, key):
        return self.array[key]  # Allows [:] to work

    def __len__(self):
        return len(self.array)

    def __repr__(self):
        # Render the actual data
        return repr(np.asarray(self))


class BatchFutureArray:
    def __init__(self, basetype, batch_promise):
        self.basetype = basetype
        self.promise = batch_promise
        self._pending_slice = None

    def __getitem__(self, index):
        self._pending_slice = index
        if self.basetype.dataset and self.basetype.dataset.is_batch_mode():
            self.basetype.dataset.register_for_batch(self.basetype)
        return self

    def _wait(self):
        return self.promise.wait_for_result(self.basetype.id)

    def __array__(self, dtype=None, copy=None):
        result = np.asarray(self._wait())
        if self._pending_slice is not None:
            return np.asarray(result[self._pending_slice])
        if dtype is not None:
            result = result.astype(dtype, copy=False)
        return result


class BaseType(DapType):
    """A thin wrapper over Numpy arrays."""

    def __init__(
        self, name="nameless", data=None, dims=None, attributes=None, **kwargs
    ):
        super(BaseType, self).__init__(name, attributes, **kwargs)
        self.data = data
        self.dims = [] if not dims else list(dims)
        # these are set when not data is present (eg, when parsing a DDS)
        self._dtype = None
        self._shape = ()
        self._itemsize = None
        self._nbytes = None
        self._is_registered_for_batch = False

    # def __repr__(self):
    #     return "<%s with data %s>" % (type(self).__name__, repr(self.data))
    def __repr__(self):
        if isinstance(self._data, SelfClearingArray):
            summary = "<SelfClearingArray (unread)>"
        elif isinstance(self._data, np.ndarray):
            summary = f"array(shape={self._data.shape}, dtype={self._data.dtype})"
        else:
            summary = repr(self._data)
        return f"<{type(self).__name__} with data {summary}>"

    def __hash__(self):
        return hash(self._id)

    @property
    def path(self):
        try:
            return self._data.path
        except AttributeError:
            return None

    @property
    def dtype(self):
        """Property that returns the data dtype."""
        return self._data.dtype

    @property
    def shape(self):
        """Property that returns the data shape."""
        try:
            return self._data.shape
        except AttributeError:
            return self._shape

    @property
    def dimensions(self):
        """Return the name of the axes."""
        warnings.warn(
            "The use of `dimensions` on a `BaseType` array will get "
            "deprecated on a future release. Use `dims` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return tuple(self.dims)

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
        return np.asarray([], dtype=self._data.dtype).itemsize

    @property
    def nbytes(self):
        return self.itemsize * self.size

    def is_remote_dapdata(self):
        return type(self._data).__name__ == "BaseProxyDap4"

    def __copy__(self):
        """A lightweight copy of the variable.

        This will return a new object, with a copy of the attributes,
        dimensions, same name, and a view of the data.

        """
        out = type(self)(self.name, self._data, self.dims[:], self.attributes.copy())
        out.id = self.id
        return out

    # Comparisons are passed to the data.
    def __eq__(self, other):
        return self._data == other

    def __ne__(self, other):
        return self._data != other

    def __ge__(self, other):
        return self._data >= other

    def __le__(self, other):
        return self._data <= other

    def __gt__(self, other):
        return self._data > other

    def __lt__(self, other):
        return self._data < other

    # Implement the sequence and iter protocols.
    def __getitem__(self, index):

        if (
            self.dataset
            and self.dataset.is_batch_mode()
            and self.id
            != "/" + str(self.dataset._session.headers.get("concat_dim", None))
        ):
            # Batch mode: just remember the slice
            out = type(self).__new__(type(self))
            out.__dict__ = self.__dict__.copy()
            out._pending_batch_slice = index
            out._is_registered_for_batch = True
            if hasattr(self, "_original_data_args"):
                from pydap.handlers.dap import BaseProxyDap4

                out._data = BaseProxyDap4(*self._original_data_args)
            else:
                out._data = self._data
            return out

        out = copy.copy(self)
        data = self._get_data_index(index)

        # Check if index is a full slice (e.g., [:], ..., or tuple of all slice(None))
        if (
            index == slice(None)
            or index == Ellipsis
            or (isinstance(index, tuple) and all(i == slice(None) for i in index))
        ):
            try:
                # Unwrap DapDecodedArray or SelfClearingArray
                data = np.asarray(data)
            except Exception:
                pass  # Leave as-is for types that don't support __array__
        out.data = data
        if type(self._data).__name__ == "BaseProxyDap4":
            if self._data.checksums:
                # updates it if defined
                out.attributes["_DAP4_Checksum_CRC32"] = self._data.checksums
            out.attributes.update({"Maps": self.Maps})
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
            return np.vectorize(decode_np_strings, otypes=self._data.dtype.char)(
                self._data[index]
            )
        else:
            return self._get_data()[index]

    def _is_data_loaded(self):
        return isinstance(self._data, (np.ndarray, SelfClearingArray))

    def _get_data(self):
        # Check if this is DAP4 remote data *and* batch mode is enabled
        if (
            self.dataset
            and self.dataset.is_batch_mode()
            and self.is_remote_dapdata()
            and self._is_registered_for_batch
            and not self._is_data_loaded()
        ):
            return self._get_data_batched()
        return self._data

    def _set_data(self, data):
        if isinstance(data, DapDecodedArray):
            self._data = SelfClearingArray(data.array)
        else:
            self._data = data
            if np.isscalar(data):
                # Convert scalar data to numpy scalar, otherwise `.dtype` and
                # `.shape` methods will fail.
                self._data = np.array(data)

    data = property(_get_data, _set_data)

    def _get_data_batched(self):
        """Get data in batch mode."""
        if self.dataset and self._is_registered_for_batch:
            self.dataset.register_for_batch(self)
            self._is_registered_for_batch = True

        future = BatchFutureArray(self, self._batch_promise)

        return future

    def build_ce(self):
        if (
            self.is_remote_dapdata()
            and hasattr(self._data, "ce")
            and self._data.ce
            and not hasattr(self, "_pending_batch_slice")
        ):
            return self._data.ce

        if (
            self.dataset
            and self.dataset.is_batch_mode()
            and hasattr(self, "_pending_batch_slice")
        ):
            self._data = self._data.__getitem__(
                self._pending_batch_slice, build_only=True
            )
            del self._pending_batch_slice
            return self._data.ce
        return None

    def is_dimension_var(self):
        if not self.dataset:
            return False
        parent_path = "/".join(self.id.split("/")[:-1])
        parent = self.dataset
        if parent_path:
            for part in parent_path.split("/"):
                parent = parent[part]
        return self.name in getattr(parent, "dimensions", [])


class StructureType(DapType, Mapping):
    """A dict-like object holding other variables."""

    def __init__(self, name="nameless", attributes=None, **kwargs):
        super(StructureType, self).__init__(name, attributes, **kwargs)

        # allow some keys to be hidden:
        self._visible_keys = []
        self._dict = OrderedDict()
        self._children = OrderedDict()

        self._current_batch_promise = None

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
            child = self._dict[_quote(key)]
            return child
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
        item.parent = self
        self._children[key] = item
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
            if hasattr(var, "dims"):
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
        self.dataset = self  # assign itself as the dataset
        self.parent = self  # no parent
        self._batch_mode = False
        self._batch_timeout = 0.2
        self._batch_registry = set()
        self._batch_timer = None

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
            if isinstance(item, GroupType) and not item.parent:
                item.parent = self
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

    def _start_batch_timer(self):
        if self._current_batch_promise is None:
            self._current_batch_promise = BatchPromise()

        if not self._batch_timer:
            promise_for_this_batch = self._current_batch_promise
            self._batch_timer = threading.Timer(
                self._batch_timeout,
                lambda: self._resolve_batch(promise_for_this_batch),
            )
            self._batch_timer.start()

    def enable_batch_mode(self, timeout=0.25):
        """Turn on batching with specified timeout window in seconds."""
        self._batch_mode = True
        self._batch_timeout = timeout
        self._batch_registry = set()
        self._batch_timer = None
        self._batch_results = {}
        self._dap_url = None
        self._checksums = True
        self._slices = None

    def register_for_batch(self, var, checksums=True):
        """Register a key for batch processing."""
        self._checksums = checksums
        self._batch_registry = {v for v in self._batch_registry if v.id != var.id}
        self._batch_registry.add(var)
        var._is_registered_for_batch = True

        if not self._batch_timer:
            # Start the timer if not already running
            self._start_batch_timer()

        var._batch_promise = self._current_batch_promise

    def _resolve_batch(self, batch_promise):
        from pydap.handlers.dap import UNPACKDAP4DATA

        # print(f"[Batch] Resolving promise: {id(batch_promise)}")
        variables = [
            var
            for var in self._batch_registry
            if getattr(var, "_pending_batch_slice", None) is not None
            and not var._is_data_loaded()
        ]

        if not variables:
            self._batch_timer = None
            return

        constraint_expressions = self.construct_shared_dim_ce(variables)

        base_url = variables[0]._data.baseurl if variables[0]._data else None

        if not constraint_expressions or not base_url:
            self._batch_registry.clear()
            self._batch_timer = None
            return

        # Build the single dap4.ce query parameter
        ce_string = "?dap4.ce=" + constraint_expressions
        _dap_url = base_url + ".dap" + ce_string
        if not self._checksums:
            warnings.warn(
                "Checksums are not optional in the current version, but will "
                "be in the next version of pydap. Setting `checksums=True`",
                stacklevel=2,
            )
        _dap_url += "&dap4.checksum=true"

        # print("dap url:", _dap_url)

        if (
            isinstance(self._session, requests_cache.CachedSession)
            and "debug" not in self._session.cache.cache_name
        ):
            cache_kwargs = {"skip": True}
        else:
            cache_kwargs = {}

        r = GET(
            _dap_url,
            session=self._session,
            get_kwargs={"stream": True},
            cache_kwargs=cache_kwargs,
        )
        parsed_dataset = UNPACKDAP4DATA(r, checksums=True, user_charset="ascii").dataset

        # Collect results
        results_dict = {}
        for var in variables:
            results_dict[var.id] = np.asarray(parsed_dataset[var.id].data[:])
            var._pending_batch_slice = None
            var._is_registered_for_batch = False
            self._batch_registry.discard(var)
            var._batch_promise = None

        # Resolve the promise for all waiting arrays
        batch_promise.set_results(results_dict)

        # Clean up
        self._batch_registry.clear()
        self._batch_timer = None

        return None

    def disable_batch_mode(self):
        """Turn off batching completely."""
        self._batch_mode = False
        self._batch_registry = set()
        self._batch_timer = None
        self._batch_results = {}

    def is_batch_mode(self):
        """Check if batching is currently enabled."""
        return getattr(self, "_batch_mode", False)

    def clear_batch_state(self):
        """Clear any current batch registry and results without disabling mode."""
        self._batch_registry = set()
        self._batch_timer = None
        self._batch_results = {}

    def register_dim_slices(self, var, key=None) -> None:
        """given a BaseType var, and an intended slice key (tuple) that matches its
        dimension, register the slice for future re use.
        Limitations:
            - key is set by user, to match dimension of var. But no checks are done
              to ensure this is correct.
            - slice is stored/registered at dataset level, so any variable with same
              dimension name will share the same slice.
            - slices are not validated, so user must ensure they make sense.
            - Intended only when in batch mode.
        """
        dataset = var.dataset
        dims = [vdim for vdim in var.dims if isinstance(dataset[var.id], BaseType)]
        var._pending_batch_slice = slice(key) if not key else key
        slice_elements = var.build_ce().split(var.name)[-1]
        dim_slices = dict(zip(dims, [sli + "]" for sli in slice_elements.split("]")]))

        # the next check is to see if all dimensions lie within the variable hierarchy
        uniformity_check = len(dims) * [True] == [
            dataset[dims[i]].parent == var.parent for i in range(len(dims))
        ]  # it is True only when all dims a share hierarchy with data
        if not key or not uniformity_check:
            self.clear_dim_slices()
        else:
            # only set the _slices if key is provided
            self._slices = dim_slices

    def clear_dim_slices(self) -> None:
        """Clear any registered dimension slices."""
        self._slices = None

    def construct_shared_dim_ce(self, variables):
        """Constructs the constraint expression for a set of variables
        sharing multiple dimensions slices.
        """
        if not variables:
            return None
        if not self._slices:
            ce_dims = [
                _quote(var.build_ce().split("=")[-1])
                for var in variables
                if var.build_ce() is not None
            ]
            return ";".join(ce_dims)
        else:
            var_names = sorted([var.id for var in variables])
            ce_dims = ";".join(
                [key + "=" + value for key, value in self._slices.items()]
            )
            return ce_dims + ";" + ";".join(var_names)


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
    def dims(self):
        """Return the name of the axes."""
        return list(self.dimensions)

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

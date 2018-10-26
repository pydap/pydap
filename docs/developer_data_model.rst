The DAP data model
------------------

The DAP is a protocol designed for the efficient transmission of scientific data over the internet.
In order to transmit data from the server to a client, both must agree on a way to represent data:
*is it an array of integers?*, *a multi-dimensional grid?*
In order to do this, the specification defines a *data model* that, in theory, should be able to represent any existing dataset.

Metadata
~~~~~~~~

pydap has a series of classes in the ``pydap.model`` module, representing the DAP data model.
The most fundamental data type is called ``BaseType``, and it represents a value or an array of values.
Here an example of creating one of these objects:

.. note:: Prior to pydap 3.2, the name argument was optional for all date types. Since pydap 3.2, it is mandatory.

.. doctest::

    >>> from pydap.model import *
    >>> import numpy as np
    >>> a = BaseType(
    ...         name='a',
    ...         data=np.array([1]),
    ...         attributes={'long_name': 'variable a'})

All pydap types have five attributes in common. The first one is the ``name`` of the variable; in this case, our variable is called "a":

.. doctest::

    >>> a.name
    'a'

Note that there's a difference between the variable name (the local name ``a``) and its attribute ``name``; in this example they are equal, but we could reference our object using any other name:

.. doctest::

    >>> b = a  # b now points to a
    >>> b.name
    'a'

We can use special characters for the variable names; they will be quoted accordingly:

.. doctest::

    >>> c = BaseType(name='long & complicated')
    >>> c.name
    'long%20%26%20complicated'

The second attribute is called ``id``. In the examples we've seen so far, ``id`` and ``name`` are equal:

.. doctest::

    >>> a.name
    'a'
    >>> a.id
    'a'
    >>> c.name
    'long%20%26%20complicated'
    >>> c.id
    'long%20%26%20complicated'

This is because the ``id`` is used to show the position of the variable in a given dataset, and in these
examples the variables do not belong to any datasets. First let's store our variables in a container
object called ``StructureType``. A ``StructureType`` is a special type of ordered dictionary that holds other pydap types:

.. doctest::

    >>> s = StructureType('s')
    >>> s['a'] = a
    >>> s['c'] = c
    Traceback (most recent call last):
        ...
    KeyError: 'Key "c" is different from variable name "long%20%26%20complicated"!'

Note that the variable name has to be used as its key on the ``StructureType``. This can be easily remedied:

.. doctest::

    >>> s[c.name] = c

There is a special derivative of the ``StructureType`` called ``DatasetType``, which represent the dataset.
The difference between the two is that there should be only one ``DatasetType``, but 
it may contain any number of ``StructureType`` objects, which can be deeply nested. Let's create our dataset object:

.. doctest::

    >>> dataset = DatasetType(name='example')
    >>> dataset['s'] = s
    >>> dataset.id
    'example'
    >>> dataset['s'].id
    's'
    >>> dataset['s']['a'].id
    's.a'

Note that for objects on the first level of the dataset, like ``s``, the id is identical to the name.
Deeper objects, like ``a`` which is stored in ``s``, have their id calculated by joining the names of the
variables with a period. One detail is that we can access variables stored in a structure using a "lazy" syntax like this:

.. doctest::

    >>> dataset.s.a.id
    's.a'

The third common attribute that variables share is called ``attributes``, which hold most of its metadata.
This attribute is a dictionary of keys and values, and the values themselves can also be dictionaries.
For our variable ``a`` we have:

.. doctest::

    >>> a.attributes
    {'long_name': 'variable a'}

These attributes can be accessed lazily directly from the variable:

.. doctest::

    >>> a.long_name
    'variable a'

But if you want to create a new attribute you'll have to insert it directly into ``attributes``:

.. doctest::

    >>> a.history = 'Created by me'
    >>> a.attributes
    {'long_name': 'variable a'}
    >>> a.attributes['history'] = 'Created by me'
    >>> sorted(a.attributes.items())
    [('history', 'Created by me'),
    ('long_name', 'variable a')]

It's always better to use the correct syntax instead of the lazy one when writing code.
Use the lazy syntax only when introspecting a dataset on the Python interpreter, to save a few keystrokes.

The fourth attribute is called ``data``, and it holds a representation of the actual data.
We'll take a detailed look of this attribute in the next subsection.

.. note:: Prior to pydap 3.2, all variables had also an attribute called ``_nesting_level``.
          This attribute had value 1 if the variable was inside a ``SequenceType`` object,
          0 if it's outside, and >1 if it's inside a nested sequence.
          Since pydap 3.2, the ``_nesting_level`` has been deprecated and there is no
          intrinsic way of finding the where in a deep object a variable is located.

Data
~~~~

As we saw on the last subsection, all pydap objects have a ``data`` attribute that holds a representation of the variable data.
This representation will vary depending on the variable type. 

``BaseType``
************

For the simple ``BaseType`` objects the ``data`` attributes is usually a Numpy array, 
though we can also use a Numpy scalar or Python number:

.. doctest::

    >>> a = BaseType(name='a', data=np.array(1))
    >>> a.data
    array(1)

    >>> b = BaseType(name='b', data=np.arange(4))
    >>> b.data
    array([0, 1, 2, 3])

Note that starting from pydap 3.2 the datatype is inferred from the input data:

.. doctest::

    >>> a.dtype
    dtype('int64')
    >>> b.dtype
    dtype('int64')

When you *slice* a ``BaseType`` array, the slice is simply passed onto the data attribute. So we may have:

.. doctest::

    >>> b[-1]
    <BaseType with data array(3)>
    >>> b[-1].data
    array(3)
    >>> b[:2]
    <BaseType with data array([0, 1])>
    >>> b[:2].data
    array([0, 1])
    
You can think of a ``BaseType`` object as a thin layer around Numpy arrays, 
until you realize that the ``data`` attribute can be *any* object implementing the array interface! 
This is how the DAP client works -- instead of assigning an array with data directly to the attribute, 
we assign a special object which behaves like an array and acts as a *proxy* to a remote dataset. 

Here's an example:

.. doctest::

    >>> from pydap.handlers.dap import BaseProxy
    >>> pseudo_array = BaseProxy(
    ...         'http://test.opendap.org/dap/data/nc/coads_climatology.nc',
    ...         'SST.SST',
    ...         np.float64,
    ...         (12, 90, 180))
    >>> print(pseudo_array[0, 10:14, 10:14])  # download the corresponding data #doctest: +SKIP
    [[[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
      [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
      [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
      [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]]
    
In the example above, the data is only downloaded in the last line, when the pseudo array is sliced. The object will construct the appropriate DAP URL, request the data, unpack it and return a Numpy array. 

``StructureType``
*****************

A ``StructureType`` holds no data; instead, its ``data`` attribute is a property that collects data from the children variables:

.. doctest::

    >>> s = StructureType(name='s')
    >>> s[a.name] = a
    >>> s[b.name] = b
    >>> a.data
    array(1)
    >>> b.data
    array([0, 1, 2, 3])
    >>> print(s.data)
    [array(1), array([0, 1, 2, 3])]

The opposite is also true; it's possible to specify the structure data and have it propagated to the children:

.. doctest::

    >>> s.data = (1, 2)
    >>> print(s.a.data)
    1
    >>> print(s.b.data)
    2

The same is true for objects of ``DatasetType``, since the dataset is simply the root structure.

``SequenceType``
****************

A ``SequenceType`` object is a special kind of ``StructureType`` holding sequential data. 
Here's an example of a sequence holding the variables ``a`` and ``c`` that we created before:

.. doctest::

    >>> s = SequenceType(name='s')
    >>> s[a.name] = a
    >>> s[c.name] = c

Let's add some data to our sequence. This can be done by setting a structured numpy array to the data attribute:

.. doctest::

    >>> print(s)
    <SequenceType with children 'a', 'long%20%26%20complicated'>
    >>> test_data = np.array([
    ... (1, 10),
    ... (2, 20),
    ... (3, 30)],
    ... dtype=np.dtype([
    ... ('a', np.int32), ('long%20%26%20complicated', np.int16)]))
    >>> s.data = test_data
    >>> print(s.data)
    [(1, 10) (2, 20) (3, 30)]

Note that the data for the sequence is an aggregation of the children data, similar to Python's ``zip()`` builtin. 
This will be more complicated when encountering nested sequences, but for flat sequences they behave the same.

We can also iterate over the ``SequenceType``. In this case, it will return a series of tuples with the data: 

.. doctest::

    >>> for record in s.iterdata():
    ...     print(record)
    (1, 10)
    (2, 20)
    (3, 30)

Prior to pydap 3.2.2, this approach was not possible and one had to iterate directly over ``SequenceType``: 

.. doctest::

    >>> for record in s:
    ...     print(record)
    (1, 10)
    (2, 20)
    (3, 30)

This approach will be deprecated in pydap 3.4.

The ``SequenceType`` behaves pretty much like `record arrays <http://docs.scipy.org/doc/numpy/user/basics.rec.html>`_ from 
Numpy, since we can reference them by column (``s['a']``) or by index:

.. doctest::

    >>> s[1].data
    (2, 20)
    >>> s[ s.a < 3 ].data
    array([(1, 10), (2, 20)], 
          dtype=[('a', '<i4'), ('long%20%26%20complicated', '<i2')])

Note that these objects are also ``SequenceType`` themselves. The basic rules when working with sequence data are: 

1. When a ``SequenceType`` is sliced with a string the corresponding children is returned. For example: ``s['a']`` will return child ``a``;
2. When a ``SequenceType`` is iterated over (using ``.iterdata()`` after pydap 3.2.2) it will return a series of tuples, each one containing the data for a record;
3. When a ``SequenceType`` is sliced with an integer, a comparison or a ``slice()`` a new ``SequenceType`` will be returned;
4. When a ``SequenceType`` is sliced with a tuple of strings a new ``SequenceType`` will be returned, containing only the children defined in the tuple in the new order.
   For example, ``s[('c', 'a')]`` will return a sequence ``s`` with the children ``c`` and ``a``, in that order.

Note that except for rule 4 ``SequenceType`` mimics the behavior of Numpy record arrays.

Now imagine that we want to add to a ``SequenceType`` data pulled from a relational database. 
The easy way would be to fetch the data in the correct column order, and insert it into the sequence. 
But what if we don't want to store the data in memory, and instead we would like to stream it directly from the database? 
In this case we can create an object that behaves like a record array, similar to the proxy object that implements the array interface. 
pydap defines a "protocol" called ``IterData``, which is simply any object that:

1. Returns data when iterated over.
2. Returns a new ``IterData`` when sliced such that:

   a) if the slice is a string the new ``IterData`` contains data only for that children;
   b) if the slice is a tuple of strings the object contains only those children, in that order;
   c) if the slice is an integer, a ``slice()`` or a comparison, the data is filter accordingly.

The base implementation works by wrapping data from a basic Numpy array. 
And here is an example of how we would use it:

.. doctest::

    >>> from pydap.handlers.lib import IterData
    >>> s.data = IterData(np.array([(1, 2), (10, 20)]), s)
    >>> print(s)
    <SequenceType with children 'a', 'long%20%26%20complicated'>
    >>> s2 = s.data[ s['a'] > 1 ]
    >>> print(s2)
    <IterData to stream array([[ 1,  2],
           [10, 20]])>
    >>> for record in s2.iterdata():
    ...     print(record)
    (10, 20)

One can also iterate directly over the ``IterData`` object to obtain the data:

.. doctest::

    >>> for record in s2:
    ...     print(record)
    (10, 20)

This approach will not be deprecated in pydap 3.4.

There are many implementations of classes derived from ``IterData``: ``pydap.handlers.dap.SequenceProxy`` is a proxy to 
sequential data on Opendap servers, ``pydap.handlers.csv.CSVProxy`` wraps a CSV file, 
and ``pydap.handlers.sql.SQLProxy`` works as a stream to a relational database.

``GridType``
************

A ``GridType`` is a special kind of object that behaves like an array and a ``StructureType``. 
The class is derived from ``StructureType``; the major difference is that the first defined variable is a multidimensional array, 
while subsequent children are vector maps that define the axes of the array. This way, the ``data`` attribute on a ``GridType`` 
returns the data of all its children: the n-dimensional array followed by *n* maps.

Here is a simple example:

.. doctest::

    >>> g = GridType(name='g')
    >>> data = np.arange(6)
    >>> data.shape = (2, 3)
    >>> g['a'] = BaseType(name='a', data=data, shape=data.shape, type=np.int32, dimensions=('x', 'y'))
    >>> g['x'] = BaseType(name='x', data=np.arange(2), shape=(2,), type=np.int32)
    >>> g['y'] = BaseType(name='y', data=np.arange(3), shape=(3,), type=np.int32)
    >>> g.data
    [array([[0, 1, 2],
               [3, 4, 5]]), array([0, 1]), array([0, 1, 2])]
 
Grid behave like arrays in that they can be sliced. When this happens, a new ``GridType`` is returned with the proper data and axes:

.. doctest::

    >>> print(g)
    <GridType with array 'a' and maps 'x', 'y'>
    >>> print(g[0])
    <GridType with array 'a' and maps 'x', 'y'>
    >>> print(g[0].data)
    [array([0, 1, 2]), array(0), array([0, 1, 2])]

It is possible to disable this feature (some older servers might not handle it nicely):

.. doctest::

    >>> g = GridType(name='g')
    >>> g.set_output_grid(False)
    >>> data = np.arange(6)
    >>> data.shape = (2, 3)
    >>> g['a'] = BaseType(name='a', data=data, shape=data.shape, type=np.int32, dimensions=('x', 'y'))
    >>> g['x'] = BaseType(name='x', data=np.arange(2), shape=(2,), type=np.int32)
    >>> g['y'] = BaseType(name='y', data=np.arange(3), shape=(3,), type=np.int32)
    >>> g.data
    [array([[0, 1, 2],
           [3, 4, 5]]), array([0, 1]), array([0, 1, 2])]
    >>> print(g)
    <GridType with array 'a' and maps 'x', 'y'>
    >>> print(g[0])
    <BaseType with data array([0, 1, 2])>
    >>> print(g[0].name)
    a
    >>> print(g[0].data)
    [0  1  2]

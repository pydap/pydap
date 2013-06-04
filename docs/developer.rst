Developer documentation
=======================

This documentation is intended for other developers that would like to contribute with the development of Pydap, or extend it in new ways. It assumes that you have a basic knowledge of Python and HTTP, and understands how data is stored in different formats. It also assumes some familiarity with the `Data Access Protocol <http://opendap.org/>`_, though a lot of its inner workings will be explained in detail here.

The DAP data model
------------------

The DAP is a protocol designed for the efficient transmission of scientific data over the internet. In order to transmit data from the server to a client, both must agree on a way to represent data: *is it an array of integers?*, *a multi-dimensional grid?* In order to do this, the specification defines a *data model* that, in theory, should be able to represent any existing dataset.

Metadata
~~~~~~~~

Pydap has a series of classes in the ``pydap.model`` module, representing the DAP data model. The most fundamental data type is called ``BaseType``, and it represents a value or an array of values. Here an example of creating one of these objects:

.. doctest::

    >>> from pydap.model import *
    >>> a = BaseType(
    ...         name='a',
    ...         data=1,
    ...         shape=(),
    ...         dimensions=(),
    ...         type=Int32,
    ...         attributes={'long_name': 'variable a'})

All Pydap types have five attributes in common. The first one is the ``name`` of the variable; in this case, our variable is called "a":

.. doctest::

    >>> print a.name
    a

Note that there's a difference between the variable name (the local name ``a``) and its attribute ``name``; in this example they are equal, but we could reference our object using any other name:

.. doctest::

    >>> b = a  # b now points to a
    >>> print b.name
    a

We can use special characters for the variable names; they will be quoted accordingly:

.. doctest::

    >>> c = BaseType(name='long & complicated')
    >>> print c.name
    long%20%26%20complicated

The second attribute is called ``id``. In the examples we've seen so far, ``id`` and ``name`` are equal:

.. doctest::

    >>> print a.name, a.id
    a a
    >>> print c.name, c.id
    long%20%26%20complicated long%20%26%20complicated

This is because the id is used to show the position of the variable in a given dataset, and in these examples the variables do not belong to any datasets. First let's store our variables in a container object called ``StructureType``. A ``StructureType`` is a special type of ordered dictionary that holds other Pydap types:

.. doctest::

    >>> s = StructureType(name='s')
    >>> s['a'] = a
    >>> s['c'] = c
    Traceback (most recent call last):
        ...
    KeyError: 'Key "c" is different from variable name "long%20%26%20complicated"!'

Note that the variable name has to be used as its key on the ``StructureType``. This can be easily remedied:

.. doctest::

    >>> s[c.name] = c

There is a special derivative of the ``StructureType`` called ``DatasetType``, which represent the dataset. The difference between the two is that there should be only one ``DatasetType``, but it may contain any number of ``StructureType`` objects, which can be deeply nested. Let's create our dataset object:

.. doctest::

    >>> dataset = DatasetType(name='example')
    >>> dataset['s'] = s
    >>> print dataset.id
    example
    >>> print dataset['s'].id
    s
    >>> print dataset['s']['a'].id
    s.a

Note that for objects on the first level of the dataset, like ``s``, the id is identical to the name. Deeper objects, like ``a`` which is stored in ``s``, have their id calculated by joining the names of the variables with a period. One detail is that we can access variables stored in a structure using a "lazy" syntax like this:

.. doctest::

    >>> print dataset.s.a.id
    s.a

The third common attribute that variables share is called ``attributes``, which hold most of its metadata. This attribute is a dictionary of keys and values, and the values themselves can also be dictionaries. For our variable ``a`` we have:

.. doctest::

    >>> print a.attributes
    {'long_name': 'variable a'}

These attributes can be accessed lazily directly from the variable:

.. doctest::

    >>> print a.long_name
    variable a

But if you want to create a new attribute you'll have to insert it directly into ``attributes``:

.. doctest::

    >>> a.history = 'Created by me'
    >>> print a.attributes
    {'long_name': 'variable a'}
    >>> a.attributes['history'] = 'Created by me'
    >>> print a.attributes
    {'long_name': 'variable a', 'history': 'Created by me'}

It's always better to use the correct syntax instead of the lazy one when writing code. Use the lazy syntax only when introspecting a dataset on the Python interpreter, to save a few keystrokes.

The fourth attribute is called ``data``, and it holds a representation of the actual data. We'll take a detailed look of this attribute in the next subsection.

Finally, all variables have also an attribute called ``_nesting_level``. This attribute has value 1 if the variable is inside a ``SequenceType`` object, 0 if it's outside, and >1 if it's inside a nested sequence. This will become clearer later when we talk about sequential data.

Data
~~~~

As we saw on the last subsection, all Pydap objects have a ``data`` attribute that holds a representation of the variable data. This representation will vary depending on the variable type. 

``BaseType``
************

For the simple ``BaseType`` objects the ``data`` attributes is usually a Numpy array, though we can also use a Numpy scalar or Python number:

.. doctest::

    >>> a = BaseType(name='a', data=1)
    >>> print a.data
    1

    >>> import numpy
    >>> b = BaseType(name='b', data=numpy.arange(4), shape=(4,))
    >>> print b.data
    [0 1 2 3]

Note that the default type for variables is ``Int32``:

.. doctest::

    >>> print a.type, b.type
    <class 'pydap.model.Int32'> <class 'pydap.model.Int32'>

When you *slice* a ``BaseType`` array, the slice is simply passed onto the data attribute. So we may have:

.. doctest::

    >>> print b[-1]
    3
    >>> print b[:2]
    [0 1]
    >>> print a[0]
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pydap/model.py", line 188, in __getitem__
    TypeError: 'int' object is unsubscriptable
    
You can think of a ``BaseType`` object as a thin layer around Numpy arrays, until you realize that the ``data`` attribute can be *any* object implementing the array interface! This is how the DAP client works -- instead of assigning an array with data directly to the attribute, we assign a special object which behaves like an array and acts as a *proxy* to a remote dataset. 

Here's an example:

.. doctest::

    >>> from pydap.proxy import ArrayProxy
    >>> pseudo_array = ArrayProxy(
    ...         'SST.SST',
    ...         'http://test.opendap.org/dap/data/nc/coads_climatology.nc',
    ...         (12, 90, 180))
    >>> print pseudo_array[0, 10:14, 10:14]  # download the corresponding data
    [[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
     [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
     [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
     [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]
    
In the example above, the data is only downloaded in the last line, when the pseudo array is sliced. The object will construct the appropriate DAP URL, request the data, unpack it and return a Numpy array. 

``StructureType``
*****************

A ``StructureType`` holds no data; instead, its ``data`` attribute is a property that collects data from the children variables:

.. doctest::

    >>> s = StructureType(name='s')
    >>> s[a.name] = a
    >>> s[b.name] = b
    >>> print a.data
    1
    >>> print b.data
    [0 1 2 3]
    >>> print s.data
    (1, array([0, 1, 2, 3]))

The opposite is also true; it's possible to specify the structure data and have it propagated to the children:

.. doctest::

    >>> s.data = (1, 2)
    >>> print s.a.data
    1
    >>> print s.b.data
    2

The same is true for objects of ``DatasetType``, since the dataset is simply the root structure.

``SequenceType``
****************

A ``SequenceType`` object is a special kind of ``StructureType`` holding sequential data. Here's an example of a sequence holding the variables ``a`` and ``c`` that we created before:

.. doctest::

    >>> s = SequenceType(name='s')
    >>> s[a.name] = a
    >>> s[c.name] = c

Let's add some data to our sequence. This can be done in several ways, the easiest of which is adding the data to its children:

.. doctest::

    >>> s.a.data = [1,2,3]
    >>> s.b.data = [10,20,30]
    >>> s.data
    array([[1, 10],
           [2, 20],
           [3, 30]], dtype=object)

Note that the data for the sequence is an aggregation of the children data, similar to Python's ``zip()`` builtin. This will be more complicated when encountering nested sequences, but for flat sequences they behave the same.

We can also iterate over the ``SequenceType``. In this case, it will return a series of ``StructureType`` objects, each one containing data for the children variables. The ``StructureType`` will have the same children as the sequence, with each one containing data for a single record:

.. doctest::

    >>> for record in s:
    ...     print type(record), record.keys(), record.data
    <class 'pydap.model.StructureType'> ['a', 'b'] (1, 10)
    <class 'pydap.model.StructureType'> ['a', 'b'] (2, 20)
    <class 'pydap.model.StructureType'> ['a', 'b'] (3, 30)

The second way of defining the data of a ``SequenceType`` is by setting if directly to the object:

.. doctest::

    >>> s.data = [(4,40), (5,50)]
    >>> s['a'].data
    array([4, 5], dtype=object)

Like in the ``StructureType``, the data is propagated to its children. Note that in the two cases the data was defined using Python lists, being automatically converted to Numpy arrays. In fact, the ``SequenceType`` behaves pretty much like `record arrays <http://docs.scipy.org/doc/numpy/user/basics.rec.html>`_ from Numpy, since we can reference them by column (``s['a']``) or by index:

.. doctest::

    >>> s[1].data
    array([[5, 50]], dtype=object)
    >>> s[ s.a < 5 ].data
    array([[4, 40]], dtype=object)

Note that these objects are also ``SequenceType`` themselves. The basic rules when working with sequence data are: 

1. When a ``SequenceType`` is sliced with a string the corresponding children is returned. For example: ``s['a']`` will return child ``a``;
2. When a ``SequenceType`` is iterated over it will return a series of ``StructureType`` objects, each one containing the data for a record;
3. When a ``SequenceType`` is sliced with an integer, a comparison or a ``slice()`` a new ``SequenceType`` will be returned;
4. When a ``SequenceType`` is sliced with a tuple of strings a new ``SequenceType`` will be returned, containing only the children defined in the tuple in the new order. For example, ``s[('c', 'a')]`` will return a sequence ``s`` with the children ``c`` and ``a``, in that order.

Note that except for rule 4 ``SequenceType`` mimics the behavior of Numpy record arrays.

Now imagine that we want to add to a ``SequenceType`` data pulled from a relational database. The easy way would be to fetch the data in the correct column order, and insert it into the sequence. But what if we don't want to store the data in memory, and instead we would like to stream it directly from the database? In this case we can create an object that behaves like a record array, similar to the proxy object that implements the array interface. Pydap defines a "protocol" called ``SequenceData``, which is simply any object that:

1. Returns data when iterated over.
2. Returns a new ``SequenceData`` when sliced such that:

   a) if the slice is a string the new ``SequenceData`` contains data only for that children;
   b) if the slice is a tuple of strings the object contains only those children, in that order;
   c) if the slice is an integer, a ``slice()`` or a comparison, the data is filter accordingly.

The base implementation works by wrapping data from a basic Numpy array:

.. code-block:: python

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

And here is an example of how we would use it:

.. doctest::

    >>> from pydap.model import SequenceData
    >>> s.data = SequenceData(numpy.array([(1,2), (10,20)]), ('a', 'b'))
    >>> s2 = s.data[ s['a'] > 1 ]
    >>> s2.data
    array([[10, 20]])

There are many implementations of classes derived from ``SequenceData``: ``pydap.proxy.SequenceProxy`` is a proxy to sequential data on Opendap servers, ``pydap.handlers.csv.CSVProxy`` wraps a CSV file, and ``pydap.handlers.sql.SQLProxy`` works as a stream to a relational database.

``GridType``
************

A ``GridType`` is a special kind of object that behaves like an array and a ``StructureType``. The class is derived from ``StructureType``; the major difference is that the first defined variable is a multidimensional array, while subsequent children are vector maps that define the axes of the array. This way, the ``data`` attribute on a ``GridType`` returns the data of all its children: the n-dimensional array followed by *n* maps.

Here is a simple example:

.. doctest::

    >>> g = GridType(name='g')
    >>> data = numpy.arange(6.)
    >>> data.shape = (2, 3)
    >>> g['a'] = BaseType(name='a', data=data, shape=data.shape, type=Float32, dimensions=('x', 'y'))
    >>> g['x'] = BaseType(name='x', data=numpy.arange(2.), shape=(2,), type=Float64)
    >>> g['y'] = BaseType(name='y', data=numpy.arange(3.), shape=(3,), type=Float64)
    >>> g.data
    (array([[ 0.,  1.,  2.],
           [ 3.,  4.,  5.]]), array([ 0.,  1.]), array([ 0.,  1.,  2.]))
 
Grid behave like arrays in that they can be sliced. When this happens, a new ``GridType`` is returned with the proper data and axes:

.. doctest::

    >>> print g
    <class 'pydap.model.GridType'>
        with data
    [[ 0.  1.  2.]
     [ 3.  4.  5.]]
        and axes
    [ 0.  1.]
    [ 0.  1.  2.]
    >>> print g[0]
    <class 'pydap.model.GridType'>
        with data
    [[ 0.  1.  2.]]
        and axes
    [ 0.]
    [ 0.  1.  2.]

Handlers
--------

Now that we saw the Pydap data model we can understand handlers: handlers are simply classes that convert data into the Pydap data model. The NetCDF handler, for example, reads a NetCDF file and builds a ``DatasetType`` object. The SQL handler reads a file describing the variables and maps them to a given table on a relational database. Pydap uses `entry points <http://peak.telecommunity.com/DevCenter/setuptools#dynamic-discovery-of-services-and-plugins>`_ in order to find handlers that are installed in the system. This means that handlers can be developed and installed separately from Pydap. Handlers are mapped to files by a regular expression that usually matches the extension of the file.

Here is the minimal configuration for a handler that serves ``.npz`` files from Numpy:

.. code-block:: python

    import os
    import re

    import numpy

    from pydap.model import *
    from pydap.handlers.lib import BaseHandler
    from pydap.handlers.helper import constrain

    class Handler(BaseHandler):
        
        extensions = re.compile(r'^.*\.npz$', re.IGNORECASE)

        def __init__(self, filepath):
            self.filename = os.path.split(filepath)[1]
            self.f = numpy.load(filepath)

        def parse_constraints(self, environ):
            dataset = DatasetType(name=self.filename)

            for name in self.f.files:
                data = self.f[name][:]
                dataset[name] = BaseType(name=name, data=data, shape=data.shape, type=data.dtype.char)

            return constrain(dataset, environ.get('QUERY_STRING', ''))

    if __name__ == '__main__':
        import sys
        from paste.httpserver import serve

        application = Handler(sys.argv[1])
        serve(application, port=8001)

So let's go over the code. Our handler has a single class called ``Handler`` that should be configured as an entry point in the ``setup.py`` file for the handler:

.. code-block:: ini

    [pydap.handler]
    npz = path.to.my.handler:Handler

Here the name of our handler ("npz") can be anything, as long as it points to the correct class. In order for Pydap to be able to find the handler, it must be installed in the system with either a ``python setup.py install`` or, even better, ``python setup.py develop``. 

The class-level attribute ``extensions`` defines a regular expression that matches the files supported by the handler. In this case, the handler will match all files ending with the ``.npz`` extension.

When the handler is instantiated the complete filepath to the data file is passed in ``__init__``. With this information, our handler extracts the filename of the data file and opens it using the ``load()`` function from Numpy. The handler will be initialized for every request, and immediately its ``parse_constraints`` method is called.

The ``parse_constraints`` method is responsible for building a dataset object based on information for the request available on ``environ``. In this simple handler we simply built a ``DatasetType`` object with the entirety of our dataset, i.e., we added *all data from all variables* that were available on the ``.npz`` file. Some requests will ask for only a few variables, and only a subset of their data. The easy way parsing the request is simply passing the complete dataset together with the ``QUERY_STRING`` to the ``contrain()`` function:

.. code-block:: python

    return constrain(dataset, environ.get('QUERY_STRING', ''))

This will take care of filtering our dataset according to the request, although it may not be very efficient. For this reason, handlers usually implement their own parsing of the Opendap constraint expression. The SQL handler, for example, will translate the query string into an SQL expression that filters the data on the database, and not on Python.

Finally, note that the handler is a WSGI application: we can initialize it with a filepath and pass it to a WSGI server. This enables us to quickly test the handler, by checking the different responses at ``http://localhost:8001/.dds``, for example. It also means that it is very easy to dinamically serve datasets by plugging them to a route dispatcher.
    

Responses
---------

If handlers are responsible for converting data into the Pydap data model, responses to the opposite: the convert from the data model to different representations. The Opendap specification defines a series of standard responses, that allow clients to introspect a dataset by downloading metadata, and later download data for the subset of interest. These standard responses are the DDS (Dataset Descriptor Structure), the DAS (Dataset Attribute Structure) and the DODS response.

Apart from these, there are additional non-standard responses that add functionality to the server. The ASCII response, for example, formats the data as ASCII for quick visualization on the browser; the HTML response builds a form from which the user can select a subset of the data.

Here is an example of a minimal Pydap response that returns the attributes of the dataset as JSON:

.. code-block:: python

    from simplejson import dumps

    from pydap.responses.lib import BaseResponse
    from pydap.lib import walk

    class JSONResponse(BaseResponse):
        def __init__(self, dataset):
            BaseResponse.__init__(self, dataset)
            self.headers.append(('Content-type', 'application/json'))

        @staticmethod
        def serialize(dataset):
            attributes = {}
            for child in walk(dataset):
                attributes[child.id] = child.attributes

            if hasattr(dataset, 'close'):
                dataset.close()

            return [dumps(attributes)]

This response is mapped to a specific extension defined in its entry point:

.. code-block:: ini

    [pydap.response]
    json = path.to.my.response:JSONResponse

In this example the response will be called when the ``.json`` extension is appended to any dataset.

The most important method in the response is the ``serialize`` method, which is responsible for serializing the dataset into the external format. The method should be a generator or return a list of strings, like in this example. Note that the method is responsible for calling ``dataset.close()``, if available, since some handlers use this for closing file handlers or database connections.

One important thing about the responses is that, like handlers, they are also WSGI applications. WSGI applications should return an iterable when called; usually this is a list of strings corresponding to the output from the application. The ``BaseResponse`` application, however, returns a special iterable that contains both the ``DatasetType`` object and its serialization function. This means that WSGI middleware that manipulate the response have direct access to the dataset, avoiding the need for deserialization/serialization of the dataset in order to change it.

Here is a simple example of a middleware that adds an attribute to a given dataset:

.. code-block:: python

    from webob import Request

    from pydap.model import *
    from pydap.handlers.lib import BaseHandler
    
    class AttributeMiddleware(object):

        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            # say that we want the parsed response
            environ['x-wsgiorg.want_parsed_response'] = True

            # call the app with the original request and get the response
            req = Request(environ)
            res = req.get_response(self.app)

            # get the dataset from the response and set attribute
            dataset = res.app_iter.x_wsgiorg_parsed_response(DatasetType)
            dataset.attributes['foo'] = 'bar'

            # return original response
            response = BaseHandler.response_map[ environ['pydap.response'] ]
            responder = response(dataset)
            return responder(environ, start_response)

The code should actually do more bookkeeping, like checking if the dataset can be retrieved from the response or updating the ``Content-Length`` header, but I wanted to keep it simple. Pydap comes with a WSGI middleware for handling server-side functions (``pydap.wsgi.ssf``) that makes heavy use of this feature. It works by removing function calls from the request, fetching the dataset from the modified request, applying the function calls and returning a new dataset.

Templating
----------

Pydap uses an `experimental backend-agnostic templating API <http://svn.pythonpaste.org/Paste/TemplateProposal/>`_ for rendering HTML and XML by responses. Since the API is neutral Pydap can use any templating engine, like `Mako <http://www.makotemplates.org/>`_ or `Genshi <http://genshi.edgewall.org/>`_, and templates can be loaded from disk, memory or a database. The server that comes with Pydap, for example, defines a ``renderer`` object that loads Genshi templates from a directory ``templatedir``:

.. code-block:: python

    from pydap.util.template import FileLoader, GenshiRenderer

    class FileServer(object):
        def __init__(self, templatedir, ...):
            loader = FileLoader(templatedir)
            self.renderer = GenshiRenderer(options={}, loader=loader)
            ...

        def __call__(self, environ, start_response):
            environ.setdefault('pydap.renderer', self.renderer)
            ...

And here is how the HTML response uses the renderer: the response requests a template called ``html.html``, that is loaded from the directory by the ``FileLoader`` object, and renders it by passing the context:

.. code-block:: python

    def serialize(dataset):
        ...
        renderer = environ['pydap.renderer']
        template = renderer.loader('html.html')
        output = renderer.render(template, context, output_format='text/html')
        return [output]

(This is acutally a simplification; if you look at the code you'll notice that there's also code to fallback to a default renderer if one is not found in the ``environ``.)

Handlers
--------

Now that we saw the pydap data model we can understand handlers: handlers are simply classes that convert data into the pydap data model. The NetCDF handler, for example, reads a NetCDF file and builds a ``DatasetType`` object. The SQL handler reads a file describing the variables and maps them to a given table on a relational database. pydap uses `entry points <http://peak.telecommunity.com/DevCenter/setuptools#dynamic-discovery-of-services-and-plugins>`_ in order to find handlers that are installed in the system. This means that handlers can be developed and installed separately from pydap. Handlers are mapped to files by a regular expression that usually matches the extension of the file.

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

Here the name of our handler ("npz") can be anything, as long as it points to the correct class. In order for pydap to be able to find the handler, it must be installed in the system with either a ``python setup.py install`` or, even better, ``python setup.py develop``. 

The class-level attribute ``extensions`` defines a regular expression that matches the files supported by the handler. In this case, the handler will match all files ending with the ``.npz`` extension.

When the handler is instantiated the complete filepath to the data file is passed in ``__init__``. With this information, our handler extracts the filename of the data file and opens it using the ``load()`` function from Numpy. The handler will be initialized for every request, and immediately its ``parse_constraints`` method is called.

The ``parse_constraints`` method is responsible for building a dataset object based on information for the request available on ``environ``. In this simple handler we simply built a ``DatasetType`` object with the entirety of our dataset, i.e., we added *all data from all variables* that were available on the ``.npz`` file. Some requests will ask for only a few variables, and only a subset of their data. The easy way parsing the request is simply passing the complete dataset together with the ``QUERY_STRING`` to the ``contrain()`` function:

.. code-block:: python

    return constrain(dataset, environ.get('QUERY_STRING', ''))

This will take care of filtering our dataset according to the request, although it may not be very efficient. For this reason, handlers usually implement their own parsing of the Opendap constraint expression. The SQL handler, for example, will translate the query string into an SQL expression that filters the data on the database, and not on Python.

Finally, note that the handler is a WSGI application: we can initialize it with a filepath and pass it to a WSGI server. This enables us to quickly test the handler, by checking the different responses at ``http://localhost:8001/.dds``, for example. It also means that it is very easy to dinamically serve datasets by plugging them to a route dispatcher.

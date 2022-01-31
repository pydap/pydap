.. pydap documentation master file, created by sphinx-quickstart on Tue May  6 23:41:51 2008.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pydap
=====

pydap is a pure `Python <http://python.org/>`_ library implementing the `Data Access Protocol <http://opendap.org/>`_, also known as **DODS** or **OPeNDAP**. You can use pydap as a `client <client.html>`_ to access hundreds of scientific datasets in a transparent and efficient way through the internet; or as a server to easily `distribute <server.html>`_ your data from a `variety of formats <handlers.html>`_.

Quickstart
----------

You can install the latest version (|release|) using `pip <http://pypi.python.org/pypi/pip>`_. After `installing pip <http://www.pip-installer.org/en/latest/installing.html>`_ you can install pydap with this command:

.. code-block:: bash

    $ pip install pydap

This will install pydap together with all the required dependencies. You can now open any remotely served dataset, and pydap will download the accessed data on-the-fly as needed:

.. doctest:: 

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> var = dataset['SST']
    >>> var.shape
    (12, 90, 180)
    >>> var.dtype
    dtype('>f4')
    >>> data = var[0,10:14,10:14]  # this will download data from the server
    >>> data
    <GridType with array 'SST' and maps 'TIME', 'COADSY', 'COADSX'>
    >>> print(data.data)
    [array([[[ -1.26285708e+00,  -9.99999979e+33,  -9.99999979e+33,
              -9.99999979e+33],
            [ -7.69166648e-01,  -7.79999971e-01,  -6.75454497e-01,
              -5.95714271e-01],
            [  1.28333330e-01,  -5.00000156e-02,  -6.36363626e-02,
              -1.41666666e-01],
            [  6.38000011e-01,   8.95384610e-01,   7.21666634e-01,
               8.10000002e-01]]], dtype=float32), array([ 366.]), array([-69., -67., -65., -63.]), array([ 41.,  43.,  45.,  47.])]

For more information, please check the documentation on `using pydap as a client <client.html>`_. pydap also comes with a simple server, implemented as a `WSGI <http://wsgi.org/>`_ application. To use it, you first need to install pydap with the server extras dependencies. If you want to serve `netCDF <http://www.unidata.ucar.edu/software/netcdf/>`_ files, install pydap with the ``handlers.netcdf`` extra:

.. code-block:: bash

    $ pip install pydap[server,handlers.netcdf]

More `handlers <handlers.html>`_ for different formats are available, if necessary. To run a simple standalone server just issue the command:

.. code-block:: bash

    $ pydap --data ./myserver/data/ --port 8001

This will start a standalone server running on http://localhost:8001/, serving netCDF files from ``./myserver/data/``, similar to the test server at http://test.pydap.org/. Since the server uses the `WSGI <http://wsgi.org/>`_ standard, it can easily be run behind Apache. The `server documentation <server.html>`_ has more information on how to better deploy pydap.

Help
----

If you need any help with pydap, please feel free to send an email to the `mailing list <http://groups.google.com/group/pydap/>`_.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   client
   server
   handlers
   responses
   developer
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


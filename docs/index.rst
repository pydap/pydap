.. pydap documentation master file, created by sphinx-quickstart on Tue May  6 23:41:51 2008.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pydap
=====

Pydap is a pure `Python <http://python.org/>`_ library implementing the `Data Access Protocol <http://opendap.org/>`_, also known as **DODS** or **OPeNDAP**. You can use Pydap as a `client <client.html>`_ to access hundreds of scientific datasets in a transparent and efficient way through the internet; or as a server to easily `distribute <server.html>`_ your data from a `variety of formats <handlers.html>`_.

Quickstart
----------

You can install the latest version (|release|) using `pip <http://pypi.python.org/pypi/pip>`_. After `installing pip <http://www.pip-installer.org/en/latest/installing.html>`_ you can install Pydap with this command:

.. code-block:: bash

    $ pip install Pydap

This will install Pydap together with all the required dependencies. You can now open any remotely served dataset, and Pydap will download the accessed data on-the-fly as needed:

.. doctest:: 

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> var = dataset['SST']
    >>> var.shape
    (12, 90, 180)
    >>> var.type
    <class 'pydap.model.Float32'>
    >>> print var[0,10:14,10:14]  # this will download data from the server
    <class 'pydap.model.GridType'>
        with data
    [[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
     [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
     [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
     [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]
        and axes
    366.0
    [-69. -67. -65. -63.]
    [ 41.  43.  45.  47.]

For more information, please check the documentation on `using Pydap as a client <client.html>`_. Pydap also comes with a simple server, implemented as a `WSGI <http://wsgi.org/>`_ application. To use it, you first need to install a data handler:

.. code-block:: bash

    $ pip install pydap.handlers.netcdf

This will install support for `netCDF <http://www.unidata.ucar.edu/software/netcdf/>`_ files; more `handlers <handlers.html>`_ for different formats are available, if necessary. Now create a directory for your server data:

.. code-block:: bash

    $ paster create -t pydap myserver

To run the server just issue the command:

.. code-block:: bash

    $ paster serve ./myserver/server.ini

This will start a standalone server running on http://localhost:8001/, serving netCDF files from ``./myserver/data/``, similar to the test server at http://test.pydap.org/. Since the server uses the `WSGI <http://wsgi.org/>`_ standard, it can easily be run behind Apache. The `server documentation <server.html>`_ has more information on how to better deploy Pydap.

Help
----

If you need any help with Pydap, please feel free to send an email to the `mailing list <http://groups.google.com/group/pydap/>`_.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   client
   server
   handlers
   responses
   developer
   Changelog
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


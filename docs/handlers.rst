Handlers
========

Handlers are special Python modules that convert between a given data format and the data model used by Pydap (defined in the ``pydap.model`` module). They are necessary in order to Pydap be able to actually serve a dataset. There are handlers for NetCDF, HDF 4 & 5, Matlab, relational databases, Grib 1 & 2, CSV, Seabird CTD files, and a few more. 

Installing data handlers
------------------------

NetCDF
~~~~~~

`NetCDF <http://www.unidata.ucar.edu/software/netcdf/>`_ is a format commonly used in oceanography, meteorology and climate science to store data in a machine-independent format. You can install the NetCDF handler using `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install pydap.handlers.netcdf

This will take care of the necessary dependencies. You don't even need to have to NetCDF libraries installed, since the handler will automatically install a pure Python NetCDF library called `pupynere <http://pypi.python.org/pypi/pupynere/>`_.

The NetCDF handler uses a buffered reader that access the data in contiguous blocks from disk, avoiding reading everything into memory at once. You can configure the size of the buffer by specifying a key in the ``server.ini`` file:

.. code-block:: ini

    [app:main]
    use = egg:pydap#server
    root = %(here)s/data
    templates = %(here)s/templates
    x-wsgiorg.throw_errors = 0
    pydap.handlers.netcdf.buf_size = 10000

In this example, the handler will read 10 thousand values at a time, converting the data and sending to the client before reading more blocks.

NCA
~~~

The ``pydap.handlers.nca`` is a simple handler for NetCDF aggregation (hence the name). The configuration is extremely simple. As an example, to aggregate model output in different files (say, ``output1.nc``, ``output2.nc``, etc.) along a new axis "ensemble" just create an INI file with the extension ``.nca``:

.. code-block:: ini

    ; output.nca
    [dataset]
    match = /path/to/output*.nc
    axis = ensemble
    ; below optional metadata:
    history = Test for NetCDF aggregator
    
    [ensemble]
    values = 1, 2, ...
    long_name = Ensemble members

This will assign the values 1, 2, and so on to each ensemble member. The new, aggregated dataset, will be accessed at the location of the INI file::

    http://server.example.com/output.nca

Another example: suppose we have monthly data in files ``data01.nc``, ``data02.nc``, ..., ``data12.nc``, and we want to aggregate along the time axis:

.. code-block:: ini

    [dataset]
    match = /path/to/data*.nc
    axis = TIME  # existing axis

The handler only works with NetCDF files for now, but in the future it should be changed to work with any other Pydap-supported data format. As all handlers, it can be installed using `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install pydap.handlers.nca

CDMS
~~~~

This is a handler that uses the ``cdms2.open`` function from `CDAT <http://www2-pcmdi.llnl.gov/cdat>`_/`CdatLite <http://proj.badc.rl.ac.uk/ndg/wiki/CdatLite>`_ to read files in any of the self-describing formats netCDF, HDF, GrADS/GRIB (GRIB with a GrADS control file), or PCMDI DRS. It can be installed using `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install pydap.handlers.cdms

The handler will automatically install ``CdatLite``, which requires the NetCDF libraries to be installed on the system.

SQL
~~~

The SQL handler reads data from a relation database, as the name suggests. It works by reading a file with the extension ``.sql``, defining the connection to the database and other metadata using either YAML or INI syntax. Below is an example that reads data from a SQLite database:

.. code-block:: ini

    # please read http://groups.google.com/group/pydap/browse_thread/thread/c7f5c569d661f7f9 before
    # setting your password on the DSN
    database: 
        dsn: 'sqlite://simple.db'
        table: test

    dataset:
        NC_GLOBAL: 
            history: Created by the Pydap SQL handler
            dataType: Station
            Conventions: GrADS

        contact: roberto@dealmeida.net
        name: test_dataset
        owner: Roberto De Almeida
        version: 1.0
        last_modified: !Query 'SELECT time FROM test ORDER BY time DESC LIMIT 1;'

    sequence:
        name: simple
        items: !Query 'SELECT COUNT(id) FROM test'

    _id: 
        col: id
        long_name: sequence id
        missing_value: -9999

    lon:
        col: lon
        axis: X
        grads_dim: x
        long_name: longitude
        units: degrees_east
        missing_value: -9999
        type: Float32
        global_range: [-180, 180]
        valid_range: !Query 'SELECT min(lon), max(lon) FROM test'

    lat:
        col: lat
        axis: Y
        grads_dim: y
        long_name: latitude
        units: degrees_north
        missing_value: -9999
        type: Float32
        global_range: [-90, 90]
        valid_range: !Query 'SELECT min(lat), max(lat) FROM test'

    time:
        col: time
        axis: T
        grads_dim: t
        long_name: time
        missing_value: -9999
        type: String

    depth: 
        axis: Z
        col: depth
        long_name: depth
        missing_value: -9999
        type: Float32
        units: m

    temp:
        col: temp
        long_name: temperature
        missing_value: -9999
        type: Float32
        units: degc

The handler works with SQLite, MySQL, PostgreSQL, Oracle, MSSQL and ODBC databases. To install the handler use pip; you should also install the dependencies according to the database used:

.. code-block:: bash

    $ pip install pydap.handlers.sql
    $ pip install "pydap.handlers.sql[oracle]"
    $ pip install "pydap.handlers.sql[postgresql]"
    $ pip install "pydap.handlers.sql[mysql]"
    $ pip install "pydap.handlers.sql[mssql]"

Proxy
~~~~~

This is a simple handler intended to serve remote datasets locally. For example, suppose you want to serve `this dataset <http://test.opendap.org:8080/dods/dts/D1.html>`_ on your Pydap server. The URL of the dataset is::

    http://test.opendap.org:8080/dods/dts/D1

So we create an INI file called, say, ``D1.url``:

.. code-block:: ini

    [dataset]
    url = http://test.opendap.org:8080/dods/dts/D1
    pass = dds, das, dods

The file specifies that requests for the DDS, DAS and DODS responses should be passed directly to the server (so that the data is downloaded directly from the remote server). Other requests, like for the HTML form or a WMS image are built by Pydap; in this case Pydap acts as an Opendap client, connecting to the remote server and downloading data to fulfill the request.

CSV
~~~

This is a handler for files with comma separated values. The first column should contain the variable names, and subsequent lines the data. Metadata is not supported. The handler is used mostly as a reference for building handlers for sequential data. You can install it with:

.. code-block:: bash

    $ pip install pydap.handlers.csv

HDF5
~~~~

A handler for HDF5 files, based on `h5py <http://code.google.com/p/h5py/>`_. In order to install it:

.. code-block:: bash

    $ pip install pydap.handlers.hdf5

SQLite
~~~~~~

This is a handler very similar to the SQL handler. The major difference is that data and metadata are all contained in a single ``.db`` SQLite file. Metadata is stored as JSON in a table called ``attributes``, while data goes into a table ``data``. 

The handler was created as a way to move sequential data from one server to another. It comes with a script called ``freeze`` which will take an Opendap dataset with sequential data and create a ``.db`` file that can be served using this handler. For example:

.. code-block:: bash

    $ freeze http://opendap.ccst.inpe.br/Observations/PIRATA/pirata_stations.sql

This will creata file called ``pirata_stations.db`` that can be served using the SQLite handler.

Using the client
================

pydap can be used as a client to inspect and retrieve data from any of the thousands of scientific datasets available on the internet on `OPeNDAP <http://opendap.org/>`_ servers. This way, it's possible to instrospect and manipulate a dataset as if it were stored locally, with data being downloaded on-the-fly as necessary.

Accessing gridded data
----------------------

Let's start accessing gridded data, i.e., data that is stored as a regular multidimensional array. Here's a simple example where we access the `COADS <https://icoads.noaa.gov/>`_ climatology from the official OPeNDAP test server:

.. doctest::

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> type(dataset)
    <class 'pydap.model.DatasetType'>

Here we use the ``pydap.client.open_url`` function to open an URL specifying the location of the dataset; this URL should be stripped of the extensions commonly used for OPeNDAP datasets, like `.dds` or `.das`. When we access the remote dataset the function returns a ``DatasetType`` object, which is a *Structure* -- a fancy dictionary that stores other variables. We can check the names of the store variables like we would do with a Python dictionary:

.. doctest::

    >>> list(dataset.keys())
    ['COADSX', 'COADSY', 'TIME', 'SST', 'AIRT', 'UWND', 'VWND']

Let's work with the ``SST`` variable; we can reference it using the usual dictionary syntax of ``dataset['SST']``, or using the "lazy" syntax ``dataset.SST``:

.. doctest::

    >>> sst = dataset['SST']  # or dataset.SST
    >>> type(sst)
    <class 'pydap.model.GridType'>

Note that the variable is of type ``GridType``, a multidimensional array with specific axes defining each of its dimensions:

.. doctest::

    >>> sst.dimensions
    ('TIME', 'COADSY', 'COADSX')
    >>> sst.maps
    OrderedDict([('TIME', <BaseType with data BaseProxy('http://test.opendap.org/dap/data/nc/coads_climatology.nc', 'SST.TIME', dtype('>f8'), (12,), (slice(None, None, None),))>), ('COADSY', <BaseType with data BaseProxy('http://test.opendap.org/dap/data/nc/coads_climatology.nc', 'SST.COADSY', dtype('>f8'), (90,), (slice(None, None, None),))>), ('COADSX', <BaseType with data BaseProxy('http://test.opendap.org/dap/data/nc/coads_climatology.nc', 'SST.COADSX', dtype('>f8'), (180,), (slice(None, None, None),))>)])

Each map is also, in turn, a variable that can be accessed using the same syntax used for Structures:

.. doctest::

    >>> sst.TIME
    <BaseType with data BaseProxy('http://test.opendap.org/dap/data/nc/coads_climatology.nc', 'SST.TIME', dtype('>f8'), (12,), (slice(None, None, None),))>

The axes are all of type ``BaseType``. This is the OPeNDAP equivalent of a multidimensional array, with a specific shape and type. Even though no data have been downloaded up to this point, we can introspect these attributes from the axes or from the Grid itself:

.. doctest::

    >>> sst.shape
    (12, 90, 180)
    >>> sst.dtype
    dtype('>f4')
    >>> sst.TIME.shape
    (12,)
    >>> sst.TIME.dtype
    dtype('>f8')

We can also introspect the variable attributes; they are stored in an attribute appropriately called ``attributes``, and they can also be accessed with a "lazy" syntax:

.. doctest::

    >>> import pprint
    >>> pprint.pprint(sst.attributes)
    {'_FillValue': -9.99999979e+33,
     'history': 'From coads_climatology',
     'long_name': 'SEA SURFACE TEMPERATURE',
     'missing_value': -9.99999979e+33,
     'units': 'Deg C'}
    >>> sst.units
    'Deg C'

Finally, we can also download some data. To download data we simply access it like we would access a `Numpy <https://numpy.org/doc/stable/>`_ array, and the data for the corresponding subset will be dowloaded on the fly from the server:

.. doctest::

    >>> sst.shape
    (12, 90, 180)
    >>> grid = sst[0,10:14,10:14]  # this will download data from the server
    >>> grid
    <GridType with array 'SST' and maps 'TIME', 'COADSY', 'COADSX'>

The data itself can be accessed in the ``array`` attribute of the Grid, and also on the individual axes:

.. doctest::

    >>> grid.array[:]
    <BaseType with data array([[[ -1.26285708e+00,  -9.99999979e+33,  -9.99999979e+33,
              -9.99999979e+33],
            [ -7.69166648e-01,  -7.79999971e-01,  -6.75454497e-01,
              -5.95714271e-01],
            [  1.28333330e-01,  -5.00000156e-02,  -6.36363626e-02,
              -1.41666666e-01],
            [  6.38000011e-01,   8.95384610e-01,   7.21666634e-01,
               8.10000002e-01]]], dtype=float32)>
    >>> print(grid.array[:].data)
    [[[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
      [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
      [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
      [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]]
    >>> grid.COADSX[:]
    <BaseType with data array([ 41.,  43.,  45.,  47.])>
    >>> print(grid.COADSX[:].data)
    [ 41.  43.  45.  47.]

Alternatively, we could have dowloaded the data directly, skipping the axes:

.. doctest::

    >>> print(sst.array[0,10:14,10:14].data)
    [[[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
      [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
      [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
      [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]]

Older Servers
~~~~~~~~~~~~~
Some servers using a very old OPeNDAP application might run of of memory when attempting to retrieve both the data and
the coordinate axes of a variable. The work around is to simply disable the retrieval of coordinate axes by using the
``output_grid`` option to open url:

.. doctest::

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc', output_grid=False)
    >>> grid = sst[0,10:14,10:14]  # this will download data from the server
    >>> grid
    <GridType with array 'SST' and maps 'TIME', 'COADSY', 'COADSX'>


Accessing sequential in situ data
---------------------------------

Now let's see an example of accessing sequential data. Sequential data consists of one or more records of related variables, such as a simultaneous measurements of temperature and wind velocity, for example. In this example we're going to access data from the `glider <https://oceanservice.noaa.gov/facts/ocean-gliders.html>`_ DAC found at the `Integrated Ocean Observing System <https://data.ioos.us/organization/glider-dac>`_ . The data can be accessed through an OPeNDAP server, as well as the `ERRDAP <https://gliders.ioos.us/erddap/index.html>`_ server. In the example below we demostrate how to access glider data from a Deep-Pelagic Nekton study off the Gulf of Mexico, with pydap through ERRDAP.

.. doctest:: python

    >>> from pydap.client import open_url
    >>> url = "https://gliders.ioos.us/erddap/tabledap/Murphy-20150809T1355.html" # this URL takes you to the ERDDAP data access form
    >>> dataset = open_url(url)['s']
    >>> type(dataset)
    pydap.model.SequenceType


ERRDAP adds a parent `s` variable, and below this is a fairly complex sequential array with many in situ variables for the entire deployment. We quickly inspect some of the variables in the sequence array

.. doctest:: python

    >>> print([key for key in dataset.keys()][2::4])
    ['profile_id', 'depth', 'density_qc', 'lat_uv', 'lon_uv_qc', 'precise_time', 'profile_lon_qc', 'salinity_qc', 'time_uv', 'v']
    >>> len([id_ for id_ in dataset['profile_id']])
    189

We can identify each individual glider data by looking at the profile id, a value that is unique for each of them. You can inspect the raw values are follows

.. doctest:: python

    >>> dataset['profile_id.'] # note the use of `.` 
    <BaseType with data SequenceProxy('https://gliders.ioos.us/erddap/tabledap/Murphy-20150809T1355', <BaseType with data <IterData to stream [(1,), (2,), (3,),(4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,), (12,), (13,), (14,), (15,), (16,), (17,), (18,), (19,), (20,), (21,), (22,), (23,), (24,), (25,), (26,), (27,), (28,), (29,), (30,), (31,), (32,), (33,), (34,), (35,), (36,), (37,), (38,), (39,), (40,), (41,), (42,), (43,), (44,), (45,), (46,), (47,), (48,), (49,),(50,), (51,), (52,), (53,), (54,), (55,), (56,), (57,), (58,), (59,), (60,), (61,), (62,), (63,), (64,), (65,), (66,), (67,), (68,), (69,), (70,), (71,), (72,), (73,), (74,), (75,), (76,), (77,), (78,), (79,), (80,), (81,), (82,), (83,), (84,), (85,), (86,), (87,), (88,), (89,), (90,), (91,), (92,), (93,), (94,),(95,), (96,), (97,), (98,), (99,), (100,), (101,), (102,), (103,), (104,), (105,), (106,), (107,), (108,), (109,), (110,), (111,), (112,), (113,), (114,), (115,), (116,), (117,), (118,), (119,), (120,), (121,), (122,), (123,), (124,), (125,), (126,), (127,), (128,), (129,), (130,), (131,), (132,), (133,), (134,), (135,), (136,), (137,), (138,), (139,), (140,), (141,), (142,), (143,), (144,), (145,), (146,), (147,), (148,), (149,), (150,), (151,), (152,), (153,), (154,),(155,), (156,), (157,), (158,), (159,), (160,), (161,), (162,), (163,), (164,), (165,), (166,), (167,), (168,), (169,), (170,), (171,), (172,), (173,), (174,),(175,), (176,), (177,), (178,), (179,), (180,), (181,), (182,), (183,), (184,), (185,), (186,), (187,), (188,), (189,)]>>, [], (slice(None, None, None),))>


These datasets are rich in metadata, which can be accessed through the attributes property as follows

.. doctest:: python

    >>> dataset['profile_id'].attributes
    {'_FillValue': -1,
     'actual_range': [1, 189],
     'cf_role': 'profile_id',
     'comment': 'Sequential profile number within the trajectory.  This value is unique in each file that is part of a single trajectory/deployment.',
     'ioos_category': 'Identifier',
     'long_name': 'Profile ID',
     'valid_max': 2147483647,
     'valid_min': 1}


The first thing we'd like to do is limit our very simple analysis. We consider only a single glider and
only inspect the variables `depth` and `temperature`. To accomplish that we use pydap's simple logic as
follows

.. doctest:: python

    >>> seq = dataset[('profile_id', 'depth', 'temperature')]
    >>> glid5 = seq[('profile_id', 'depth', 'temperature')].data[seq['profile_id.']==5]
    >>> type(glid5)
    pydap.handlers.dap.SequenceProxy

We can now unpack the values for each variables with common pythonic syntax

.. doctest:: python

    >>> Depths = np.array([depth for depth in glid5['depth']])
    >>> IDs = np.array([id_ for id_ in glid5['profile_id']])
    >>> Temps = np.array([temp for temp in glid5['temperature']])
    >>> for i in range(5):
        print([list(IDs), Depths[i], Temps[i]])
    [[5], 10.95661, 30.1331]
    [[5], 12.547435, 30.1232]
    [[5], 14.361932, 30.1104]
    [[5], 15.034961, 30.0979]
    [[5], 17.547983, 30.0903]

An similarly for glider with `id=6`

.. doctest:: python

    >>> glid6 = seq[('profile_id', 'depth', 'temperature')].data[seq['profile_id.']==6]
    >>> Depths = np.array([depth for depth in glid6['depth']])
    >>> IDs = np.array([id_ for id_ in glid6['profile_id']])
    >>> Temps = np.array([temp for temp in glid6['temperature']])
    >>> for i in range(5):
        print([list(IDs), Depths[i], Temps[i]])
    [[6], 10.013372, 30.1366]
    [[6], 12.850507, 30.1172]
    [[6], 14.958507, 30.092]
    [[6], 16.944101, 30.0838]
    [[6], 17.751884, 30.0753]
    

The glider profiles could be easily plotted using `matplotlib <https://matplotlib.org/stable/users/index>`_:


Authentication
--------------

Basic & Digest
~~~~~~~~~~~~~~

To use Basic and Digest authentication, simply add your username and password to the dataset URL. Keep in mind that if the server only supports Basic authentication your credentials will be sent as plaintext, and could be sniffed on the network.

.. code-block:: python

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://username:password@server.example.com/path/to/dataset')

CAS
~~~

The `Central Authentication Service <http://en.wikipedia.org/wiki/Central_Authentication_Service>`_ (CAS) is a single sign-on protocol for the web, usually involving a web browser and cookies. Nevertheless it's possible to use pydap with an OPeNDAP server behind a CAS. The function ``install_cas_client`` below replaces pydap's default HTTP function with a new version able to submit authentication data to an HTML form and store credentials in cookies. (In this particular case, the server uses Javascript to redirect the browser to a new location, so the client has to parse the location from the Javascript code; other CAS would require a tweaked function.)

To use it, just attach a web browsing ``session`` with authentication cookies:

.. code-block:: python

    >>> from pydap.client import open_url
    >>> from pydap.cas.get_cookies import setup_session
    >>> session = setup_session(authentication_url, username, password)
    >>> dataset = open_url('http://server.example.com/path/to/dataset', session=session)

This method could work but each CAS is slightly different and might require a specifically designed
``setup_session`` instance. Two CAS are however explicitly supported by ``pydap``:

URS NASA EARTHDATA
^^^^^^^^^^^^^^^^^^
Authentication is done through a ``username`` and a ``password``:

.. code-block:: python

    >>> from pydap.client import open_url
    >>> from pydap.cas.urs import setup_session
    >>> dataset_url = 'http://server.example.com/path/to/dataset'
    >>> session = setup_session(username, password, check_url=dataset_url)
    >>> dataset = open_url(dataset_url, session=session)

Earth System Grid Federation (ESGF)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Authentication is done through an ``openid`` and a ``password``:

.. code-block:: python

    >>> from pydap.client import open_url
    >>> from pydap.cas.esgf import setup_session
    >>> dataset_url = 'http://server.example.com/path/to/dataset'
    >>> session = setup_session(openid, password, check_url=dataset_url)
    >>> dataset = open_url(dataset_url, session=session)

If your ``openid`` contains contains the
string ``ceda.ac.uk`` authentication requires an additional ``username`` argument:

.. code-block:: python

    >>> from pydap.client import open_url
    >>> from pydap.cas.esgf import setup_session
    >>> session = setup_session(openid, password, check_url=dataset_url, username=username)
    >>> dataset = open_url(dataset_url, session=session)

Advanced features
-----------------

Calling server-side functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you open a remote dataset, the ``DatasetType`` object has a special attribute named ``functions`` that can be used to invoke any server-side functions. Here's an example of using the ``geogrid`` function from Hyrax:

.. doctest::

    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> new_dataset = dataset.functions.geogrid(dataset.SST, 10, 20, -10, 60)
    >>> new_dataset.SST.shape
    (12, 12, 21)
    >>> new_dataset.SST.COADSY[:]
    [-11.  -9.  -7.  -5.  -3.  -1.   1.   3.   5.   7.   9.  11.]
    >>> new_dataset.SST.COADSX[:]
    [ 21.  23.  25.  27.  29.  31.  33.  35.  37.  39.  41.  43.  45.  47.  49.
      51.  53.  55.  57.  59.  61.]

Unfortunately, there's currently no standard mechanism to discover which functions the server support. The ``function`` attribute will accept any function name the user specifies, and will try to pass the call to the remote server.

Opening a specific URL
~~~~~~~~~~~~~~~~~~~~~~

You can pass any URL to the ``open_url`` function, together with any valid constraint expression. Here's an example of restricting values for the months of January, April, July and October:

.. doctest::

    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc?SST[0:3:11][0:1:89][0:1:179]')
    >>> dataset.SST.shape
    (4, 90, 180)

This can be extremely useful for server side-processing; for example, we can create and access a new variable ``A`` in this dataset, equal to twice ``SSH``:

.. doctest::

    >>> dataset = open_url('http://hycom.coaps.fsu.edu:8080/thredds/dodsC/las/dynamic/data_A5CDC5CAF9D810618C39646350F727FF.jnl_expr_%7B%7D%7Blet%20A=SSH*2%7D?A')
    >>> dataset.keys()
    ['A']

In this case, we're using the Ferret syntax ``let A=SSH*2`` to define the new variable, since the data is stored in an `F-TDS server <http://ferret.pmel.noaa.gov/LAS/documentation/the-ferret-thredds-data-server-f-tds/using-f-tds-and-the-server-side-analysis/>`_. Server-side processing is useful when you want to reduce the data before downloading it, to calculate a global average, for example.

Accessing raw data
~~~~~~~~~~~~~~~~~~

The client module has a special function called ``open_dods``, used to access raw data from a DODS response:

.. doctest::

    >>> from pydap.client import open_dods
        >>> dataset = open_dods_url(
        ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods?SST[0:3:11][0:1:89][0:1:179]')

    This function allows you to access raw data from any URL, including appending expressions to
    >>> dataset = open_dods(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods?SST[0:3:11][0:1:89][0:1:179]')

This function allows you to access raw data from any URL, including appending expressions to `F-TDS <http://ferret.pmel.noaa.gov/LAS/documentation/the-ferret-thredds-data-server-f-tds/>`_ and `GDS <http://www.iges.org/grads/gds/>`_ servers or calling server-side functions directly. By default this method downloads the data directly, and skips metadata from the DAS response; if you want to investigate and introspect datasets you should set the ``get_metadata`` parameter to true:

.. doctest::

    >>> dataset = open_dods(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods?SST[0:3:11][0:1:89][0:1:179]',
    ...      get_metadata=True)
    >>> dataset.attributes['NC_GLOBAL']['history']
    FERRET V4.30 (debug/no GUI) 15-Aug-96


Using a cache
~~~~~~~~~~~~~

You can specify a cache directory in the ``pydap.lib.CACHE`` global variable. If this value is different than ``None``, the client will try (if the server headers don't prohibit) to cache the result, so repeated requests will be read from disk instead of the network:

.. code-block:: python

    >>> import pydap.lib
    >>> pydap.lib.CACHE = "/tmp/pydap-cache/"

Timeout
~~~~~~~

To specify a timeout for the client, just set the desired number of seconds using the ``timeout`` option to ``open_url(...)`` or ``open_dods(...)``.
For example, the following commands would timeout after 30 seconds without receiving a response from the server:

.. code-block:: python

    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc', timeout=30)
    >>> dataset = open_dods('http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods', timeout=30)

Configuring a proxy
~~~~~~~~~~~~~~~~~~~

It's possible to configure pydap to access the network through a proxy server. Here's an example for an HTTP proxy running on ``localhost`` listening on port 8000:

.. code-block:: python

    >>> import httplib2
    >>> from pydap.util import socks
    >>> import pydap.lib
    >>> pydap.lib.PROXY = httplib2.ProxyInfo(
    ...         socks.PROXY_TYPE_HTTP, 'localhost', 8000)

This way, all further calls to ``pydap.client.open_url`` will be routed through the proxy server. You can also authenticate to the proxy:

.. code-block:: python

    >>> pydap.lib.PROXY = httplib2.ProxyInfo(
    ...         socks.PROXY_TYPE_HTTP, 'localhost', 8000,
    ...         proxy_user=USERNAME, proxy_pass=PASSWORD)

A user `has reported <http://groups.google.com/group/pydap/browse_thread/thread/425b2e1a3b3f233d>`_ that ``httplib2`` has problems authenticating against a NTLM proxy server. In this case, a simple solution is to change the ``pydap.http.request`` function to use ``urllib2`` instead of ``httplib2``, monkeypatching the code like in the `CAS authentication example above <#cas>`_:

.. code-block:: python

    import urllib2
    import logging

    def install_urllib2_client():
        def new_request(url):
            log = logging.getLogger('pydap')
            log.INFO('Opening %s' % url)

            f = urllib2.urlopen(url.rstrip('?&'))
            headers = dict(f.info().items())
            body = f.read()
            return headers, body

        from pydap.util import http
        http.request = new_request

The function ``install_urllib2_client`` should then be called before doing any requests.

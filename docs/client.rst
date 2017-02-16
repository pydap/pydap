Using the client
================

Pydap can be used as a client to inspect and retrieve data from any of the `hundreds of scientific datasets <http://www.opendap.org/data/datasets.cgi?xmlfilename=datasets.xml&exfunction=none>`_ available on the internet on `OPeNDAP <http://opendap.org/>`_ servers. This way, it's possible to instrospect and manipulate a dataset as if it were stored locally, with data being downloaded on-the-fly as necessary.

Accessing gridded data
----------------------

Let's start accessing gridded data, i.e., data that is stored as a regular multidimensional array. Here's a simple example where we access the `COADS <http://www.ncdc.noaa.gov/oa/climate/coads/>`_ climatology from the official OPeNDAP server:

.. doctest::

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> print type(dataset)
    <class 'pydap.model.DatasetType'>

Here we use the ``pydap.client.open_url`` function to open an URL specifying the location of the dataset; this URL should be stripped of the extensions commonly used for OPeNDAP datasets, like `.dds` or `.das`. When we access the remote dataset the function returns a ``DatasetType`` object, which is a *Structure* -- a fancy dictionary that stores other variables. We can check the names of the store variables like we would do with a Python dictionary:

.. doctest::

    >>> print dataset.keys()
    ['SST', 'AIRT', 'UWND', 'VWND']

Let's work with the ``SST`` variable; we can reference it using the usual dictionary syntax of ``dataset['SST']``, or using the "lazy" syntax ``dataset.SST``:

.. doctest::

    >>> sst = dataset['SST']  # or dataset.SST
    >>> print type(sst)
    <class 'pydap.model.GridType'>

Note that the variable is of type ``GridType``, a multidimensional array with specific axes defining each of its dimensions:

.. doctest::
    
    >>> print sst.dimensions
    ('TIME', 'COADSY', 'COADSX')
    >>> print sst.maps  #doctest: +ELLIPSIS
    {'TIME': <pydap.model.BaseType object at ...>, 'COADSY': <pydap.model.BaseType object at ...>, 'COADSX': <pydap.model.BaseType object at ...>}

Each map is also, in turn, a variable that can be accessed using the same syntax used for Structures:

.. doctest::

    >>> print sst.TIME  #doctest: +ELLIPSIS
    <class 'pydap.model.BaseType'>
        with data
    <ArrayProxy pointing to variable "SST.TIME" at "http://test.opendap.org/dap/data/nc/coads_climatology.nc">

The axes are all of type ``BaseType``. This is the OPeNDAP equivalent of a multidimensional array, with a specific shape and type. Even though no data have been downloaded up to this point, we can introspect these attributes from the axes or from the Grid itself:

.. doctest::

    >>> print sst.shape
    (12, 90, 180)
    >>> print sst.type
    <class 'pydap.model.Float32'>
    >>> print sst.TIME.shape
    (12,)
    >>> print sst.TIME.type
    <class 'pydap.model.Float64'>

We can also introspect the variable attributes; they are stored in an attribute appropriately called ``attributes``, and they can also be accessed with a "lazy" syntax:

.. doctest::

    >>> import pprint
    >>> pprint.pprint(sst.attributes)
    {'_FillValue': -9.999999790214768e+33,
     'history': 'From coads_climatology',
     'long_name': 'SEA SURFACE TEMPERATURE',
     'missing_value': -9.999999790214768e+33,
     'units': 'Deg C'}
    >>> print sst.units
    Deg C

Finally, we can also download some data. To download data we simply access it like we would access a `Numpy <http://numpy.scipy.org/>`_ array, and the data for the corresponding subset will be dowloaded on the fly from the server:

.. doctest::

    >>> print sst.shape
    (12, 90, 180)
    >>> grid = sst[0,10:14,10:14]  # this will download data from the server
    >>> print grid
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

The data itself can be accessed in the ``array`` attribute of the Grid, and also on the individual axes:

.. doctest::

    >>> print grid.array[:]
    [[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
     [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
     [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
     [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]
    >>> print grid.COADSX[:]
    [ 41.  43.  45.  47.]

Alternatively, we could have dowloaded the data directly, skipping the axes:

.. doctest::

    >>> print sst.array[0,10:14,10:14] 
    [[ -1.26285708e+00  -9.99999979e+33  -9.99999979e+33  -9.99999979e+33]
     [ -7.69166648e-01  -7.79999971e-01  -6.75454497e-01  -5.95714271e-01]
     [  1.28333330e-01  -5.00000156e-02  -6.36363626e-02  -1.41666666e-01]
     [  6.38000011e-01   8.95384610e-01   7.21666634e-01   8.10000002e-01]]

Instead of indexes we can also subset the data using its maps, in a more natural way. Just keep in mind that sometimes axes can be cyclic, like longitude, and you may have to download two separate parts and concatenate them together. This is not the case here:

.. doctest::

    >>> print sst[ 0 , (-10 < sst.COADSY) & (sst.COADSY < 10) , (sst.COADSX > 320) & (sst.COADSX < 328) ]
    <class 'pydap.model.GridType'>
        with data
    [[ -9.99999979e+33  -9.99999979e+33   2.75645447e+01   2.74858131e+01]
     [ -9.99999979e+33  -9.99999979e+33   2.75924988e+01   2.74538631e+01]
     [  2.74333324e+01   2.75676193e+01   2.75849991e+01   2.72220459e+01]
     [  2.74995346e+01   2.75236359e+01   2.75734081e+01   2.71845455e+01]
     [  2.75163631e+01   2.74263630e+01   2.73368282e+01   2.72538090e+01]
     [  2.74848824e+01   2.74654541e+01   2.72157135e+01   2.71914806e+01]
     [  2.75176182e+01   2.74858055e+01   2.71117859e+01   2.71154156e+01]
     [  2.74184361e+01   2.71918182e+01   2.70971432e+01   2.68821430e+01]
     [  2.66373062e+01   2.65258331e+01   2.66468735e+01   2.65185719e+01]
     [  2.56100006e+01   2.62577419e+01   2.62805882e+01   2.62171783e+01]]
        and axes
    366.0
    [-9. -7. -5. -3. -1.  1.  3.  5.  7.  9.]
    [ 321.  323.  325.  327.]

Older Servers
^^^^^^^^^^^^^
Some servers using a very old OPeNDAP application might run of of memory when attempting to retrieve both the data and
the coordinate axes of a variable. The work around is to simply disable the retrieval of coordinate axes by using the
``output_grid`` option to open url:

.. doctest::

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc', output_grid=False)


Accessing sequential data
-------------------------

Now let's see an example of accessing sequential data. Sequential data consists of one or more records of related variables, such as a simultaneous measurements of temperature and wind velocity, for example. In this example we're going to access data from the `Argo project <http://www.argo.ucsd.edu/>`_, consisting of profiles made by autonomous buoys drifting on the ocean:

.. doctest:: python

    >>> from pydap.client import open_url
    >>> dataset = open_url('http://dapper.pmel.noaa.gov/dapper/argo/argo_all.cdp')

This dataset is fairly complex, with several variables representing heterogeneous 4D data. The layout of the dataset follows the `Dapper in-situ conventions <http://www.epic.noaa.gov/epic/software/dapper/dapperdocs/conventions/>`_, consisting of two nested sequences: the outer sequence contains, in this case, a latitude, longitude and time variable, while the inner sequence contains measurements along a z axis.

The first thing we'd like to do is limit our region; let's work with a small region in the Tropical Atlantic:

.. doctest:: python

    >>> print type(dataset.location)
    <class 'pydap.model.SequenceType'>
    >>> print dataset.location.keys()
    ['LATITUDE', 'JULD', 'LONGITUDE', '_id', 'profile', 'attributes', 'variable_attributes']
    >>> my_location = dataset.location[
    ...         (dataset.location.LATITUDE > -2) &
    ...         (dataset.location.LATITUDE < 2) &
    ...         (dataset.location.LONGITUDE > 320) &
    ...         (dataset.location.LONGITUDE < 330)]

Note that the variable ``dataset.location`` is of type ``SequenceType`` -- also a Structure that holds other variables. Here we're limiting the sequence ``dataset.location`` to measurements between given latitude and longitude boundaries. Let's access the identification number of the first 10-or-so profiles:

.. code-block:: python

    >>> for i, id_ in enumerate(my_location['_id']):
    ...     print id_
    ...     if i == 10:
    ...         print '...'
    ...         break
    1125393
    835304
    839894
    875344
    110975
    864748
    832685
    887712
    962673
    881368
    1127922
    ...
    >>> print len(my_location['_id'])
    623

Note that calculating the length of a sequence takes some time, since the client has to download all the data and do the calculation locally. This is why you should use ``len(my_location['_id'])`` instead of ``len(my_location)``. Both should give the same result (unless the dataset changes between requests), but the former retrieves only data for the ``_id`` variable, while the later retrives data for all variables.

We can explicitly select just the first 5 profiles from our sequence:

.. doctest:: python

    >>> my_location = my_location[:5]
    >>> print len(my_location['_id'])
    5

And we can print the temperature profiles at each location. We're going to use the `coards <http://pypi.python.org/pypi/coards>`_ module to convert the time to a Python ``datetime`` object:

.. code-block:: python

    >>> from coards import from_udunits
    >>> for position in my_location:
    ...     date = from_udunits(position.JULD.data, position.JULD.units.replace('GMT', '+0:00'))
    ...     print
    ...     print position.LATITUDE.data, position.LONGITUDE.data, date
    ...     print '=' * 40
    ...     i = 0
    ...     for pressure, temperature in zip(position.profile.PRES, position.profile.TEMP):
    ...         print pressure, temperature
    ...         if i == 10:
    ...             print '...'
    ...             break
    ...         i += 1
    <BLANKLINE>
    -1.01 320.019 2009-05-03 11:42:34+00:00
    ========================================
    5.0 28.59
    10.0 28.788
    15.0 28.867
    20.0 28.916
    25.0 28.94
    30.0 28.846
    35.0 28.566
    40.0 28.345
    45.0 28.05
    50.0 27.595
    55.0 27.061
    ...
    <BLANKLINE>
    -0.675 320.027 2006-12-25 13:24:11+00:00
    ========================================
    5.0 27.675
    10.0 27.638
    15.0 27.63
    20.0 27.616
    25.0 27.617
    30.0 27.615
    35.0 27.612
    40.0 27.612
    45.0 27.605
    50.0 27.577
    55.0 27.536
    ...
    <BLANKLINE>
    -0.303 320.078 2007-01-12 11:30:31.001000+00:00
    ========================================
    5.0 27.727
    10.0 27.722
    15.0 27.734
    20.0 27.739
    25.0 27.736
    30.0 27.718
    35.0 27.694
    40.0 27.697
    45.0 27.698
    50.0 27.699
    55.0 27.703
    ...
    <BLANKLINE>
    -1.229 320.095 2007-04-22 13:03:35.002000+00:00
    ========================================
    5.0 28.634
    10.0 28.71
    15.0 28.746
    20.0 28.758
    25.0 28.755
    30.0 28.747
    35.0 28.741
    40.0 28.737
    45.0 28.739
    50.0 28.748
    55.0 28.806
    ...
    <BLANKLINE>
    -1.82 320.131 2003-04-09 13:20:03+00:00
    ========================================
    5.1 28.618
    9.1 28.621
    19.4 28.637
    29.7 28.662
    39.6 28.641
    49.6 28.615
    59.7 27.6
    69.5 26.956
    79.5 26.133
    89.7 23.937
    99.2 22.029
    ...

These profiles could be easily plotted using `matplotlib <http://matplotlib.sf.net/>`_:

.. code-block:: python

    >>> for position in my_location:
    ...     plot(position.profile.TEMP, position.profile.PRES)
    >>> show()

You can also access the deep variables directly. When you iterate over these variables the client will download the data as nested lists:

.. code-block:: python

    >>> for value in my_location.profile.PRES:
    ...     print value[:10]
    [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    [5.0999999, 9.1000004, 19.4, 29.700001, 39.599998, 49.599998, 59.700001, 69.5, 79.5, 89.699997]

Pydap 3.0 has been rewritten to make it easier to work with Dapper datasets like this one, and it should be intuitive [1]_ to work with these variables. 

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

The `Central Authentication Service <http://en.wikipedia.org/wiki/Central_Authentication_Service>`_ (CAS) is a single sign-on protocol for the web, usually involving a web browser and cookies. Nevertheless it's possible to use Pydap with an OPeNDAP server behind a CAS. The function ``install_cas_client`` below replaces Pydap's default HTTP function with a new version able to submit authentication data to an HTML form and store credentials in cookies. (In this particular case, the server uses Javascript to redirect the browser to a new location, so the client has to parse the location from the Javascript code; other CAS would require a tweaked function.)

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
    >>> session = setup_session(openid, password)
    >>> dataset = open_url('http://server.example.com/path/to/dataset', session=session)

If your ``openid`` contains contains the
string ``ceda.ac.uk`` authentication requires an additional ``username`` argument:

.. code-block:: python

    >>> from pydap.client import open_url  
    >>> from pydap.cas.esgf import setup_session 
    >>> session = setup_session(openid, password, username=username)
    >>> dataset = open_url('http://server.example.com/path/to/dataset', session=session)

Advanced features
-----------------

Calling server-side functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you open a remote dataset, the ``DatasetType`` object has a special attribute named ``functions`` that can be used to invoke any server-side functions. Here's an example of using the ``geogrid`` function from Hyrax:

.. doctest::

    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> new_dataset = dataset.functions.geogrid(dataset.SST, 10, 20, -10, 60)
    >>> print new_dataset.SST.shape
    (12, 12, 21)
    >>> print new_dataset.SST.COADSY[:]
    [-11.  -9.  -7.  -5.  -3.  -1.   1.   3.   5.   7.   9.  11.]
    >>> print new_dataset.SST.COADSX[:]
    [ 21.  23.  25.  27.  29.  31.  33.  35.  37.  39.  41.  43.  45.  47.  49.
      51.  53.  55.  57.  59.  61.]

Unfortunately, there's currently no standard mechanism to discover which functions the server support. The ``function`` attribute will accept any function name the user specifies, and will try to pass the call to the remote server.

Opening a specific URL
~~~~~~~~~~~~~~~~~~~~~~

You can pass any URL to the ``open_url`` function, together with any valid constraint expression. Here's an example of restricting values for the months of January, April, July and October:

.. doctest::

    >>> dataset = open_url('http://test.opendap.org/dap/data/nc/coads_climatology.nc?SST[0:3:11][0:1:89][0:1:179]')
    >>> print dataset.SST.shape
    (4, 90, 180)

This can be extremely useful for server side-processing; for example, we can create and access a new variable ``A`` in this dataset, equal to twice ``SSH``:

.. doctest::

    >>> dataset = open_url('http://hycom.coaps.fsu.edu:8080/thredds/dodsC/las/dynamic/data_A5CDC5CAF9D810618C39646350F727FF.jnl_expr_%7B%7D%7Blet%20A=SSH*2%7D?A')
    >>> print dataset.keys()
    ['A']

In this case, we're using the Ferret syntax ``let A=SSH*2`` to define the new variable, since the data is stored in an `F-TDS server <http://ferret.pmel.noaa.gov/LAS/documentation/the-ferret-thredds-data-server-f-tds/using-f-tds-and-the-server-side-analysis/>`_. Server-side processing is useful when you want to reduce the data before downloading it, to calculate a global average, for example.

Accessing raw data
~~~~~~~~~~~~~~~~~~

The client module has a special function called ``open_dods``, used to access raw data from a DODS response:

.. doctest::

    >>> from pydap.client import open_dods
    >>> dataset = open_dods(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods?SST[0:3:11][0:1:89][0:1:179]')

This function allows you to access raw data from any URL, including appending expressions to `F-TDS <http://ferret.pmel.noaa.gov/LAS/documentation/the-ferret-thredds-data-server-f-tds/>`_ and `GDS <http://www.iges.org/grads/gds/>`_ servers or calling server-side functions directly. By default this method downloads the data directly, and skips metadata from the DAS response; if you want to investigate and introspect datasets you should set the ``get_metadata`` parameter to true:

.. doctest::

    >>> dataset = open_dods(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc.dods?SST[0:3:11][0:1:89][0:1:179]',
    ...      get_metadata=True)
    >>> print dataset.attributes['NC_GLOBAL']['history']
    FERRET V4.30 (debug/no GUI) 15-Aug-96


Using a cache
~~~~~~~~~~~~~

You can specify a cache directory in the ``pydap.lib.CACHE`` global variable. If this value is different than ``None``, the client will try (if the server headers don't prohibit) to cache the result, so repeated requests will be read from disk instead of the network:

.. code-block:: python

    >>> import pydap.lib
    >>> pydap.lib.CACHE = "/tmp/pydap-cache/"

Timeout
~~~~~~~

To specify a timeout for the client, just set the global variable ``pydap.lib.TIMEOUT`` to the desired number of seconds; after this time trying to connect the client will give up. The default is ``None`` (never timeout).

.. code-block:: python

    >>> import pydap.lib
    >>> pydap.lib.TIMEOUT = 60

Configuring a proxy
~~~~~~~~~~~~~~~~~~~

It's possible to configure Pydap to access the network through a proxy server. Here's an example for an HTTP proxy running on ``localhost`` listening on port 8000:

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

.. [1] But please check `this quote <http://www.greenend.org.uk/rjk/2002/08/nipple.html>`_.


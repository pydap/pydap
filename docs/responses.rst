Responses
=========

Like `handlers <handlers.html>`_, responses are special Python modules that convert between the Pydap data model and an external representation. For instance, to access a given dataset an Opendap client request two diferent representations of the dataset: a *Dataset Attribute Structure* (DAS) response, describing the attributes of the dataset, and a *Dataset Descriptor Structure* (DDS), describing its structure (shape, type, hierarchy). These responses are returned by appending the extension ``.das`` and ``.dds`` to the dataset URL, respectively.

Other common responses include the ASCII (``.asc`` or ``.ascii``) response, which returns an ASCII representation of the data; and an HTML form for data request using the browser, at the ``.html`` extension. And perhaps the most important response is the ``.dods`` response, which actually carries the data in binary format, and is used when clients request data from the server. All these responses are standard and come with Pydap.

There are other extension responses available for Pydap; these are not defined in the DAP specification, but improve the user experience by allowing data to be accessed in different formats.

Installing additional responses
-------------------------------

Web Map Service
~~~~~~~~~~~~~~~

This response enables Pydap to act like a `Web Map Service <http://en.wikipedia.org/wiki/Web_Map_Service>`_ 1.1.1 server, returning images (maps) of the available data. These maps can be visualized in any WMS client like Openlayers or Google Earth.

You can install the WMS response using `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install pydap.responses.wms

This will take care of the necessary dependencies, which include `Matplotlib <http://matplotlib.sf.net/>`_ and Pydap itself. Once the response is installed you can introspect the available layers at the URL::

    http://server.example.com/dataset.wms?REQUEST=GetCapabilities

The response will create valid layers from any `COARDS <http://ferret.wrc.noaa.gov/noaa_coop/coop_cdf_profile.html>`_ compliant datasets, ie, grids with properly defined latitude and longitude axes. If the data is not two-dimensional it will be averaged along each axis except for the last two, so the map represents a time and/or level average of the data. Keep in mind that Opendap constraint expressions apply before the map is generated, so it's possible to create a map of a specific level (or time) by constraining the variable on the URL::

    http://server.example.com/dataset.wms?var3d[0]&REQUEST=GetCapabilities

You can specify the default colormap and the DPI resolution in the ``server.ini`` file:

.. code-block:: ini

    [app:main]
    use = egg:pydap#server
    root = %(here)s/data
    templates = %(here)s/templates
    x-wsgiorg.throw_errors = 0
    pydap.responses.wms.dpi = 80
    pydap.responses.wms.cmap = jet

Google Earth
~~~~~~~~~~~~

This response converts a Pydap dataset to a `KML <http://code.google.com/apis/kml/documentation/kmlreference.html>`_ representation, allowing the data to be visualized using Google Earth as a client. Simply install it with `pip <http://pypi.python.org/pypi/pip>`_:

.. code-block:: bash

    $ pip install pydap.responses.kml

And open a URL by appending the ``.kml`` extension to the dataset, say::

    http://server.example.com/dataset.kml

For now, the KML response will only return datasets that have a valid WMS representation. These datasets can be overlayed as layers on top of Google Earth, and are presented with a nice colorbar. In the future, `Dapper <http://www.epic.noaa.gov/epic/software/dapper/dapperdocs/conventions/>`_-compliant datasets should be supported too.

NetCDF
~~~~~~

This response allows data to be downloaded as a NetCDF file; it works better with gridded data, but sequential data will be converted into 1D variables. To install it, just type:

.. code-block:: bash

    $ pip install pydap.responses.netcdf

And try to append the extension ``.nc`` to a request. The data will be converted on-the-fly to a NetCDF file.

Matlab
~~~~~~

The Matlab response returns data in a Matlab v5 file. It is returned when the file is requested with the extension ``.mat``, and can be installed by with:

.. code-block:: bash

    $ pip install pydap.responses.matlab

Excel spreadsheet
~~~~~~~~~~~~~~~~~

This response returns sequential data as an Excel spreadsheet when ``.xls`` is appended to the URL. Install with:

.. code-block:: bash

    $ pip install pydap.responses.xls

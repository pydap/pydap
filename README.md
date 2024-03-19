pydap
=====

[![Build Status](https://travis-ci.org/pydap/pydap.svg)](https://travis-ci.org/pydap/pydap)
[![Python3](https://img.shields.io/badge/python-3-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/pydap.svg?maxAge=2592000?style=plastic)](https://pypi.python.org/pypi/pydap/)
[![Join the chat at https://gitter.im/pydap/pydap](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/pydap/pydap) 

[pydap](https://pydap.github.io/pydap/) is an implementation of the
Opendap/DODS protocol, written from scratch in pure python.  You can
use pydap to access scientific data on the internet without having to
download it; instead, you work with special array and iterable objects
that download data on-the-fly as necessary, saving bandwidth and
time. The module also comes with a robust-but-lightweight Opendap
server, implemented as a WSGI application.


Quickstart
----------

You can install the latest version using
[pip](http://pypi.python.org/pypi/pip). After [installing
pip](http://www.pip-installer.org/en/latest/installing.html) you can
install pydap with this command:

```bash
    $ pip install pydap
```

This will install pydap together with all the required
dependencies. You can now open any remotely served dataset, and pydap
will download the accessed data on-the-fly as needed:

```python

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
```

For more information, please check the documentation on [using pydap
as a client](https://pydap.github.io/pydap/client.html). pydap also
comes with a simple server, implemented as a [WSGI]( http://wsgi.org/)
application. To use it, you first need to install the server and
optionally a data handler:

```bash

    $ pip install pydap[server,handlers.netcdf]
```

This will install support for
[netCDF](http://www.unidata.ucar.edu/software/netcdf/) files; more
[handlers](https://pydap.github.io/pydap/handlers.html) for
different formats are available, if necessary. Now create a directory
for your server data.


To run the server just issue the command:

```bash

    $ pydap --data ./myserver/data/ --port 8001
```

This will start a standalone server running on http://localhost:8001/,
serving netCDF files from ``./myserver/data/``, similar to the test
server at http://test.pydap.org/. Since the server uses the
[WSGI](http://wsgi.org/) standard, it can easily be run behind
Apache. The [server
documentation](https://pydap.github.io/pydap/server.html) has
more information on how to better deploy pydap.

## Documentation

For more information, see [the pydap
documentation](https://pydap.github.io/pydap/).

## Help

If you need any help with pydap, please feel free to send an email to
the [mailing list](http://groups.google.com/group/pydap/)


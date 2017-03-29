News
====

3.2.1
-----

*Release date: 2017-Mar-28*

* PyDAP client fixes
  * Adds workaround to the client when making requests to older ESGF OPENDAP servers
  * Fixes a bug where mechanicalsoup wouldn't its browser
  * Adds handling for values of -NaN
  * Overhauls URS authentication to use the requests library
  * Sets a default charset when connecting to servers that do not
* Packaging fixes
  * Moves gunicorn in to server_extras dependency list
  * Adds test data to the release tarball
* Code base improvements
  * Adds flake8 linting/checking to the code base
  * Improves testing for client authentication
  * Drops support for Python < 2.7
  * Converts internal imports to be explicit relative
* Miscellaneous bug fixes
  * Fixes bug in fix_slices() when `stop` > len
  * Fixes unexpected flattening of sliced arrays (#41)
  * Fixes bug where attributes were not propagated to nested structures (#75)


3.2.0
-----

*Release date: 2016-Dec-01*

* Adds some optimizations to the server for DAP sequences
* Rewrite of the client so that it's now able to stream real time data
* Simplifies the design of handlers, eliminating DAP-related details
  (so that developers can focus only on the data parsing when creating
  new handlers).
* Full test coverage and continuous integration
* Adds support for Python version 3.3 through 3.5
* Adds support for federated authentication through the Earth System
  Grid Federation (ESGF) and NASA User Registration System (URS).
* Fixes HTML response to show all dimensions for BaseType variables

3.1.1
-----

*Release date: 14-Nov-2013*

* Final release done by Roberto De Almeida

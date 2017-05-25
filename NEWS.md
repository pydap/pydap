News
====

3.2.2
-----

*Release date: 2017-May-24*

* Python 3.3 is no longer supported. This is in line with
  other similar projects (Numpy, Xarray, ...) and it preempts the
  expected python 3.3 EOL in September 2017.
* Server improvements
  * Merges pydap.handlers.netcdf into the main code base
  * Adds a lightweight testing/development server
  * Rewrites the server docs to reflect a post-paster world
* Miscellaneous bug fixes
  * Ensures Byte use is consistent with DAP2 standards
  * Fixes client authentication to UK's CEDA
  * Fixes client communcation with ERDDAP servers
  * Fixes regression bug in model.GridType (#43)
  * Fixes bug where the iteration does not replace previous_chunk
  * Fixes bugs in command-line server (#52 and #53)
* Fix mapping scheme for SequenceType (PR #89)
  * Makes all types a mapping and protects the mapping semantics for sequence data
  * Converts dict in StructureType to OrderedDict, changing
    _original_keys handling (#3) and convers test_model.py to pytest
    semantics (#82).
  * Updats docs and docstrings. Added basic automatic
    doctests. Doctests use integers for easy continuous integration
  * 100% test coverage in src/pydap/model.py.
* Various codebase improvements
  * Transition tests from nose to pytest
  * Tests with flake8 on all Python version
* Adds timeout option to open_urls and open_dods


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

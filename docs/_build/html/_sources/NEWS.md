What's New
==========

3.5.2
------

*Release date: 2024-Nov-19*


* Add zenodo badge by @Mikejmnez in https://github.com/pydap/pydap/pull/405
* Update `pre-commit` hooks by @pre-commit-ci in https://github.com/pydap/pydap/pull/408
* Adds newer `python` versions to metadata and tests workflows by @Mikejmnez in https://github.com/pydap/pydap/pull/410
* include `cas-extras` as minimal required dependencies to use of pydap as client only by @Mikejmnez in https://github.com/pydap/pydap/pull/413
* Update documentation, adding info about DAP4 and Constraint Expressions under `Pydap as a Client` by @Mikejmnez in https://github.com/pydap/pydap/pull/414
* Quick patchwork to parse TDS DAP4 responses, with proper warning message to use dap2 instead by @Mikejmnez in https://github.com/pydap/pydap/pull/415



3.5.1
-----

*Release date: 2024-Oct-28*

- DAP4 support:
  * Improve docs description of Constraint Expressions (include shared dimensions) by @Mikejmnez in https://github.com/pydap/pydap/pull/357
  * Set dimensions at `Group` level by @Mikejmnez in https://github.com/pydap/pydap/pull/360
  * Creates method to generate dap objects by @Mikejmnez in https://github.com/pydap/pydap/pull/362
  * serve nc4 data with `Groups` by @Mikejmnez in https://github.com/pydap/pydap/pull/367
  * `get.Dap` objects function (and a fix)  by @Mikejmnez in https://github.com/pydap/pydap/pull/373.
  * Allow repeated dimensions by @Mikejmnez in https://github.com/pydap/pydap/pull/381
  * Removes `GridType` from netcdf handler by @Mikejmnez in https://github.com/pydap/pydap/pull/395
  * Parse attribute elements with atomic types on root by @Mikejmnez in https://github.com/pydap/pydap/pull/403

- Strip down installation of `pydap`:
  - For `client`-only uses do: `pip install pydap`, or `conda install pydap` if using `conda`.
  - If need to use `pydap`'s server do: `pip install "pydap[server,netcdf]"`, or `conda install pydap-server`.

- Other changes:
  * Updates logo file and point to it by @Mikejmnez in https://github.com/pydap/pydap/pull/366
  * Reduced required dependencies to install by @Mikejmnez in https://github.com/pydap/pydap/pull/369
  * update readme by @Mikejmnez in https://github.com/pydap/pydap/pull/375 and https://github.com/pydap/pydap/pull/376
  * Worflows by @Mikejmnez in https://github.com/pydap/pydap/pull/377
  * Docs update by @Mikejmnez in https://github.com/pydap/pydap/pull/378
  * Allow `dds` and `DMR` parser of remote datasets with `Flatten` groups (slashes in name) by @Mikejmnez in https://github.com/pydap/pydap/pull/399
  * change variable to plot and decode by @Mikejmnez in https://github.com/pydap/pydap/pull/383
  * Remove whitespace on ci/env file by @Mikejmnez in https://github.com/pydap/pydap/pull/386
  * Bump mamba-org/setup-micromamba from 1 to 2 by @dependabot in https://github.com/pydap/pydap/pull/384
  * Update pre-commit hooks by @pre-commit-ci in https://github.com/pydap/pydap/pull/387
  * Update README.md by @Mikejmnez in https://github.com/pydap/pydap/pull/396


3.5.0
-----

*Release date: 2024-Aug-16*

- DAP4 Support:
  * New extra argument to `client.open_url` : `protocol='dap2'|'dap4'`. Default is `protocol='dap2'`.
  * Allow escaping of '[' and ']' characters when opening remote datasets with dap4 protocol by @Mikejmnez in https://github.com/pydap/pydap/pull/310
  * Adds a tree method for inspecting data within a pydap dataset by @Mikejmnez in https://github.com/pydap/pydap/pull/324
  * Simplify the Dataset model in DAP4 by @Mikejmnez in https://github.com/pydap/pydap/pull/327
  * correctly parse projections (CEs) with Arrays in DAP4 by @Mikejmnez in https://github.com/pydap/pydap/pull/336
  * Iss339 by @Mikejmnez in https://github.com/pydap/pydap/pull/340
  * Parse NaN attribute values on DMR (DAP4) by @Mikejmnez in https://github.com/pydap/pydap/pull/345
  * correctly define `named dimensions` at `root` level by @Mikejmnez in https://github.com/pydap/pydap/pull/348

- General updates:
  * Tests fix by @jgallagher59701 in https://github.com/pydap/pydap/pull/275
  * Clean up test workflows. by @owenlittlejohns in https://github.com/pydap/pydap/pull/283
  * `Import Mapping` from `collections.abc` by @rbeucher in https://github.com/pydap/pydap/pull/272
  * Allow newer python versions to test on MacOS mimicking Ubuntu workflows by @Mikejmnez in https://github.com/pydap/pydap/pull/293
  * Includes templates for PRs and Issues, fixes broken links in documentation, adds dependabots by @Mikejmnez in https://github.com/pydap/pydap/pull/296
  * Bump `actions/setup-python` from 4 to 5 by @dependabot in https://github.com/pydap/pydap/pull/300
  * Bump `actions/checkout` from 3 to 4 by @dependabot in https://github.com/pydap/pydap/pull/301
  * Removes dependency of `six` (for python 2.7) by @Mikejmnez in https://github.com/pydap/pydap/pull/304
  * `Pydap` now uses `pyproject.toml` by @Mikejmnez in https://github.com/pydap/pydap/pull/307
  * Includes `pre-commit`  by @Mikejmnez in https://github.com/pydap/pydap/pull/309
  * Set up `pre-commit` on github actions by @Mikejmnez in https://github.com/pydap/pydap/pull/312
  * Bump `actions/setup-python` from 3 to 5 by @dependabot in https://github.com/pydap/pydap/pull/316
  * Bump `actions/checkout` from 3 to 4 by @dependabot in https://github.com/pydap/pydap/pull/317
  * Fixes #207: `Pydap` can now use `PasterApp` and serve data  by @Mikejmnez in https://github.com/pydap/pydap/pull/318
  * Include compatibility with Numpy=2.0 @Mikejmnez in https://github.com/pydap/pydap/pull/322
  * Removes deprecation warnings by @Mikejmnez in https://github.com/pydap/pydap/pull/325
  * Point to `main` branch on GH/workflows by @Mikejmnez in https://github.com/pydap/pydap/pull/330
  * add authentication notebook by @Mikejmnez in https://github.com/pydap/pydap/pull/341
  * docs fix by @Mikejmnez in https://github.com/pydap/pydap/pull/342
  * resolve Numpy>1.25 deprecation error by @Mikejmnez in https://github.com/pydap/pydap/pull/343
  * include numpy attributes to BaseType to compute arraysize in bytes (uncompressed) by @Mikejmnez in https://github.com/pydap/pydap/pull/329
  * Modernize the documentation with jupyter-books  by @Mikejmnez in https://github.com/pydap/pydap/pull/337
  * Implicit discovery of entry points by @Mikejmnez in https://github.com/pydap/pydap/pull/346


3.4.0
-----

*Release date: 2023-April-5*

* DAP4/DAS Patch (#278)
  * Fixing a type that was causing DAP4 content to be igested in a DAP2 object with bad results.
  * Retiring tests for Python 3.6 as it is no longer available in ubuntu. Adding tests for Python 3.10 and 3.11
  * Dropped 3.7 and 3.8 from the version matrix
  * test_response_error regex fixed
  * test_response_error fix for 3.10 and 3.9
  * changed python_macro version to 3.9
  * Updated .gitignore for OSX Finder stuff

* Dap4 beta (#271)
  * Initial DAP4 support
  * These changes are useful but do not represent 100% conformance to the DAP4.

3.3.0
-----

*Release date: 2022-Feb-1*

* There are many changes going from 3.2.0 to 3.3.0

  - Merge pull request #259 from pydap/ejh_readme: fixing documentation links in README

  - Merge pull request #258 from pydap/ejh_version: changed version to 3.3.0

  - Merge pull request #253 from pydap/ejh_remove_python_2: initial attempt to remove python 2 support

  - Merge pull request #209 from shreddd/master: Fix to speed up directory listings.

  - Merge pull request #257 from pydap/ejh_macos_2: adding macos to GitHub CI

  - Merge branch 'timeout' of github.com:cskarby/pydap
  - Merge branch 'float_inf' of github.com:d70-t/pydap into ejh_inf

  - Merge pull request #247 from pydap/ejh_warn2: fixed tostring warnings

  - Merge pull request #246 from pydap/ejh_warn: fixed pytest warnings

  - Merge pull request #243 from pydap/ejh_collections: Import ABC from collections.abc instead of collections for Python 3 compatibility (adding more versions of python)

  - Merge pull request #241 from pydap/ejh_t1: adding GitHub actions CI workflow

  - fix pos arg (#225)

  - WIP: add user_charset arg (#223)

  - Add 'default_charset' to open_url, for servers that don't (#222): specify it but serve utf-8

  - client: Bugfix - pass session to server functions
  - self.session was set to None instead of passed session object

  - client: Pass timeout from open_url to server functions as well: Fixes pydap/pydap#220

  - Handle KeyErrors as described in issue #128 (#201)

  - Do not yield faulty DAS lines (#195): Fix #194.
  - `sudo` is no longer needed (#193): https://blog.travis-ci.com/2018-11-19-required-linux-infrastructure-migration

  - Avoid applying scale factor for consistency with dtype (#191)
  - Fix #190.
  - Fix Travis CI (#192)
  - Fix PEP 479
  - Fix PEP8
  - add netcdf handler entry point (#179)
  - minor client doc fixes (#181)
  - adding logo pydap (#178)

  - Merge pull request #177 from tomkralidis/add-tomkralidis-to-contributors

  - Explicitly test client-only installations (solves #120) (#124)
  0 Add a ``verify`` option to ``open_url`` (#112)

  - Add a netcdf4-python interface for testing (#106)
  - Remove serverside functions in devel server (#123)
  - Remove non-existent entry in index (#115)
  - make pydap canonical project name (#174)
  - simplify HTML (#144)
  - Fix gzip compression (#126) (#152)
  - add support for THREDDS Catalog XML (#136) (#138)
  - add support for THREDDS Catalog XML (#136)
  - add pydap.__version__ capability (#133) (#135)

  - Merge pull request #172 from rsignell-usgs/patch-1
  - Create CODE_OF_CONDUCT.md

  - Merge pull request #173 from betodealmeida/fix_ci_35
  - Fix unit tests in Python 3.5

  - Create CODE_OF_CONDUCT.md

  - Merge pull request #161 from flackdl/patch-1
  - Fix bad link in README

  - add LICENSE file (#142) (#143)

  - Handle gzipped responses (Solves #126) (#127)
  - add requests to core dependencies (#145) (#120) (#146)
  - Fixes #121, fixes deprecation warnings and incorporates flake8 changes (#159)
  - Fix title level inconsistency (#117)
  - Closes #116
  - Exclude the Sphinx build directory from sdist (#114)
  - Do not require mock for Python 3.3 or later (#113)
  - `unittest.mock` is available since Python 3.3

  - Merge pull request #34 from laliberte/merging/handlers.csv
  - Merges CSV handler into the main repo

  - Merge branch 'release/3.2.2'
  - Add PasteDeploy as an optional dependency. Fixes #53
  - New way of running a Paste server with Gunicorn. Fixes #52

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

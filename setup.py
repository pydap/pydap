import io
import os
import re
from setuptools import setup, find_packages
import sys

install_requires = [
    'numpy',
    'Webob',
    'Jinja2',
    'docopt',
    'six >= 1.4.0',
    'beautifulsoup4',
    'requests'
]

if sys.version_info < (3, 5):
    install_requires.append('singledispatch')

functions_extras = [
    'gsw==3.0.6',
    'coards'
]

server_extras = [
    'gunicorn',
    'PasteDeploy',
]

docs_extras = [
    'Sphinx',
    'Pygments',
    'sphinx_rtd_theme',
]

cas_extras = [
    'lxml'
]

hdl_netcdf_extras = [
    'netCDF4',
    'ordereddict'
]

# These extras should only contain pure
# testing packages (e.g. pytest, mock, flake8, ...)
tests_extras = [
    'pytest>=3.6',
    'pytest-cov',
    'pytest-attrib',
    'beautifulsoup4',
    'requests-mock',
    'WebTest',
    'flake8',
    'werkzeug',
    'pyopenssl']


testing_extras = (functions_extras + cas_extras + server_extras +
                  hdl_netcdf_extras + tests_extras)

if sys.version_info < (3, 3):
    testing_extras.append('mock')


def read(filename, encoding='utf-8'):
    """read file contents"""
    full_path = os.path.join(os.path.dirname(__file__), filename)
    with io.open(full_path, encoding=encoding) as fh:
        contents = fh.read().strip()
    return contents


def get_package_version():
    """get version from top-level package init"""
    version_file = read('src/pydap/__init__.py')
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


setup(name='pydap',
      version=get_package_version(),
      description="An implementation of the Data Access Protocol.",
      long_description="",
      classifiers=[
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6"
            "Programming Language :: Python :: 3.7"
            # Get strings from
            # http://pypi.python.org/pypi?%3Aaction=list_classifiers
            ],
      keywords='opendap dods dap science data',
      author='Roberto De Almeida',
      author_email='roberto@dealmeida.net',
      maintainer='James Hiebert',
      maintainer_email='james@hiebert.name',
      url='http://pydap.org/',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      zip_safe=False,
      namespace_packages=["pydap", "pydap.responses",
                          "pydap.handlers", "pydap.tests"],
      install_requires=install_requires,
      extras_require={
            'client': [],
            'tests': tests_extras,
            'docs': docs_extras,
            'functions': functions_extras,
            'cas': cas_extras,
            'handlers.netcdf': hdl_netcdf_extras,
            'netcdf': hdl_netcdf_extras,
            'server': server_extras,
            'handlers.netcdf': hdl_netcdf_extras,
            'testing': testing_extras
      },
      test_suite="pydap.tests",
      entry_points="""
            [pydap.handler]
            nc = pydap.handlers.netcdf:NetCDFHandler

            [pydap.response]
            das = pydap.responses.das:DASResponse
            dds = pydap.responses.dds:DDSResponse
            dods = pydap.responses.dods:DODSResponse
            html = pydap.responses.html:HTMLResponse
            asc = pydap.responses.ascii:ASCIIResponse
            ascii = pydap.responses.ascii:ASCIIResponse
            ver = pydap.responses.version:VersionResponse

            [pydap.function]
            bounds = pydap.wsgi.functions:bounds
            mean = pydap.wsgi.functions:mean
            density = pydap.wsgi.functions:density

            [console_scripts]
            pydap = pydap.wsgi.app:main
            dods = pydap.handlers.dap:dump
      """)

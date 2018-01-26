from setuptools import setup, find_packages
import sys

__version__ = '3.2.2'

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

tests_require = (functions_extras + cas_extras + server_extras +
                 hdl_netcdf_extras +
                 ['WebTest',
                  'beautifulsoup4',
                  'flake8'])

testing_extras = tests_require + [
    'pytest>=2.8',
    'pytest-cov',
    'pytest-attrib',
    'requests-mock',
    'requests'
]

if sys.version_info < (3, 3):
    testing_extras.append('mock')

setup(name='Pydap',
      version=__version__,
      description="An implementation of the Data Access Protocol.",
      long_description="",
      classifiers=[
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6"
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
            'functions': functions_extras,
            'testing': testing_extras,
            'docs': docs_extras,
            'tests': tests_require,
            'cas': cas_extras,
            'server': server_extras,
            'handlers.netcdf': hdl_netcdf_extras
      },
      test_suite="pydap.tests",
      entry_points="""
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

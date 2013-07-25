from setuptools import setup, find_packages
import sys, os


__version__ = '3.2'

install_requires = [
    'Numpy',
    'requests',
    'singledispatch',
    'Webob',
    'Jinja2',
    'docopt',
    'gunicorn',
    'PasteDeploy',
    'coards',
    'gsw',
]

if sys.version_info < (2, 7):
    install_requires.append('ordereddict')

docs_extras = [
    'Sphinx',
    'Pygments',
]

tests_require = [
    'WebTest',
    'beautifulsoup4',
]

testing_extras = tests_require + [
    'nose',
    'coverage',
    'virtualenv', # for scaffolding tests
]

if sys.version_info < (2, 7):
    testing_extras.append('unittest2')


setup(name='Pydap',
    version=__version__,
    description="An implementation of the Data Access Protocol.",
    long_description="",
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='opendap dods dap science data',
    author='Roberto De Almeida',
    author_email='roberto@dealmeida.net',
    url='http://pydap.org/',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    namespace_packages=["pydap", "pydap.responses", "pydap.handlers"],
    install_requires=install_requires,
    extras_require = {
        'testing': testing_extras,
        'docs': docs_extras,
    },
    tests_require = tests_require,
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
    """,
)

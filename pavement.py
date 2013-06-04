import string

from paver.easy import *
from paver.setuputils import setup, find_packages, find_package_data
import paver.doctools
import paver.virtual
from paver.release import setup_meta

try:
    from pydap.lib import __version__
except ImportError:
    __version__ = ('unknown',)

options = environment.options
setup(**setup_meta)

options(
    setup=Bunch(
        name='Pydap',
        version='.'.join(str(d) for d in __version__),
        description='Pure Python Opendap/DODS client and server.',
        long_description='''
Pydap is an implementation of the Opendap/DODS protocol, written from
scratch. You can use Pydap to access scientific data on the internet
without having to download it; instead, you work with special array
and iterable objects that download data on-the-fly as necessary, saving
bandwidth and time. The module also comes with a robust-but-lightweight
Opendap server, implemented as a WSGI application.
        ''',
        keywords='opendap dods dap data science climate oceanography meteorology',
        classifiers=filter(None, map(string.strip, '''
            Development Status :: 5 - Production/Stable
            Environment :: Console
            Environment :: Web Environment
            Framework :: Paste
            Intended Audience :: Developers
            Intended Audience :: Science/Research
            License :: OSI Approved :: MIT License
            Operating System :: OS Independent
            Programming Language :: Python
            Topic :: Internet
            Topic :: Internet :: WWW/HTTP :: WSGI
            Topic :: Scientific/Engineering
            Topic :: Software Development :: Libraries :: Python Modules
        '''.split('\n'))),
        author='Roberto De Almeida',
        author_email='rob@pydap.org',
        url='http://pydap.org/',
        license='MIT',

        packages=find_packages(),
        package_data=find_package_data("pydap", package="pydap",
                only_in_packages=False),
        include_package_data=True,
        zip_safe=False,
        namespace_packages=['pydap', 'pydap.responses', 'pydap.handlers', 'pydap.wsgi'],

        test_suite='nose.collector',

        dependency_links=[],
        install_requires=[
            'numpy',
            'httplib2>=0.4.0',
            'Genshi',
            'Paste',
            'PasteScript',
            'PasteDeploy',
        ],
        extras_require={
            'test': ['nose', 'wsgi_intercept'],
            'docs': ['Paver', 'Sphinx', 'Pygments', 'coards'],
            'esgf': ['M2Crypto'],
        },
        entry_points="""
            [pydap.response]
            dds = pydap.responses.dds:DDSResponse
            das = pydap.responses.das:DASResponse
            dods = pydap.responses.dods:DODSResponse
            asc = pydap.responses.ascii:ASCIIResponse
            ascii = pydap.responses.ascii:ASCIIResponse
            ver = pydap.responses.version:VersionResponse
            version = pydap.responses.version:VersionResponse
            help = pydap.responses.help:HelpResponse
            html = pydap.responses.html:HTMLResponse
      
            [paste.app_factory]
            server = pydap.wsgi.file:make_app
      
            [paste.paster_create_template]
            pydap = pydap.wsgi.templates:DapServerTemplate
        """,
    ),
    minilib=Bunch(
        extra_files=['doctools', 'virtual'],
        versioned_name=True
    ), 
    virtualenv=Bunch(
        packages_to_install=['Paste', 'Pydap'],
        script_name='bootstrap.py',
        paver_command_line=None,
        install_paver=True
    ),
    sphinx=Bunch(
        builddir='_build',
    ),
    cog=Bunch(
        includedir='.',
    ),
    deploy=Bunch(
        htmldir = path('pydap.org'),
        bucket = 'pydap.org',
    ),
)


if paver.doctools.has_sphinx:
    @task
    @needs(['cog', 'paver.doctools.html'])
    def html():
        """Build the docs and put them into our package."""
        destdir = path('pydap.org')
        destdir.rmtree()
        builtdocs = path("docs") / options.builddir / "html"
        builtdocs.move(destdir)

    @task
    @needs(['cog', 'paver.doctools.doctest'])
    def doctest():
        pass


if paver.virtual.has_virtualenv:
    @task
    def bootstrap():
        """Build a virtualenv bootstrap for developing paver."""
        paver.virtual._create_bootstrap(options.script_name,
                options.packages_to_install,
                options.paver_command_line,
                options.install_paver)


@task
@needs(['generate_setup', 'setuptools.command.sdist'])
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass


@task
@cmdopts([
    ('username=', 'u', 'Username to use when logging in to the servers')
])
def deploy():
    """Deploy the HTML to the server."""
    import os
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key

    conn = S3Connection()
    bucket = conn.create_bucket(options.bucket)
    bucket.set_acl('public-read')

    for root, dirs, files in os.walk(options.htmldir):
        for file in files:
            path = os.path.join(root, file)
            k = Key(bucket)
            k.key = path[len(options.htmldir)+1:]  # strip pydap.org/
            k.set_contents_from_filename(path)
            k.set_acl('public-read')

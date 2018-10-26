Running a server
================

pydap comes with a lightweight and scalable OPeNDAP server, implemented as a `WSGI <http://wsgi.org/>`_ application. Being a WSGI `application <http://wsgi.org/wsgi/Applications>`_, pydap can run on a variety of `servers <http://wsgi.org/wsgi/Servers>`_, and frameworks including Apache, `Nginx <https://www.nginx.com/>`_, IIS, `uWSGI <https://uwsgi-docs.readthedocs.io/en/latest/>`_, `Flask <http://flask.pocoo.org/>`_ or as a standalone Python process. It can also be seamless combined with different `middleware <http://wsgi.org/wsgi/Middleware_and_Utilities>`_ for authentication/authorization, GZip compression, and much more.

There is no one right way to run pydap server; your application requirements and software stack will inform your deployment decisions. In this chapter we provide a few examples to try and get you on the right track.

In order to distribute your data first you need to install a proper `handler <handlers.html>`_, that will convert the data format to the pydap data model. 

Running standalone
------------------

If you just want to quickly test the pydap server, you can run it as a standalone Python application using the server that comes with `Python Paste <http://pythonpaste.org/>`_ and `gunicorn <http://gunicorn.org/>`_. To run the server, first make sure that you have installed pydap with the server extras dependencies:

.. code-block:: bash

    $ pip install pydap[server]

and then just run the ``pydap`` script that pip installs into your bin directory:

.. code-block:: bash

    $ pydap --data /path/to/my/data/files --port 8080

To change the default directory listing, the help page and the HTML form, you can point a switch to your template directory

.. code-block:: bash

    $ pydap --data /path/to/my/data/files --templates /path/to/my/templates.

The HTML form template is fairly complex, since it contain some application logic and some Javascript code, so be careful to not break anything.

.. _wsgi-application-section:

WSGI Application
----------------

pydap follows the `WSGI specification <https://www.fullstackpython.com/wsgi-servers.html>`_, and most web servers gateways simply require a WSGI callable and a small amount of boiler plate code. pydap provides the ``DapServer`` class which is a WSGI callable located in the ``pydap.wsgi.app`` module. A simple WSGI application script file would be something like this:

.. code-block:: python

    from pydap.wsgi.app import DapServer
    application = DapServer('/path/to/my/data/files')


Flask
-----

The `Flask <http://flask.pocoo.org/>`_ framework simply requires a couple more function calls to spin up an application server. A simple server would looks something like this (your mileage may vary):

.. code-block:: python

    from flask import Flask
    from pydap.wsgi.app import DapServer

    application = DapServer('/path/to/my/data/files')
    app = Flask(__name__)
    app.wsgi_app = application
    app.run('0.0.0.0', 8000)

Apache
------

For a robust deployment you can run pydap with Apache, using `mod_wsgi <http://modwsgi.org/>`_. After `installing mod_wsgi <http://code.google.com/p/modwsgi/wiki/InstallationInstructions>`_, create a sandbox in a directory *outside* your DocumentRoot, say ``/var/www/pydap/``, using `a virtual environment <https://docs.python.org/3/library/venv.html>`_:

.. code-block:: bash

    $ mkdir /var/www/pydap
    $ python3 -m venv /var/www/pydap/env

If you want the sandbox to use your system installed packages (like Numpy, e.g.) you can use the ``--system-site-packages`` flag:

.. code-block:: bash

    $ python3 -m venv --system-site-packages /var/www/pydap/env

Now let's activate the sandbox and install pydap -- this way the module and its dependencies can be isolated from the system libraries:

.. code-block:: bash

    $ source /var/www/pydap/env/bin/activate.sh
    (env)$ pip install pydap

Create a `WSGI script file <http://modwsgi.readthedocs.io/en/develop/user-guides/quick-configuration-guide.html#mounting-the-wsgi-application>`_ somewhere convenient (e.g. /var/www/pydap/server/apache/pydap.wsgi) that reads something like this:

.. code-block:: python

    import site
    # force mod_wsgi to use the Python modules from the sandbox
    site.addsitedir('/var/www/pydap/env/lib/pythonX.Y/site-packages')

    from pydap.wsgi.app import DapServer
    application = DapServer('/path/to/my/data/files')

Now create an entry in your Apache configuration pointing to the ``pydap.wsgi`` file you just edited. To mount the server on the URL ``/pydap``, for example, you should configure it like this:

.. code-block:: apache

        WSGIScriptAlias /pydap /var/www/pydap/server/apache/pydap.wsgi

        <Directory /var/www/pydap/server/apache>
            Order allow,deny
            Allow from all
        </Directory>

This is the file I use for the `test.pydap.org <http://test.pydap.org/>`_ virtualhost:

.. code-block:: apache

    <VirtualHost *:80>
        ServerAdmin rob@pydap.org
        ServerName test.pydap.org

        DocumentRoot /var/www/sites/test.pydap.org/server/data

        <Directory /var/www/sites/test.pydap.org/server/data>
            Order allow,deny
            Allow from all
        </Directory>

        WSGIScriptAlias / /var/www/sites/test.pydap.org/server/apache/pydap.wsgi

        <Directory /var/www/sites/test.pydap.org/server/apache>
            Order allow,deny
            Allow from all
        </Directory>

        ErrorLog /var/log/apache2/test.pydap.org.error.log

        # Possible values include: debug, info, notice, warn, error, crit,
        # alert, emerg.
        LogLevel warn

        CustomLog /var/log/apache2/test.pydap.org.access.log combined
        ServerSignature On
    </VirtualHost>

You can find more information on the `mod_wsgi configuration guide <http://code.google.com/p/modwsgi/wiki/QuickConfigurationGuide>`_. Just remember that pydap is a WSGI application like any other else, so any information on WSGI applications applies to it as well.


uWSGI
-----

`uWSGI <http://projects.unbit.it/uwsgi/>`_ is a "fast, self-healing and developer/sysadmin-friendly application container server coded in pure C" that can run pydap. This is the recommended way to run pydap if you don't have to integrate it with other web applications. Simply install uWSGI, follow the instructions in the last section in order to create a virtualenv and pydap installation:

.. code-block:: bash

    $ mkdir /var/www/pydap
    $ python virtualenv.py /var/www/pydap/env
    $ source /var/www/pydap/env/bin/activate.sh
    (env)$ pip install pydap uWSGI
    (env)$ cd /var/www/pydap

Create a WSGI application file myapp.wsgi :ref:`as above <wsgi-application-section>`

Now create a file in ``/etc/init/pydap.conf`` with the content:

.. code-block:: bash

    description "uWSGI server for pydap"

    start on runlevel [2345]
    stop on runlevel [!2345]

    respawn

    exec /var/www/pydap/env/bin/uwsgi \
        --http-socket 0.0.0.0:80 \
        -H /var/www/pydap/env \
        --master --processes 4 \
        --wsgi-file /var/www/pydap/myapp.wsgi

In order to make it run automatically during boot on Linux you can type:

.. code-block:: bash

    $ sudo initctl reload-configuration


Docker
------

Users have `reported success <https://github.com/pydap/pydap/issues/46>`_ deploying pydap with a docker image built with nginx + uWSGI + Flask (based on https://hub.docker.com/r/tiangolo/uwsgi-nginx-flask/. A full configuration is somewhat beyond the scope of this documentation (since it will depend on your requirements and your software stack), but it is certainly possible.

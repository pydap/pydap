Running a server
================

Pydap comes with a lightweight and scalable OPeNDAP server, implemented as a `WSGI <http://wsgi.org/>`_ application. Being a WSGI `application <http://wsgi.org/wsgi/Applications>`_, Pydap can run on a variety of `servers <http://wsgi.org/wsgi/Servers>`_, including Apache, IIS or even as a standalone Python process. It can also be seamless combined with different `middleware <http://wsgi.org/wsgi/Middleware_and_Utilities>`_ for authentication/authorization, GZip compression, and much more.

In order to distribute your data first you need to install a proper `handler <handlers.html>`_, that will convert the data format to the Pydap data model. 

Running standalone
------------------

If you just want to quickly test the Pydap server, you can run it as a standalone Python application using the server that comes with `Python Paste <http://pythonpaste.org/>`_:

.. code-block:: bash

    $ paster create -t pydap myserver

To run the server just issue the command:

.. code-block:: bash

    $ paster serve ./myserver/server.ini

This will run the server on http://localhost:8001/, serving files from ``./myserver/data/``. By default the server will listen only to local requests, ie, from the same machine. You can change this by editing the ``server.ini`` file; and you can also change the port number, though for ports lower than 1024 you will probably need to run the script as root.

To change the default directory listing, the help page and the HTML form, simply edit the corresponding templates in ``./myserver/templates/``. The HTML form template is fairly complex, since it contain some application logic and some Javascript code, so be careful to not break anything.

Running Pydap with Apache
-------------------------

For a robust deployment you should run Pydap with Apache, using `mod_wsgi <http://modwsgi.org/>`_. After `installing mod_wsgi <http://code.google.com/p/modwsgi/wiki/InstallationInstructions>`_, create a sandbox in a directory *outside* your DocumentRoot, say ``/var/www/pydap/``, using `virtualenv <http://pypi.python.org/pypi/virtualenv>`_:

.. code-block:: bash

    $ mkdir /var/www/pydap
    $ python virtualenv.py /var/www/pydap/env

If you want the sandbox to use your system installed packages (like Numpy, e.g.) you can use the ``--system-site-packages`` flag:

.. code-block:: bash

    $ python virtualenv.py --system-site-packages /var/www/pydap/env

Now let's activate the sandbox and install Pydap -- this way the module and its dependencies can be isolated from the system libraries:

.. code-block:: bash

    $ source /var/www/pydap/env/bin/activate.sh
    (env)$ pip install Pydap

And now we can install the basic server files:

.. code-block:: bash

    (env)$ cd /var/www/pydap
    (env)$ paster create -t pydap server

Now edit the file ``/var/www/pydap/server/apache/pydap.wsgi`` and insert the two following lines in the beginning of the file, forcing mod_wsgi to use the Python modules from the sandbox:

.. code-block:: python

    import site
    site.addsitedir('/var/www/pydap/env/lib/python2.X/site-packages')
    
You'll need to insert the correct path (including Python version) to your sandbox ``site-packages`` directory, of course. After this, your file should look like this:

.. code-block:: python

    import site
    site.addsitedir('/var/www/pydap/env/lib/python2.X/site-packages')

    import os
    from paste.deploy import loadapp

    config = os.path.join(os.path.dirname(__file__), '../server.ini')
    application = loadapp('config:%s' % config)

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

You can find more information on the `mod_wsgi configuration guide <http://code.google.com/p/modwsgi/wiki/QuickConfigurationGuide>`_. Just remember that Pydap is a WSGI application like any other else, so any information on WSGI applications applies to it as well.

Running Pydap with uWSGI
------------------------

`uWSGI <http://projects.unbit.it/uwsgi/>`_ is a "fast, self-healing and developer/sysadmin-friendly application container server coded in pure C" that can run Pydap. This is the recommended way to run Pydap if you don't have to integrate it with other web applications. Simply install uWSGI, follow the instructions in the last section in order to create a virtualenv and Pydap installation:

.. code-block:: bash

    $ mkdir /var/www/pydap
    $ python virtualenv.py /var/www/pydap/env
    $ source /var/www/pydap/env/bin/activate.sh
    (env)$ pip install Pydap uWSGI
    (env)$ cd /var/www/pydap
    (env)$ paster create -t pydap server

Now create a file in ``/etc/init/pydap.conf`` with the content:

.. code-block:: bash

    description "uWSGI server for Pydap"

    start on runlevel [2345]
    stop on runlevel [!2345]

    respawn

    exec /var/www/pydap/env/bin/uwsgi \
        --http-socket 0.0.0.0:80 \
        -H /var/www/pydap/env \
        --master --processes 4 \
        --paste config:/var/www/pydap/server/server.ini

In order to make it run automatically during boot on Linux you can type:

.. code-block:: bash

    $ sudo initctl reload-configuration


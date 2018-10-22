Responses
---------

If handlers are responsible for converting data into the pydap data model, responses to the opposite: the convert from the data model to different representations. The Opendap specification defines a series of standard responses, that allow clients to introspect a dataset by downloading metadata, and later download data for the subset of interest. These standard responses are the DDS (Dataset Descriptor Structure), the DAS (Dataset Attribute Structure) and the DODS response.

Apart from these, there are additional non-standard responses that add functionality to the server. The ASCII response, for example, formats the data as ASCII for quick visualization on the browser; the HTML response builds a form from which the user can select a subset of the data.

Here is an example of a minimal pydap response that returns the attributes of the dataset as JSON:

.. code-block:: python

    from simplejson import dumps

    from pydap.responses.lib import BaseResponse
    from pydap.lib import walk

    class JSONResponse(BaseResponse):
        def __init__(self, dataset):
            BaseResponse.__init__(self, dataset)
            self.headers.append(('Content-type', 'application/json'))

        @staticmethod
        def serialize(dataset):
            attributes = {}
            for child in walk(dataset):
                attributes[child.id] = child.attributes

            if hasattr(dataset, 'close'):
                dataset.close()

            return [dumps(attributes)]

This response is mapped to a specific extension defined in its entry point:

.. code-block:: ini

    [pydap.response]
    json = path.to.my.response:JSONResponse

In this example the response will be called when the ``.json`` extension is appended to any dataset.

The most important method in the response is the ``serialize`` method, which is responsible for serializing the dataset into the external format. The method should be a generator or return a list of strings, like in this example. Note that the method is responsible for calling ``dataset.close()``, if available, since some handlers use this for closing file handlers or database connections.

One important thing about the responses is that, like handlers, they are also WSGI applications. WSGI applications should return an iterable when called; usually this is a list of strings corresponding to the output from the application. The ``BaseResponse`` application, however, returns a special iterable that contains both the ``DatasetType`` object and its serialization function. This means that WSGI middleware that manipulate the response have direct access to the dataset, avoiding the need for deserialization/serialization of the dataset in order to change it.

Here is a simple example of a middleware that adds an attribute to a given dataset:

.. code-block:: python

    from webob import Request

    from pydap.model import *
    from pydap.handlers.lib import BaseHandler
    
    class AttributeMiddleware(object):

        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            # say that we want the parsed response
            environ['x-wsgiorg.want_parsed_response'] = True

            # call the app with the original request and get the response
            req = Request(environ)
            res = req.get_response(self.app)

            # get the dataset from the response and set attribute
            dataset = res.app_iter.x_wsgiorg_parsed_response(DatasetType)
            dataset.attributes['foo'] = 'bar'

            # return original response
            response = BaseHandler.response_map[ environ['pydap.response'] ]
            responder = response(dataset)
            return responder(environ, start_response)

The code should actually do more bookkeeping, like checking if the dataset can be retrieved from the response or updating the ``Content-Length`` header, but I wanted to keep it simple. pydap comes with a WSGI middleware for handling server-side functions (``pydap.wsgi.ssf``) that makes heavy use of this feature. It works by removing function calls from the request, fetching the dataset from the modified request, applying the function calls and returning a new dataset.

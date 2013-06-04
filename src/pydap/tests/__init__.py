def requests_intercept(app, location):
    """
    Intercept WSGI requests and pass them to `webtest.TestApp`.

    """
    def new_get(url, **kwargs):
        path = url[len(location):]
        response = app.get('/%s' % path)
        return MockResponse(response)
    return new_get


class MockResponse(object):
    """
    Return a fake requests response.

    This class converts a webtest response to a requests response. It 
    implements only the methods used by the Pydap client.

    """
    def __init__(self, response):
        self.response = response

        self.text = response.body
        self.content = response.body

    def raise_for_status(self):
        pass

    def iter_content(self, blocksize):
        return iter(self.content)


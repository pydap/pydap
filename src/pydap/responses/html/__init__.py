"""HTML DAP response

This is a simple HTML response that allows that to be analysed on the browser.
The user can select a subset of the data and download in different formats.

"""

from jinja2 import Environment, PackageLoader, ChoiceLoader, TemplateNotFound

from pydap.responses.lib import BaseResponse
from pydap.lib import __version__


class HTMLResponse(BaseResponse):

    """A simple HTML response for browsing and downloading data."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ("Content-description", "dods_form"),
            ("Content-type", "text/plain; charset=utf-8"),
        ])

        # our default environment; we need to include the base template from
        # pydap as well since our template extends it
        loaders = [
            PackageLoader("pydap", "responses/html/templates"),
            PackageLoader("pydap", "wsgi/templates"),
        ]
        self.env = Environment(loader=ChoiceLoader(loaders))
        print self.env.list_templates()

    def __call__(self, environ, start_response):
        # check if the server has specified a render environment
        try:
            env = environ["pydap.jinja2.environment"]
            template = env.get_template("html.html")
        except (KeyError, TemplateNotFound):
            template = self.env.get_template("html.html")

        return Response(
            body=template.render(context),
            content_type="text/html",
            charset="utf-8")

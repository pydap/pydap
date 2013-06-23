"""HTML DAP response

This is a simple HTML response that allows that to be analysed on the browser.
The user can select a subset of the data and download in different formats.

"""

from jinja2 import Environment, PackageLoader, ChoiceLoader, TemplateNotFound
from webob import Request, Response
from webob.dec import wsgify

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
        self.loaders = [
            PackageLoader("pydap", "responses/html/templates"),
            PackageLoader("pydap", "wsgi/templates"),
        ]

    @wsgify
    def __call__(self, req):
        # check if the server has specified a render environment; if it has, 
        # make a copy and add our loaders to it
        if "pydap.jinja2.environment" in req.environ:
            env = req.environ["pydap.jinja2.environment"].overlay()
            env.loader = ChoiceLoader([env.loader] + self.loaders)
        else:
            env = Environment(loader=self.loaders)
        template = env.get_template("html.html")

        tokens = req.path_info.split("/")[1:]
        breadcrumbs = [{
            "url": "/".join([req.application_url] + tokens[:i+1]),
            "title": token,
        } for i, token in enumerate(tokens) if token]

        context = {
            "root": req.application_url,
            "location": req.path_url,
            "breadcrumbs": breadcrumbs,
            "dataset": self.dataset,
            "version": __version__,
        }

        return Response(
            body=template.render(context),
            content_type="text/html",
            charset="utf-8")

"""Fundamental functions for pydap responses.

pydap responses are WSGI applications that convert a dataset into different
representations, like the DDS, DAS and DODS responses described in the DAP
specification.

In addition to the official responses, pydap also has responses that generate
KML, WMS, JSON, etc., installed as third-party Python packages that declare the
"pydap.response" entry point.

"""

from importlib.metadata import entry_points

from ..lib import __version__
from ..model import DatasetType


def load_responses():
    """Load all available responses from the system, returning a dictionary."""
    eps = entry_points(group="pydap.response")
    Rs = [r for r in eps if r.module[:5] == "pydap"]
    nRs = [r for r in eps if r.module[:5] != "pydap"]
    base_dict = dict((r.name, r.load()) for r in Rs)

    opts_dict = dict((r.name, r.load()) for r in nRs)
    base_dict.update(opts_dict)
    return base_dict


class BaseResponse(object):
    """A base class for pydap responses.

    A pydap response is a WSGI application that converts a dataset into any
    other representation. The most know responses are the DDS, DAS and DODS
    responses from the DAP spec, which describe the dataset structure,
    attributes and data, respectively.

    According to the WSGI specification, WSGI applications must returned an
    iterable object when called. While this is traditionally a list of strings
    representing an HTML response, this is not the case for pydap. pydap will
    return an object (the response instance itself), which is an iterable that
    yields the corresponding output (a DDS response, eg).

    In practice, this means that the generation of the response is delayed
    until the data is being sent to the client. But since the response object
    also carries the original dataset, this means it's possible to write WSGI
    middleware that modifies the dataset directly. A WSGI middleware can add
    additional metadata to a dataset, eg, by adding attributes directly to the
    dataset object, without having to generate a new response.

    """

    def __init__(self, dataset):
        self.dataset = dataset
        self.headers = [
            ("OPeNDAP-Server", "pydap/%s" % __version__),
        ]

    def __call__(self, environ, start_response):
        start_response("200 OK", self.headers)
        return self

    def x_wsgiorg_parsed_response(self, type):
        r"""Avoid serialization of datasets.

        This function will return the contained dataset if ``type`` is a
        ``pydap.model.DatasetType`` object. Based on this proposal:

            http://wsgi.readthedocs.org/en/latest/specifications/ \
                    avoiding_serialization.html

        """
        if type is DatasetType:
            return self.dataset

    def __iter__(self):
        raise NotImplementedError("Subclasses must implement __iter__")

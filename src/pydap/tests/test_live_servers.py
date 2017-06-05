from pydap.client import open_url
from pydap.model import DatasetType

url = 'http://geoport-dev.whoi.edu/thredds/dodsC/estofs/atlantic'


def test_open():
    dataset = open_url(url)
    assert(isinstance(dataset, DatasetType))

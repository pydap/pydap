import unittest

import numpy as np
from pydap.parsers import parse_ce
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import D1


class TestConstrain(unittest.TestCase):
    def test_no_ce(self):
        data = np.rec.fromrecords(
                D1.Drifters.data.tolist(), names=D1.Drifters.keys())

        projection, selection = parse_ce('')
        dataset = BaseHandler(D1).parse(projection, selection)
        np.testing.assert_array_equal(data, dataset.Drifters.data)

    def test_filtering(self):
        data = np.rec.fromrecords(
                D1.Drifters.data.tolist(), names=D1.Drifters.keys())
        filtered = data[data['longitude'] < 999]

        projection, selection = parse_ce('Drifters.longitude<999')
        dataset = BaseHandler(D1).parse(projection, selection)
        np.testing.assert_array_equal(filtered, dataset.Drifters.data)

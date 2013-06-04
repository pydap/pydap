import unittest                                                                 

import numpy as np
                                                                                
from pydap.model import *                                                       
from pydap.parsers import parse_ce
from pydap.handlers.lib import BaseHandler


DATA = zip(
    [("This is a data test string (pass %d)." % (1+i*2)) for i in range(5)],
    [("This is a data test string (pass %d)." % (i*2)) for i in range(5)],
    [1000.0, 999.95, 999.80, 999.55, 999.20],
    [999.95, 999.55, 998.75, 997.55, 995.95])
                                 
                                                                                
class Test_constrain(unittest.TestCase):                                            
    def setUp(self):
        # create dataset
        self.dataset = DatasetType('EOSDB.DBO')                                 
        self.dataset['Drifters'] = SequenceType('Drifters')                     
        self.dataset['Drifters']['instrument_id'] = BaseType('instrument_id')
        self.dataset['Drifters']['location'] = BaseType('location')
        self.dataset['Drifters']['latitude'] = BaseType('latitude')
        self.dataset['Drifters']['longitude'] = BaseType('longitude')

        self.dataset.Drifters.data = np.rec.fromrecords(
            DATA, names=self.dataset.Drifters.keys())

    def test_no_ce(self):
        data = np.rec.fromrecords(DATA, names=self.dataset.Drifters.keys())

        projection, selection = parse_ce('')
        dataset = BaseHandler(self.dataset).parse(projection, selection)
        np.testing.assert_array_equal(data, dataset.Drifters.data)

    def test_filtering(self):
        data = np.rec.fromrecords(DATA, names=self.dataset.Drifters.keys())
        filtered = data[ data['longitude'] < 999 ]

        projection, selection = parse_ce('Drifters.longitude<999')
        dataset = BaseHandler(self.dataset).parse(projection, selection)
        np.testing.assert_array_equal(filtered, dataset.Drifters.data)

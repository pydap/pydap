import unittest                                                                 

import numpy as np
from webtest import TestApp
                                                                                
from pydap.model import *                                                       
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url
from pydap.tests import requests_intercept
                                 
                                                                                
class Test_quote(unittest.TestCase):                                            
    def setUp(self):
        # create dataset
        dataset = DatasetType('test')
        dataset['foo%5B'] = BaseType('foo[', np.array(1))

        # create WSGI app
        self.app = TestApp(BaseHandler(dataset))

    def test_children(self):
        dataset = DatasetType('test')

        with self.assertRaises(KeyError):
            dataset['foo['] = BaseType('foo[')

        var = BaseType('foo[')
        dataset[var.name] = var

    def test_dds(self):
        self.assertEqual(self.app.get('/.dds').body,
            """Dataset {
    Int32 foo%5B;
} test;
""")

    def test_client(self):
        import requests
        requests.old_get = requests.get
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')

        dataset = open_url('http://localhost:8001/')
        self.assertEqual(dataset['foo%5B'].name, 'foo%5B')
        self.assertEqual(dataset['foo%5B'][0], 1)

        requests.get = requests.old_get

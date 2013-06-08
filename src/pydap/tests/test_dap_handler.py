import unittest                                                                 

import numpy as np
from webtest import TestApp                                                     
import requests                                                                 
                                                                                
from pydap.model import *                                                       
from pydap.handlers.lib import BaseHandler                                      
from pydap.client import open_url
from pydap.tests import requests_intercept
from pydap.tests.datasets import rain


class TestDapHandler(unittest.TestCase):
    def setUp(self):                                                            
        # create WSGI app                                                       
        self.app = TestApp(BaseHandler(rain))
                                                                                
        # intercept HTTP requests                                               
        self.requests_get = requests.get                                        
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')   
                                                                                
    def tearDown(self):                                                         
        requests.get = self.requests_get   

    def test_Predefined_Projection(self):
        dataset = open_url('http://localhost:8001/?rain[0]')
        self.assertEqual(dataset.rain.array.shape, (1,3))

"""
This is an example of a Dapper-compliant dataset.

    http://www.ifremer.fr/oceanotron/OPENDAP/ArgoNetCDFToTrajectory.dds

"""
import unittest                                                                 

import numpy as np
from webtest import TestApp
import requests
                                                                                
from pydap.model import *                                                       
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url
from pydap.tests import requests_intercept

                                                                                
class Test_Dapper(unittest.TestCase):                                            
    def setUp(self):
        # create dataset
        ### XXX create our own dataset here
        return
        self.dataset = open_url(
            "http://www.ifremer.fr/oceanotron/OPENDAP/ArgoNetCDFToTrajectory")

    def test_parse(self):
        return
        self.assertEqual(self.dataset.keys(), 
                ['location', 'constrained_ranges', 'response_metadata'])

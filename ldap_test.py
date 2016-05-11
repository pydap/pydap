
# Set up PyDAP to use the URS request() function

from pydap.util.urs import install_basic_client

import logging
logging.basicConfig(filename='urs_test.log',level=logging.DEBUG)

install_basic_client('130.56.244.153','tesla', 'password')

from pydap.client import open_url

d = open_url('https://130.56.244.153/opendap/data/nc/coads_climatology.nc')

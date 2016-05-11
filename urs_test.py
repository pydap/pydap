
# Set up PyDAP to use the URS request() function

from pydap.util.urs import install_basic_client

import logging
logging.basicConfig(filename='urs_test.log',level=logging.DEBUG)

install_basic_client()

from pydap.client import open_url

d = open_url('https://52.1.74.222/opendap/data/hdf4/S3096277.HDF')

import os
from paste.deploy import loadapp

config = os.path.join(os.path.dirname(__file__), '../server.ini')
application = loadapp('config:%s' % config)

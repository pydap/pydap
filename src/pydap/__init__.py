'''
Declare the namespace ``pydap`` here.
'''

from pkg_resources import get_distribution

__import__('pkg_resources').declare_namespace(__name__)

__version__ = get_distribution("pydap").version

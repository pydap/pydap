import re
import ast
import operator

from pydap.parsers import SimpleParser
from pydap.model import *
from pydap.lib import walk


atomic = ('byte', 'int', 'uint', 'int16', 'uint16', 'int32', 'uint32', 'float32', 'float64', 'string', 'url')


class DASParser(SimpleParser):
    def __init__(self, das):
        super(DASParser, self).__init__(das, re.IGNORECASE | re.VERBOSE | re.DOTALL)

    def consume(self, regexp):
        """
        Ignore white space when consuming tokens.

        """
        token = super(DASParser, self).consume(regexp)
        self.buffer = self.buffer.lstrip()
        return token

    def parse(self):
        out = {}
        self.consume('attributes')
        self.container(out)
        return out

    def container(self, target):
        self.consume('{')
        while not self.peek('}'):
            if self.peek('[^\s]+').lower() in atomic:
                name, values = self.attribute()
                target[name] = values
            else:
                name = self.consume('[^\s]+')
                target[name] = {}
                self.container(target[name])
        self.consume('}')

    def attribute(self):
        type = self.consume('[^\s]+')
        name = self.consume('[^\s]+')

        values = []
        while not self.peek(';'):
            value = self.consume(
                    r'''
                        ""          # empty attribute
                        |           # or
                        ".*?[^\\]"  # from quote up to an unquoted quote
                        |           # or
                        [^;,]+      # up to semicolon or comma 
                        '''
                    )
            
            if type.lower() in ['string', 'url']:
                value = str(value).strip('"')
            elif value.lower() in ['nan', 'nan.']:
                value = float('nan')
            else:
                value = ast.literal_eval(value)

            values.append(value)
            if self.peek(','):
                self.consume(',')

        self.consume(';')

        if len(values) == 1:
            values = values[0]

        return name, values


def parse_das(das):
    """
    Parse the DAS into nested dictionaries.

    """
    return DASParser(das).parse()


def add_attributes(dataset, attributes):
    """
    Add attributes from a parsed DAS to a dataset.

    """
    dataset.attributes['NC_GLOBAL'] = attributes.get('NC_GLOBAL', {})
    dataset.attributes['DODS_EXTRA'] = attributes.get('DODS_EXTRA', {})

    # add attributes that don't belong to any child
    for k, v in attributes.items():
        if k not in dataset:
            dataset.attributes[k] = v

    for var in walk(dataset):
        # attributes can be flat, eg, "foo.bar" : {...}
        if var.id in attributes:
            var.attributes.update(attributes[var.id])
        # or nested, eg, "foo" : { "bar" : {...} }
        try:
            var.attributes.update(
                    reduce(operator.getitem, [attributes] + var.id.split('.')))
        except KeyError:
            pass

    return dataset



if __name__ == '__main__':
    import sys
    import pprint
    import requests

    pprint.pprint(parse_das(requests.get(sys.argv[1]).text))

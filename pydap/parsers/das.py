import re
import array
import operator

import numpy

from pydap.parsers import SimpleParser
from pydap.model import *
from pydap.util.safeeval import expr_eval

atomic_types = ('byte', 'int', 'uint', 'int16', 'uint16', 'int32',
        'uint32', 'float32', 'float64', 'string', 'url', 'alias')


class DASParser(SimpleParser):
    def __init__(self, das, dataset):
        SimpleParser.__init__(self, das, re.IGNORECASE | re.VERBOSE | re.DOTALL)
        self.das = das
        self.dataset = dataset

    def consume(self, regexp):
        token = SimpleParser.consume(self, regexp)
        self.buffer = self.buffer.lstrip()
        return token

    def parse(self):
        self._target = self.dataset

        self.consume('attributes')
        self.consume('{')
        while not self.peek('}'):
            self._attr_container()
        self.consume('}')
        
        return self.dataset

    def _attr_container(self):
        if self.peek('\w+').lower() in atomic_types:
            name, values = self._attribute()
            self._target.attributes[name] = values
        else:
            self._container()

    def _container(self):
        name = self.consume('[\w_\.%-\/]+')
        self.consume('{')

        if '.' in name:
            # Get new target.
            names = name.split('.')
            target = self._target
            d = [target] + names
            try:
                self._target = reduce(operator.getitem, d)
            except (KeyError, TypeError):
                pass

            # Get attributes.
            while not self.peek('}'):
                self._attr_container()
            self.consume('}')

            # Revert to old target.
            self._target = target

        elif isinstance(self._target, StructureType) and name in self._target:
            target = self._target
            self._target = target[name]

            # Get attributes.
            while not self.peek('}'):
                self._attr_container()
            self.consume('}')

            # Revert to old target.
            self._target = target

        else:
            self._target.attributes[name] = self._metadata()
            self.consume('}')

    def _metadata(self):
        output = {}
        while not self.peek('}'):
            if self.peek('\w+').lower() in atomic_types:
                name, values = self._attribute()
                output[name] = values
            else:
                name = self.consume('[\w%]+')
                self.consume('{')
                output[name] = self._metadata()
                self.consume('}')
        return output

    def _attribute(self):
        type_ = self.consume('\w+')
        name = self.consume('[^\s]+')

        values = []

        # One attribute for MLS data needs special handling since it breaks the
        # parser (doesn't meet the DAP 2.0 standard):
        if type_.lower() in ['string'] and name == 'PCF1':
            endstrindx = self.buffer.index('";')
            value = self.buffer[1:endstrindx]
            self.buffer = self.buffer[endstrindx+1:]
            self.consume(';')
            return name, value

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
            
            if type_.lower() in ['string', 'url']:
                value = expr_eval(repr(value))
                value = value.strip('"')
            elif type_.lower() == 'alias':
                # Support for Alias is not documented in the DAP spec. I based
                # this on the Java documentation from the OPeNDAP website at:
                # http://www.opendap.org/api/javaDocs/dods/dap/Alias.html

                # Check if we should start from the root dataset or from
                # the current item.
                if value.startswith('.'):
                    tokens = value[1:].split('.')
                    target = self.dataset
                else:
                    tokens = value.split('.')
                    target = self._target

                # Run over tokens to get the value.
                for token in tokens:
                    if (isinstance(target, StructureType) and
                            token in target):
                        value = target = target[token]
                    else:
                        value = target = target.attributes.get(token)
            else:
                if value.lower() in ['nan', 'nan.']:
                    value = numpy.NaN
                else:
                    # Convert to proper type. This is specially important for floats,
                    # since this preserves the resolution even though Python has no
                    # difference between float 32 vs. 64.
                    dtype = {'float64': 'd',
                             'float32': 'f',
                             'int32'  : 'l',
                             'int16'  : 'h',
                             'uint32' : 'L',
                             'uint16' : 'H',
                             'byte'   : 'B'}[type_.lower()]
                    if dtype in ['d', 'f']:
                        value = array.array(dtype, [float(value)])[0]
                    else:
                        value = expr_eval(value)
                        try:
                            value = int(value)
                        except OverflowError:
                            value = long(value)

            values.append(value)
            if self.peek(','):
                self.consume(',')

        self.consume(';')

        if len(values) == 1:
            values = values[0]

        return name, values

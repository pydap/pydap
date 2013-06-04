import re


class SimpleParser(object):
    def __init__(self, input, flags=0):
        self.buffer = input
        self.flags = flags

    def peek(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
        else:
            token = ''
        return token

    def consume(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
            self.buffer = self.buffer[len(token):]
        else:
            raise Exception("Unable to parse token: %s" % self.buffer[:10])
        return token

    def tokenize(self, regexps):
        while self:
            for regexp in regexps:
                try:
                    token = self.consume(regexp)
                    yield token
                    break
                except:
                    pass
            else:
                raise Exception("Unable to parse token: %s" % self.buffer[:10])

    def __nonzero__(self):
        return len(self.buffer)

# http://svn.pythonpaste.org/Paste/TemplateProposal/

import os


class TemplateNotFound(Exception):
    pass


class StringTemplateRenderer(object):
    name = 'string.Template'
    output_types = []

    def __init__(self, options, loader):
        self.options = options
        self.loader = loader

    def render(self, template_object, variables,
               fragment=False, output_format=None,
               output_type='unicode'):
        if output_type != 'unicode':
            raise ValueError(
                "Bad output_type: %r" % output_type)
        self.compile(template_object)
        return template_object.native.substitute(variables)

    def compile(self, template_object):
        import string
        s = template_object.unicode_contents()
        template_object.native = string.Template(s)


class MakoRenderer(object):
    name = 'mako'
    output_types = []

    def __init__(self, options, loader):
        self.options = options
        self.loader = loader

    def render(self, template_object, variables,
               fragment=False, output_format=None,
               output_type='unicode'):
        if output_type != 'unicode':
            raise ValueError(
                "Bad output_type: %r" % output_type)
        self.compile(template_object)
        return template_object.native.render(**variables)

    def compile(self, template_object):
        from mako.template import Template
        template_object.native = Template(filename=template_object.filename)


class GenshiRenderer(object):
    name = 'genshi'
    output_types = []

    def __init__(self, options, loader):
        self.options = options
        self.loader = loader

    def render(self, template_object, variables,
               fragment=False, output_format=None,
               output_type='unicode'):
        if output_type != 'unicode':
            raise ValueError(
                "Bad output_type: %r" % output_type)
        self.compile(template_object)
        stream = template_object.native.generate(**variables)
        if 'xml' in output_format:
            return stream.render('xml')
        else:
            return stream.render('html', doctype='html')

    def compile(self, template_object):
        from genshi.template import MarkupTemplate
        f = template_object.open()
        template_object.native = MarkupTemplate(f)


class FileSource(object):

    native = None
    # Ideally this would be picked up from the OS somehow:
    default_encoding = 'utf8'
    real_name = None

    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
        self.real_name = filename
        self.mtime = None
        
    def open(self):
        if self.mtime is None:
            self.mtime = os.path.getmtime(self.filename)
        return open(self.filename, 'rb')

    def unicode_contents(self):
        return self.str_contents().decode(self.default_encoding)

    def str_contents(self):
        f = self.open()
        try:
            return f.read()
        finally:
            f.close()


class FileLoader(object):

    def __init__(self, base_directory):
        self.base_directory = base_directory

    def __call__(self, template_name, relative_to_template=None):
        if isinstance(template_name, FileSource):
            mtime = template_name.mtime
            if mtime is None:
                # It hasn't even been opened, so it must not be out of date
                return template_name
            cur_mtime = os.path.getmtime(template_name.filename)
            if mtime >= cur_mtime:
                return template_name
            # Not up-to-date
            template_name = template_name.name
            # template_name.name is an absolute name
            relative_to_template = None
        template_name = template_name.lstrip('/\\')
        template_name = template_name.replace(os.path.sep, '/')
        template_name = os.path.normpath(template_name)
        if relative_to_template is not None:
            template_name = os.path.join(
                os.path.dirname(relative_to_template), template_name)
        filename = os.path.join(self.base_directory, template_name)
        if not os.path.exists(filename):
            raise TemplateNotFound(
                "No template in %s (looked in %s)"
                % (template_name, filename))
        return FileSource(template_name, filename)


class StringSource(object):

    native = None
    default_encoding = 'utf-8'
    real_name = None

    def __init__(self, name, template):
        self.real_name = self.name = name
        self.template = template

    def open(self):
        from StringIO import StringIO
        return StringIO(self.template)

    def unicode_contents(self):
        return self.template.decode(self.default_encoding)

    def str_contents(self):
        return self.template


class StringLoader(dict):

    def __call__(self, template_name, relative_to_template=None):
        template = self[template_name]
        return StringSource(template_name, template)

"""
HTML DAP response.

This is a simple HTML response, building a form to download data
in ASCII format. The response builds the HTML page and redirects
the user to the proper response (ASCII, usually) when a POST is
done.

"""

__author__ = "Roberto De Almeida <rob@pydap.org>"

from pkg_resources import iter_entry_points
from paste.request import construct_url, parse_formvars
from paste.httpexceptions import HTTPSeeOther, HTTPBadRequest

from pydap.lib import __version__
from pydap.util.template import GenshiRenderer, StringLoader
from pydap.responses.dds import dispatch as dds_dispatch
from pydap.responses.lib import BaseResponse


COMMON_RESPONSES = ['dds', 'das', 'dods', 'asc', 'ascii', 'html', 'ver', 'version', 'help']


DEFAULT_TEMPLATE = """<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:py="http://genshi.edgewall.org/">
    <py:def function="attributes(attrs)">
        <dl py:if="attrs" class="attributes">
            <py:for each="k, v in attrs.items()">
                <dt>${k}</dt>
                <dd py:choose="">
                    <py:when test="isinstance(v, dict)">${attributes(v)}</py:when>
                    <py:otherwise>${v}</py:otherwise>
                </dd>
            </py:for>
        </dl>
    </py:def>

    <div py:def="children(var)" class="children">
        <fieldset py:for="child in var.walk()">
            <legend>${child.name}</legend>

            <?python
                from pydap.model import *
            ?>
            <py:choose test="">
                <p py:when="isinstance(child, SequenceType)" class="filter">
                    <select class="var1" name="var1_${child.id}[0]" id="var1_${child.id}[0]">
                        <option value="--" selected="selected">--</option>
                        <option py:for="grandchild in child.walk()" value="${grandchild.id}">${grandchild.id}</option>
                    </select>
                    <select class="op" name="op_${child.id}[0]" id="op_${child.id}[0]">
                        <option value="%3D" selected="selected">=</option>
                        <option value="%21%3D">!=</option>
                        <option value="%3C">&lt;</option>
                        <option value="%3C%3D">&lt;=</option>
                        <option value="%3E">&gt;</option>
                        <option value="%3E%3D">&gt;=</option>
                        <option value="%3D%7E">=~</option>
                    </select>
                    <input type="text" name="var2_${child.id}[0]" id="var2_${child.id}[0]" value="" class="var2" />
                </p>
                <div py:when="isinstance(child, (BaseType, GridType))">
                    <p><input type="checkbox" name="${child.id}" id="${child.id}" /><label for="${child.id}">Retrieve this variable at indices:</label></p>
                    <?python 
                        dimensions = child.dimensions or ['dim_%id' % j for j in range(len(child.shape))]
                    ?>
                    <div py:for="i in range(len(child.shape))">
                        <label for="${child.id}[${i}]">${dimensions[i]}</label>:<br />
                        <input type="text" name="${child.id}[${i}]" id="${child.id}[${i}]" value="0:1:${child.shape[i]-1}" /><br />
                    </div>
                </div>
            </py:choose>

            ${attributes(child.attributes)}
            ${children(child)}
        </fieldset>
    </div>

    <head>
        <title>Pydap server: ${dataset.name}</title>

        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    </head>

    <body>
        <div id="main">
            <h1>Download data from <code>${dataset.name}</code></h1>

            <!-- Global attributes -->
            <hr />
            <h2>Global attributes</h2>
            ${attributes(dataset.attributes)}

            <hr />
            <form id="dods_form" method="post" action="${location}">
                <!-- Dataset variables -->
                ${children(dataset)}

                <p><input type="submit" id="submit" value="Download data" /> as 
                <select id="response" name="response">
                    <option value="ascii" selected="selected">ASCII</option>
                    <option py:for="response in responses" value="$response">$response</option>
                </select>
                <br /><input type="reset" value="Reset" /></p>
            </form>

            <hr />
            <p><em><a href="http://pydap.org/">pydap/$version</a></em> &copy; Roberto De Almeida</p>
        </div>
    </body>
</html>"""


class HTMLResponse(BaseResponse):

    renderer = GenshiRenderer(
            options={}, loader=StringLoader( {'html.html': DEFAULT_TEMPLATE} ))

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
                ('Content-description', 'dods_form'),
                ('Content-type', 'text/html'),
                ])

    def __call__(self, environ, start_response):
        # If we came from a post, parse response and redirect to ascii.
        if environ['REQUEST_METHOD'] == 'POST':
            # Parse POST and redirect to proper response.
            form = parse_formvars(environ)
            projection, selection = [], []
            for k in form:
                # Selection.
                if k.startswith('var1') and form[k] != '--':
                    name = k[5:]
                    sel = '%s%s%s' % (form[k], form['op_%s' % name], form['var2_%s' % name])
                    selection.append(sel)
                # Projection.
                if form[k] == 'on':
                    var = [k]
                    i = 0
                    while '%s[%d]' % (k, i) in form:
                        var.append('[%s]' % form[ '%s[%d]' % (k, i) ])
                        i += 1
                    var = ''.join(var)
                    if var not in projection:
                        projection.append(var)

            projection = ','.join(projection)
            selection = '&'.join(selection)
            query = projection + '&' + selection
            
            # Get current location.
            location = construct_url(environ, with_query_string=False)

            # Empty queries SHOULD NOT return everything, because this
            # means the user didn't select any variables.
            if not query.rstrip('?&'):
                app = HTTPBadRequest('You did not select any variables.')
            else:
                # Replace html extension for ascii and redirect.
                response = form['response']
                redirect = '%s.%s?%s' % (location[:-5], response, query)
                app = HTTPSeeOther(redirect)
            return app(environ, start_response)
        else:
            self.serialize = self._render(environ)
            return BaseResponse.__call__(self, environ, start_response)

    def _render(self, environ):
        def serialize(dataset):
            location = construct_url(environ, with_query_string=False)
            base = location[:location.rfind('/')]
            context = {
                'environ': environ,
                'root': construct_url(environ, with_query_string=False, with_path_info=False, script_name='').rstrip('/'),
                'base': base,
                'location': location,
                'dataset': dataset,
                'responses': dict([(r.name, getattr(r.load(), '__description__', r.name))
                        for r in iter_entry_points('pydap.response')
                        if r.name not in COMMON_RESPONSES]),
                'version': '.'.join(str(i) for i in __version__),
            }
            renderer = environ.get('pydap.renderer', self.renderer)
            template = renderer.loader('html.html')
            output = renderer.render(template, context, output_format='text/html')
            if hasattr(dataset, 'close'): dataset.close()
            return [output.encode('utf-8')]
        return serialize

from webob import Request, Response

from pydap.responses.lib import BaseResponse


INFO = """<h1>{url}</h1>

<p>This is an <a href="http://opendap.org">Opendap</a>-enabled dataset. It can be accessed using different applications, without the need to download unpack and parse the data.</p>

<h2>Python</h2>

<p>To access this dataset using Python you can use the Pydap module:</p>

<code><pre>&gt;&gt;&gt; from pydap.client import open_url
&gt;&gt;&gt; dataset = open_url("{url}")</pre></code>

<h2>Ferret</h2>

<p>To open this dataset with Ferret:</p>

<code><pre>$ ferret
yes? use "{url}"</pre></code>


<h2>GrADS</h2>

<p>GrADS has different ways of accessing gridded and in-situ data. To access both data types:</p>

<code><pre>$ grads
ga-> sdfopen {url}
ga-> open {url}</pre></code>

<h2>Panoply</h2>

<p>In order to load this dataset in Panoply, click "File", "Open Remote File" (CTRL-L) and insert the URL "{url}".</p>


<h2>IDV</h2>

<p>To access the dataset, go to "Data Choosers", select "URLs" and type "{dods}".</p>


<h2>ODV</h2>

<p>To open this dataset in ODV, open the remote dataset "{url}.nc".</p>


<h2>IDL</h1>

<p>To open this dataset using IDL:</p>

<code><pre>IDL> url = '{url}'
IDL> stat = opendap_get(url, def, mode='dds')
IDL> help, def, /structures</pre></code>


"""


class InfoResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-type', 'text/html; charset=utf-8'),
        ])

    def __call__(self, environ, start_response):
        req = Request(environ)
        res = Response(status='200 OK', body=INFO.format(
            url=req.path_url.rsplit('.', 1)[0],
            dods=req.path_url.rsplit('.', 1)[0].replace('http://', 'dods://')))
        return res(environ, start_response)


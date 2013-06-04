r"""
A tiling Opendap-aware caching proxy server.

This program is a proxy to any Opendap server. Data requests (dods,
ascii and other configurable responses) are cached locally by an
Opendap-aware algorithm; this means that requests for a subset of
data that was already requested, eg, will be read from cache even
though the URLs may be completely different.

The caching mechanism works by splitting an n-dimensional dataset
in pairs of tiles, like a binary k-d tree::

        A 
       / \
      B   C
     /|   |\
    D E   F G

When a slice of the data is requested we check each tile to see if
the data is present in that tile. The result may be this, eg::

        1 
       / \
      1   1
     /|   |\
    1 1   1 0

In order to download the data with the least transferred bytes we
need to request tiles B and F from the Opendap server, store it
locally, and then return the requested slice (which now is contained
in the cached data). If the node E is already in the cache we can
request D instead of B, to minimize downloaded data. 

(c) 2011-2012 Roberto De Almeida, Guilherme Castelao

"""
from __future__ import division

import sys, logging
logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger('pydap')
logger.setLevel(logging.INFO)

import os
from urlparse import urljoin
from collections import defaultdict
from rfc822 import parsedate
import time
from stat import ST_MTIME

from webob import Request
from paste.proxy import Proxy
import requests
import h5py
import numpy as np

from pydap.client import open_url
from pydap.handlers.lib import SimpleHandler
from pydap.lib import walk, combine_slices, fix_slice, hyperslab
from pydap.model import *
from pydap.proxy import ArrayProxy
from pydap.util.rwlock import ReadWriteLock

import pydap.lib
pydap.lib.USER_AGENT = 'DapCache/0.1'


TILESIZE = int(2e6)  # bytes
MAXSIZE  = int(1e8)
LOCK = defaultdict(ReadWriteLock)

# TODO:
# improve storage
# check if cache has exceeded its size: we need to use redis for the RW lock, shared with a script that deletes old files.
#   https://github.com/andymccurdy/redis-py
#   http://chris-lamb.co.uk/2010/06/07/distributing-locking-python-and-redis/
#   http://degizmo.com/2010/03/22/getting-started-redis-and-python/
#   http://redis.io/commands/setnx


class DapCache(object):
    def __init__(self, url, responses, cachedir, tilesize=TILESIZE, maxsize=MAXSIZE):
        self.url = url
        self.responses = responses
        if not os.path.exists(cachedir):
            os.mkdir(cachedir)
        self.cachedir = cachedir
        self.tilesize = int(tilesize)
        self.maxsize = int(maxsize)

    def __call__(self, environ, start_response):
        req = Request(environ)
        if '.' in req.path_info:
            basename, response = req.path_info.rsplit('.', 1)
        else:
            basename, response = req.path_info, None

        # cache a local copy
        if response in self.responses:
            url = urljoin(self.url, basename)
            dataset = open_url(url)
            cachepath = os.path.join(self.cachedir, basename.replace('/', '_'))

            # here we an use mstat to check the mtime of the file, and 
            # do a HEAD on the dataset to compare with Last-Modified header
            r = requests.head(url + '.dods')
            if 'last-modified' in r.headers:
                last_modified = time.mktime(parsedate(r.headers['last-modified']))
                mtime = time.mktime(time.localtime( os.stat(cachepath)[ST_MTIME] ))
                if last_modified > mtime:
                    os.unlink(cachepath)

            # replace data with a caching version
            for var in walk(dataset, BaseType):
                var.data = CachingArrayProxy(
                        cachepath, self.tilesize, self.maxsize,
                        var.type, var.id,
                        var.data.url, var.data.shape, var.data._slice)
            #for var in walk(dataset, SequenceType):
            #    var.data = CachingSequenceProxy(
            #            cachepath,
            #            var.id,
            #            var.data.url, var.data.slice, var.data._slice, var.data.children)

            app = SimpleHandler(dataset)
        # pass this upstream
        else:
            app = Proxy(self.url)

        return app(environ, start_response)


class CachingArrayProxy(ArrayProxy):
    def __init__(self, cachepath, tilesize, maxsize, dtype, id_, url, shape, slice_=None):
        super(CachingArrayProxy, self).__init__(id_, url, shape, slice_)

        self.tilesize = tilesize
        self.maxsize = maxsize

        self.lock = LOCK[cachepath]
        self.fp = h5py.File(cachepath, 'a')

        # how many tiles are we using for the cache? we can calculate
        # this analytically, but this way is more explicit... ;)
        size = np.prod(shape) * dtype.size
        divisions = 0
        while size > tilesize:
            size = np.ceil(size/2)
            divisions += 1
        self.tiles = 2**divisions

        # open cache data/index and create arrays if necessary
        with self.lock.readlock:
            if id_ not in self.fp:
                with self.lock.writelock:
                    self.fp.create_dataset(id_, shape, dtype.typecode)
            if 'index' not in self.fp:
                with self.lock.writelock:
                    self.fp.create_group('index')
            if id_ not in self.fp['index']:
                with self.lock.writelock:
                    self.fp['index'].create_dataset(id_, (self.tiles,), bool)
        self.cache = self.fp[id_]
        self.index = self.fp['index'][id_]

    def __getitem__(self, index):
        """
        Download data for all the tiles containing the request.

        """
        slice_ = combine_slices(self._slice, fix_slice(index, self.shape))
        requested = self.parse_request(slice_)
        with self.lock.readlock:
            needed = requested & ~self.index[:]

            # update cache with needed data
            with self.lock.writelock:
                for tile in self.get_tiles(needed):
                    self.cache[tile] = super(CachingArrayProxy, self).__getitem__(tile)
                # update index with newly requested data
                self.index[:] = self.index[:] | needed

            return self.cache[slice_]

    def parse_request(self, slice_):
        """
        Parse a slice request into an array of requested tiles.

        """
        # check which of the smaller tiles are in the request
        height = int(np.log2(self.tiles))
        requested = []
        queue = [ (0, list(0 for dim in self.shape), list(self.shape)) ]
        while queue:
            depth, start, end = queue.pop(0)
            if depth < height:
                left, right = split(start, end)
                queue.append( ((depth+1,) + left) )
                queue.append( ((depth+1,) + right) )
            else:
                for s, min_, max_ in zip(slice_, start, end):
                    if s.stop <= min_ or s.start >= max_:
                        requested.append(0)
                        break
                else:
                    requested.append(1)

        return np.array(requested, dtype=bool)

    def get_tiles(self, needed):
        r"""
        Combine needed tiles and return them as slices.

        We create a k-d tree and go from the top to the bottom.
        If for a given node all its lower children are needed, say::

                0 
               / \
              0   0
             /|   |\
            1 1   1 1
            
        We can make a request for a continuous region that contains
        all child nodes.

        """
        queue = [ (needed, list(0 for dim in self.shape), list(self.shape)) ]
        while queue:
            needed, start, end = queue.pop(0)
            size = sum(needed) * self.tilesize
            if all(needed) and size < self.maxsize:
                yield tuple(slice(min_, max_, 1) for min_, max_ in zip(start, end))
            elif any(needed):
                middle = np.floor(len(needed) / 2)
                left, right = split(start, end)
                queue.append( ((needed[:middle],) + left) )
                queue.append( ((needed[middle:],) + right) )


def split(start, end):
    # split along longest dimension
    shape = tuple(p1-p0 for p0, p1 in zip(start, end))
    axis = shape.index(max(shape))
    middle = int(start[axis] + np.floor(shape[axis] / 2))

    left = start, end[:axis] + [middle] + end[axis+1:]
    right = start[:axis] + [middle] + start[axis+1:], end

    return left, right


def make_cache(global_conf, url, responses, **kwargs):
    from paste.deploy.converters import aslist
    responses = aslist(responses)
    return DapCache(url, responses, **kwargs)


if __name__ == '__main__':
    app = DapCache('http://pydap.zenofdata.com/', ['dods', 'asc', 'ascii'], '.cache', 64)
    from paste import httpserver
    httpserver.serve(app, '127.0.0.1', port=8003)

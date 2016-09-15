Pydap
=====

[![license](https://img.shields.io/github/license/pydap/pydap.svg?maxAge=2592000?style=plastic)](https://opensource.org/licenses/MIT)
[![Build Status](https://travis-ci.org/pydap/pydap.svg)](https://travis-ci.org/pydap/pydap)
[![PyPI](https://img.shields.io/pypi/v/pydap.svg?maxAge=2592000?style=plastic)](https://pypi.python.org/pypi/pydap)


##Introduction

[Pydap](http://www.pydap.org/) is an implementation of the Opendap/DODS protocol, 
written from scratch.  You can use Pydap to access scientific data on the internet 
without having to  download it; instead, you work with special array and iterable 
objects that  download data on-the-fly as necessary, saving bandwidth and time. 
The module also comes with a robust-but-lightweight Opendap server, implemented 
as a WSGI application.

##Installation
From the cheeseshop
```
$ pip install pydap
```
or from source
```
$ git clone https://github.com/pydap/pydap.git
$ cd pydap
$ paver
```



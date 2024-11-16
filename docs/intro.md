# <font size="7"><span style='color:#0066cc'> **Welcome to pydap**<font size="3">


`pydap` is a Python implementation of the **Data Access Protocol** (**DAP**), also known as [OPeNDAP](http://www.opendap.org/). You can use `pydap` as a client to access thousands of scientific datasets in a transparent and efficient way through the internet, or you can set up `pydap` as a server to make your data available through the internet via an URL.

## Why Pydap?

Pydap was originally developed in the mid to late 2000s, as a way to access data in OPeNDAP servers. See [this talk](https://www.youtube.com/live/rPbW_RZmIJA?feature=shared) by the original developer of PyDAP. Pydap was increadible successful, and widely used both as a client and server.


Since then, many more clients have been developed within the growing Python ecosystem, among them the hugely successful `xarray` and many of the Pangeo tools. Many people are not aware of but `pydap` is a backend engine for `xarray` to access OPeNDAP data, is installed everytime xarray gets installed. Over the last 10-15 years, OPeNDAP servers have gotten more sophisticated, and so continuing support for the development of `pydap` will benefit `xarray`/Pangeo users, by providing efficient access patterns to OPeNDAP servers.


Dive into the documentation to learn best practices for accessing remote data on OPeNDAP servers.

```{tableofcontents}
```

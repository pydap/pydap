<a href="../es/intro.html">Leer en Español</a> | <a href="../en/intro.html">Read in English</a>

# <font size="7"><span style='color:#0066cc'> **Welcome to pydap**<font size="3">


`pydap` is a Python implementation of the **Data Access Protocol** (**DAP**), also known as [OPeNDAP](http://www.opendap.org/). You can use `pydap` as a client to access thousands of scientific datasets available via OPeNDAP servers in a secure, transparent, and efficient way through the internet, or you can set up `pydap` as a server to make your data available through the internet via a URL.

## <font size="5.5"><span style='color:#ff6666'>**Why OPeNDAP?**<font size="3">

Equitable open data access remains essential for advancing effective Open Science frameworks, enabling data-driven discoveries, and empowering inclusive science education and citizen science practices. At the institution level, `OPeNDAP` servers represent a free, open-source solution to enable data access as an alternative to the comercial cloud, as a cost-effective solution when data is stored on the cloud and data file formats that are not cloud-native, or when the collections are too large to re-format.

For researchers, educators, and citizen scientists, `OPeNDAP` allows to share scientific data freely under well-known standard protocols over the web, making data publishable, citable, and findable. Importantly, data users can access and subset data in a data-proximate way, downloading only the subregion of interest.

Beginner OPeNDAP users may rapidly find themselves spending the time to better understand OPeNDAP to enable efficient data access. Some of the OPeNDAP elements that require developing a varying degree of skill by the user to better exploit OPeNDAP are:

1. Constraint Expressions.
2. Escaping URL characters for safe internet use.
3. Differences between DAP2 / DAP4 protocol.


## <font size="5.5"><span style='color:#ff6666'>**Why Pydap?**<font size="3">


| ![WhyPydap](/images/WhyPydap.png) |
|:--:|
| *Figure 1. Comparison of ways to download a subset of an entire remote file. In this example, the remote data covers the globe, and a pydap user downloads a subset by slicing the pydap array. A traditional OPeNDAP native approach is to use a Data Request Form to manually construct the URL along with its Constraint Expression.* |


`Pydap` enables access to data on OPeNDAP servers in a pythonic way, and enables interactive and exploratory subsetting of remote datasets. To summarize `pydap`:

1. Builds Contraint Expression for the user. This is done by slicing an array (See [Figure 1](WhyPydap)).
2. Escapes URL parameters to safely transmit data use over the internet.
3. Can fetch binary data from DAP2 (`.dods`) and DAP4 (`.dap`) data servers, turning it to a numerical `numpy` array.
4. Covers the DAP2 and (*Most*) of the DAP4 data model.
5. Is being developed and maintained by members of the OPeNDAP team, with open communication with Unidata.


```{note}
Knowledge of how to construct URLs with Constraint Expressions remains important, as this can speed up (`Pydap`'s) dataset creation and therefore data exploration.
```

## <font size="5.5"><span style='color:#ff6666'>**What Pydap is not**<font size="3">

`Pydap` is very lightweight, which is great! However, as a result it offers little parallelism, compute or plotting. Most of that is enabled by external Python libraries. However, `Pydap` remains a `backend engine for xarray`, which fosters a growing community of users and developers, and `xarray` can add parallelism via `Dask` / `Coiled` and plotting via its own use of `matplotlib`.

That said, we recognize that `pydap` native approaches may provide boost in performance, before using the resulting pydap dataset to create `xarray` dataset. And so `pydap` remains under development! See the [What's New](NEWS) section If you would like to contribute, head to the [issue tracker](https://github.com/pydap/pydap/issues). We welcome contributions! You can pick an existing issue, open a new one. You can contribute to improve our code base, or you can also help improve our documentation with a tutorial example!


Dive into the documentation to learn best practices for accessing remote data on OPeNDAP servers.

```{tableofcontents}
```

<a href="../es/intro.html">Leer en Español</a> | <a href="../en/intro.html">Read in English</a>

# <font size="7"><span style='color:#0066cc'> **Welcome to pydap**<font size="3">


`pydap` is a Python implementation of the **Data Access Protocol** (**DAP**), also known as [OPeNDAP](http://www.opendap.org/). Pydap's client now offers robust `DAP4` support, enabling data users to access thousands of scientific datasets available via OPeNDAP servers in a secure, transparent, and efficient way through the internet, or you can set up `pydap` as a server to make your data available through the internet via a URL.

## <font size="5.5"><span style='color:#ff6666'>**Pydap now supports DAP4 data access in a much performant way!**<font size="3">


| ![WhyPydap](/images/benchmark1.png) |
|:--:|
| *Figure 1. Benchmarks comparing data streaming using Xarray (with pydap as backend engine) and pydap-only new streaming API. Non-supported implies data cannot be aggregated directly with Xarray* |

| ![WhyPydap](/images/benchmark2.png) |
|:--:|
| *Figure 2. Benchmarks comparing data streaming using Xarray (with pydap as backend) and pydap-only new streaming API. Non-supported implies data cannot be aggregated directly with Xarray* |

To read more about benchmarks displayed above, and the specifics on how pydap's performance has been improved over the past year, check out [this free zenodo resource](https://zenodo.org/records/19372926)

The following tutorials show `pydap-only` streaming  workflows from NASA Earthdata:

- [Access Calipso L2 data](./notebooks/CalipsoL2_access)
- [Access TEMPO Near-Real-Time data](./notebooks/TEMPO_NRT)
- [Access Ecostress data](./notebooks/Ecostress)
- [Access DAYMET data](./notebooks/DAYMET)

Dive into the documentation to learn best practices for accessing remote data on OPeNDAP servers.


## <font size="5.5"><span style='color:#ff6666'>**Why OPeNDAP?**<font size="3">

Equitable open data access remains essential for advancing effective Open Science frameworks, enabling data-driven discoveries, and empowering inclusive science education and citizen science practices. At the institution level, `OPeNDAP` servers represent a free, open-source solution to enable data access as an alternative to the comercial cloud, as a cost-effective solution when data is stored on the cloud and data file formats that are not cloud-native, or when the collections are too large to re-format.

For researchers, educators, and citizen scientists, `OPeNDAP` allows to share scientific data freely under well-known standard protocols over the web, making data publishable, citable, and findable. Importantly, data users can access and subset data in a data-proximate way, downloading only the subregion of interest.

Beginner OPeNDAP users may rapidly find themselves spending the time to better understand OPeNDAP to enable efficient data access. Some of the OPeNDAP elements that require developing a varying degree of skill by the user to better exploit OPeNDAP are:

1. Constraint Expressions.
2. Escaping URL characters for safe internet use.
3. Differences between DAP2 / DAP4 protocol.



```{tableofcontents}
```

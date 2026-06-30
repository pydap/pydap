<a href="../es/intro.html">Leer en Español</a> | <a href="../en/intro.html">Leer en inglés</a>

# <font size="7"><span style='color:#0066cc'> **Bienvenido a pydap**<font size="3">


`pydap` es una implementación en Python del **Data Access Protocol** (**DAP**), también conocido como [OPeNDAP](http://www.opendap.org/). `Pydap` ahora es compatible con el protocolo `DAP4`, lo que permite acceder de forma segura, transparente, y eficiente, a millones de archivos científicos disponibles mediante servidores OPeNDAP a traves de la conexion de internet, o por medio de la `Nube`.

## <font size="5.5"><span style='color:#ff6666'>**Pydap ahora permite accesso con mucho mejor rendimiento por medio del protocolo de  DAP4.**<font size="3">


| ![WhyPydap](/images/benchmark1.png) |
|:--:|
| *Figura 1. Comparativas de rendimiento de transmisión de datos usando Xarray (con pydap como "backend engine") y la nueva API de transmisión unica de pydap. No compatible implica que los datos no se pueden agregar directamente con Xarray.* |

| ![WhyPydap](/images/benchmark2.png) |
|:--:|
| *Figura 2. Comparativas de rendimiento de transmisión de datos usando Xarray (con pydap como "backend engine") y la nueva API de transmisión unica de pydap. No compatible implica que los datos no se pueden agregar directamente con Xarray.* |

Para leer más sobre las comparativas mostradas arriba y los detalles de cómo ha mejorado el rendimiento de pydap durante el último año, consulta [este recurso gratuito en Zenodo](https://zenodo.org/records/19372926).

Los siguientes tutoriales muestran el nuevo accesso directo por medio de `pydap` y el protocolo `DAP4`, accessando datos cientificos de NASA Earthdata:

- [Tutorial de acceso al projecto de NASA Calipso L2](./notebooks/CalipsoL2_access)
- [Tutorial de acceso al projecto de NASA TEMPO Near-Real-Time](./notebooks/TEMPO_NRT)
- [Tutorial de acceso al projecto de NASA Ecostress](./notebooks/Ecostress)
- [Tutorial de acceso al projecto de NASA DAYMET](./notebooks/DAYMET)

Explora la documentación para aprender buenas prácticas al acceder a datos remotos en servidores OPeNDAP.


## <font size="5.5"><span style='color:#ff6666'>**¿Por qué OPeNDAP?**<font size="3">

El acceso equitativo a datos abiertos sigue siendo esencial para impulsar marcos efectivos de ciencia abierta, permitir descubrimientos basados en datos y fortalecer la educación científica inclusiva y la ciencia ciudadana. A nivel institucional, los servidores de `OPeNDAP` representan una solución libre y de código abierto para facilitar el acceso abierto a datos como alternativa a la nube comercial. `OPeNDAP` tambien representa una solución rentable cuando los datos están almacenados en la nube y los formatos de archivo no son nativos de la nube (`Cloud-Native`), o cuando los archivos en conjunto ocupan demasiada como para reformatearlas.

Para investigadores, educadores y científicos ciudadanos, `OPeNDAP` permite compartir datos científicos libremente mediante protocolos estándar, permitiendo la publicacion de datos cientificos de manera que puedan ser citados y fáciles de encontrar. Es importante destacar que las personas usuarias pueden acceder y subdividir los datos de forma próxima a ellos, descargando solo la subregión de interés.



```{tableofcontents}
```

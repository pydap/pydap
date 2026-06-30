<a href="../es/intro.html">Leer en Español</a> | <a href="../en/intro.html">Leer en inglés</a>

# <font size="7"><span style='color:#0066cc'> **Bienvenido a pydap**<font size="3">


`pydap` es una implementación en Python del **Data Access Protocol** (**DAP**), también conocido como [OPeNDAP](http://www.opendap.org/). El cliente de pydap ahora ofrece soporte robusto para `DAP4`, lo que permite a las personas usuarias acceder de forma segura, transparente y eficiente, a través de internet, a miles de conjuntos de datos científicos disponibles mediante servidores OPeNDAP. También puedes configurar `pydap` como servidor para publicar tus datos en internet mediante una URL.

## <font size="5.5"><span style='color:#ff6666'>**Pydap ahora admite el acceso a datos DAP4 con mucho mejor rendimiento.**<font size="3">


| ![WhyPydap](/images/benchmark1.png) |
|:--:|
| *Figura 1. Comparativas de rendimiento de transmisión de datos usando Xarray (con pydap como motor backend) y la nueva API de transmisión solo con pydap. No compatible implica que los datos no se pueden agregar directamente con Xarray.* |

| ![WhyPydap](/images/benchmark2.png) |
|:--:|
| *Figura 2. Comparativas de rendimiento de transmisión de datos usando Xarray (con pydap como backend) y la nueva API de transmisión solo con pydap. No compatible implica que los datos no se pueden agregar directamente con Xarray.* |

Para leer más sobre las comparativas mostradas arriba y los detalles de cómo ha mejorado el rendimiento de pydap durante el último año, consulta [este recurso gratuito en Zenodo](https://zenodo.org/records/19372926).

Los siguientes tutoriales muestran flujos de trabajo de transmisión `solo con pydap` desde NASA Earthdata:

- [Acceder a datos Calipso L2](./notebooks/CalipsoL2_access)
- [Acceder a datos TEMPO casi en tiempo real](./notebooks/TEMPO_NRT)
- [Acceder a datos Ecostress](./notebooks/Ecostress)
- [Acceder a datos DAYMET](./notebooks/DAYMET)

Explora la documentación para aprender buenas prácticas al acceder a datos remotos en servidores OPeNDAP.


## <font size="5.5"><span style='color:#ff6666'>**¿Por qué OPeNDAP?**<font size="3">

El acceso equitativo a datos abiertos sigue siendo esencial para impulsar marcos efectivos de ciencia abierta, permitir descubrimientos basados en datos y fortalecer la educación científica inclusiva y la ciencia ciudadana. A nivel institucional, los servidores `OPeNDAP` representan una solución libre y de código abierto para habilitar el acceso a datos como alternativa a la nube comercial, como una solución rentable cuando los datos están almacenados en la nube y los formatos de archivo no son nativos de la nube, o cuando las colecciones son demasiado grandes para reformatearlas.

Para investigadores, educadores y científicos ciudadanos, `OPeNDAP` permite compartir datos científicos libremente mediante protocolos estándar conocidos en la web, haciendo que los datos sean publicables, citables y fáciles de encontrar. Es importante destacar que las personas usuarias pueden acceder y subdividir los datos de forma próxima a ellos, descargando solo la subregión de interés.

Quienes empiezan a usar OPeNDAP pueden encontrarse rápidamente invirtiendo tiempo en entenderlo mejor para habilitar un acceso eficiente a los datos. Algunos elementos de OPeNDAP que requieren desarrollar cierto grado de habilidad para aprovecharlo mejor son:

1. Expresiones de restricción.
2. Escapar caracteres de URL para un uso seguro en internet.
3. Diferencias entre los protocolos DAP2 / DAP4.



```{tableofcontents}
```

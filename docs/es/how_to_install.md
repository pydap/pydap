# Cómo instalar

Las versiones recientes de `pydap` pueden requerir actualizar la versión de Python. La versión más reciente de `pydap` requiere `Python=>3.12`. `Pydap` se puede instalar desde PyPI de la siguiente manera:

```shell
    $ pip install pydap
```

o, si estás usando Anaconda:
```shell
    $ conda install pydap
```

```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```

Esta instalación de `pydap` incluirá las dependencias mínimas para permitir que las personas usuarias subdividan datos remotos en servidores OPeNDAP.

```{note}
Recomendamos usar administradores de paquetes como `conda`/`mamba`. Este enfoque requiere tener una instalación de [Miniconda](https://docs.anaconda.com/miniconda/) o [Anaconda](https://docs.anaconda.com/anaconda/install/).
```

## Entornos reproducibles (conda)

Puedes usar conda fácilmente para instalar `pydap` y cualquier paquete opcional, y así compartir un flujo de trabajo reproducible. Por ejemplo:

```shell
    $ conda create -n pydap_env -c conda-forge python=3.12 pydap
    $ conda activate pydap_env
```

```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```

### Opcional para ejecutar los notebooks de esta documentación
- `matplotlib`
- `jupyterlab`
- `cartopy`
- `xarray`

Para instalar la versión más reciente de `pydap` (solo cliente), directamente desde el repositorio de GitHub, ejecuta:

```shell
    $ pip install --upgrade git+https://github.com/pydap/pydap.git
```

Esta versión no es estable, ya que se desarrolla y mejora activamente por las personas que contribuyen y mantienen el paquete `pydap`.

Si te interesa instalar `pydap` en `modo desarrollador` para contribuir potencialmente al paquete, ve a [Contribuir al código](contribute/contr_cod.md).

# Cómo instalar

Versiones recientes de `pydap` pueden requerir una versión de Python. Por ejemplo la versión más reciente de `pydap` requiere `Python=>3.12`. `Pydap` se puede instalar desde PyPI de la siguiente manera:

```shell
pip install pydap
```

o, si estás usando Anaconda:
```shell
conda install pydap
```
```{note}
Recomendamos usar `conda`/`mamba`, lo cual requiere tener una instalación de `conda-forge` [Miniforge](https://conda-forge.org/download/).
```

```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```

Esta instalación de `pydap` incluirá las dependencias mínimas para accessar a datos remotos en servidores OPeNDAP.



## Entornos reproducibles (conda)

Puedes usar conda fácilmente para instalar `pydap` y cualquier paquete opcional, y así compartir un flujo de trabajo reproducible. Por ejemplo:

```shell
conda create -n pydap_env -c conda-forge python=3.12 pydap
conda activate pydap_env
```

```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```

### Opcional para ejecutar los notebooks de esta documentación
- `matplotlib`
- `jupyterlab`
- `cartopy`
- `xarray`
- `earthaccess`

Para instalar la versión más reciente de `pydap` directamente desde el repositorio de GitHub, ejecuta:

```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```

Esta versión no es la mas estable, ya que esta en continue desarrollo. Solo se recommienda si la nueva version contiene un `bug` que ya ha side resuelto.

Si te interesa instalar `pydap` en mode `editable` para contribuir al proyecto, lee [Contribuir al código](contribute/contr_cod.md).

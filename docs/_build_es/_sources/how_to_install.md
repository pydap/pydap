# Como Installar

A partir de la version `3.5.1`, la installacion de `pydap` esta dividida en las siguientes dos partes, dependiendo de como se quiera usar
## 1. Puro Acceso
Para installar `pydap` de manera que solo se use para acceder a archivos scientificos remotos, en la terminal ejecute lo siguiente:

```shell
pip install pydap
```
o usando el manejador de paquetes `conda`

```shell
conda install pydap
```

```{note}
Si ya tiene `mamba` instalado, puede reemplazar `conda` por `mamba` en los comandos.
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```
This installation of `pydap` will include the minimal dependencies to allow users to subset remote data on OPeNDAP servers.

## 2. Installacion Completa
Para installar `pydap` con todas su funcionalidades, includendo como servidos, execute:

```shell
conda install pydap-server
```
La installacion de `pydap` incluira todas las dependencias necesarias para a) acceder a informacion scientifica en servidores de OPeNDAP, y b) user `pydap` como servidor.


## Dependencias
### Minimas requerias
Las siguientes son las dependencias minimas para user a `pydap` como cliente de acceso:

- `python>=3.10`
- `numpy`
- `scipy`
- `requests`
- `requests_cache`
- `beautifulsoup4`
- `lxml`
- `Webob`


### Addicionales
Los siguientes son paquetes de python para poder executar los ejemplos que se encuentran en el resto de la documentacion
- `matplotlib`
- `jupyter-lab`
- `cartopy`
- `xarray`


### extra-dependencies
Con [PyPI](https://pypi.org/) uno tambien puede installar las dependencias extras en el project `pydap`. Por ejemplo:
```shell
pip install pydap"[server,netcdf]"
```

Este comando installara la libreria `netCDF4` as como otras dependencias para user/ejecutar `pydap` como un servidor. Con esto, ser podra user `pydap` como un servidor detras de [Apache](https://www.apache.org/).

```{note}
De todas las opciones presentadas, recomendamos usar `conda`/`mamba`. Eso requiere la instalacion de [Miniconda](https://docs.anaconda.com/miniconda/) o [Anaconda](https://docs.anaconda.com/anaconda/install/).
```

## Ejemplo de entorno virtual

Como ejemplo presentamos los siguientes comandos para crear un entorno virtual de conda, con los paquetes necesarios para usar `pydap`.

```shell
conda create -n pydap_env -c conda-forge python=3.10 pydap-server jupyterlab ipython netCDF4 matplotlib
conda activate pydap
```

## Version mas reciente de `pydap`

Para instalar la version mas reciente de `pydap` directamente del repositorio de github, ejecute:

```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```
La version que se instalara sera la reciente en el projecto, y muy posiblemente no sea la version estable oficial.

Si estas interesado en instalar `pydap` en modo "desarrollo", sigue la siguente liga [Contributing to the code](contribute/contr_cod.md).

# Contribuir a la documentación

Tus contribuciones son bienvenidas. Hay muchas formas de contribuir a la documentación:

1. Identificar y corregir errores tipográficos.
2. Mejorar la descripción de `PyDAP` y, en general, del modelo DAP.
3. Recetas. Queremos saber cómo se están usando `PyDAP` y [OPeNDAP](https://www.opendap.org/), es decir, qué tipo de preguntas o problemas ayudan a resolver y cuáles son los dominios de experiencia.
4. Demostrar una optimización en los patrones de acceso, por ejemplo una comparativa de rendimiento.
5. Una URL de `OPeNDAP`. Queremos aprender más sobre URLs de datos OPeNDAP disponibles y hacerlas accesibles a la comunidad amplia de usuarios de PyDAP. Somos firmes defensores de la `democratización de datos` y la `ciencia abierta`, y ambas comienzan haciendo que tus datos sean `encontrables`.


La documentación se construyó con [jupyter-book](https://jupyterbook.org/en/stable/intro.html), que admite distintos tipos de archivos. Aquí usamos `rst` e `ipynb` (notebooks ejecutables).

## ¿Cómo contribuir a la documentación?
Para agregar o editar la documentación, recomendamos seguir las guías previas sobre control de versiones, forks y ramas. Dicho eso, puedes seguir estos pasos:

1. Navega al repositorio clonado en tu máquina local.

2. Crea o activa el entorno conda.
```shell
conda env create -f docs/environment.yml
conda activate pydap_docs
```
```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```
3. Instala `pydap` en modo `developer`, para asegurarte de que todos los notebooks se construyan correctamente. Para instalar en modo de desarrollo, ejecuta:

```shell
pip install -e .
```

4. Crea una rama nueva, configura su upstream y usa git (consulta los [pasos 3 y 4 de contribuir al código](contr_cod.md)).

5. La documentación ahora está dividida en dos fuentes: una en inglés (la puedes encontrar en `docs/en`) y otra en español (la puedes encontrar en `docs/es`). Dependiendo de la versión de la documentación a la que contribuyas, puedes modificar los archivos fuente.

6. Una vez que hayas hecho cambios en los archivos fuente de la documentación (ya sea en `docs/en` o `docs/es`), usa `build.sh` para limpiar y construir los archivos de documentación `html` (puede que necesites hacer que `build.sh` sea ejecutable con `chmod +x`).
```shell
cd docs
chmod +x build.sh
./build.sh
```

```{warning}
Muchos ejemplos tutoriales de la documentación requieren autenticación EDL mediante un archivo local `.netrc`. Asegúrate de tener uno con credenciales válidas. Consulta [Authentication](../notebooks/Authentication).
```
Dependiendo de cuántos cambios hayas hecho en la documentación, este último paso puede tardar un tiempo. También depende del tipo de archivos agregados a la documentación (`ipynb` tarda más en construirse).

7. Una vez terminado el proceso de construcción, puedes inspeccionar los archivos html generados localmente. `build.sh` crea una redirección en la base de los archivos html construidos. Por lo tanto, para abrir la documentación en inglés ejecuta:
```shell
open _build/html/index.html
```
La redirección significa que la versión en inglés de la documentación es la predeterminada. Para abrir la versión en español, ejecuta:
```shell
open _build/html/es/intro.html
```

```{warning}
Asegúrate de comprobar que **TODOS** los notebooks se construyeron correctamente.
```

```{note}
La documentación tendrá un selector para alternar manualmente entre las versiones en inglés y español.
```

8. Sube todos los cambios y crea un PR. `PyDAP` sigue la recomendación de mantener los archivos `source` en `main` y los archivos `build` en la rama `gh-pages`.
```{note}
No incluyas contraseñas ni tokens. Solo estás enviando archivos `source`.
```

9. Una vez que una persona mantenedora de `PyDAP` apruebe tu PR, este se fusionará en `main`. La persona mantenedora de `PyDAP` puede publicar la documentación y actualizar la rama `gh-pages`. En términos generales, los pasos para publicar la documentación (es decir, reconstruir la rama `gh-pages`) están detallados y descritos aquí: https://jupyterbook.org/en/stable/start/publish.html.

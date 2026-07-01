# Contribuir al código

1. Instala `PyDAP` dentro de un entorno de pruebas aislado.
```shell
conda create -n pydap_tests -c conda-forge python=3.12
conda env update -n pydap_tests -f ci/environment.yml
conda activate pydap_tests
pip install -e .
```
Esto creará y activará un entorno de pruebas llamado `pydap_tests`, que contendrá muchas de las dependencias necesarias para probar la instalación de pydap (`pydap-server`) (consulta [cómo instalar](../how_to_install.md)) en `modo desarrollador`.

```{note}
Si ya tienes `mamba` instalado, puedes reemplazar `conda` por `mamba` en todos los comandos.
```
2. Clona el repositorio en tu máquina local y descarga los commits más recientes.
Si todavía no tienes un repositorio local, clónalo.
```shell
git clone https://github.com/pydap/pydap.git
```
Si ya tienes un repositorio local, entonces ejecuta:
```shell
git pull
```
3. Crea una rama nueva y configura su upstream.
```shell
git checkout -b new_branch_name
git push --set-upstream origin new_branch_name
```
4. Ahora usa [git](git.md) para agregar y confirmar cambios en `pydap`.

5. Asegúrate de que el código siga la guía de estilo ejecutando:

```shell
conda install -c conda-forge pre-commit
pre-commit run --all
```
Los comandos anteriores instalan y ejecutarán automáticamente toda la configuración de formato de pre-commit especificada en el archivo yaml cada vez que se use git commit.

6. Asegúrate de que el código esté bien probado agregando o mejorando pruebas en el repositorio `src/pydap/tests`. pydap usa [pytest](https://docs.pytest.org/en/stable/). Para ejecutar las pruebas, usa el siguiente comando:

```shell
pytest -v
```

7. Haz push a `upstream` y crea un Pull Request hacia el repositorio principal. Asegúrate de describir bien el bug, la mejora del código y, siempre que sea posible, cualquier issue que los cambios propuestos cerrarán.

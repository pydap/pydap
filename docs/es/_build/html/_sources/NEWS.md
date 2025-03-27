Lo Nuevo
========

3.5.4
------
*Fecha de lanzamiento: 18 de marzo de 2025*

* Actualizacion de pre-commit hooks por @pre-commit-ci in #431
* `Webob` ya no es usado por `pydap`. Ahora `pydap` usa la libreria `requests`, la cual automatiza el processo de autentification. Por @Mikejmnez in #434
* Actualización de pre-commit hooks por @pre-commit-ci en #436
* Nueva funcionalidad: `pydap` ahora usa `request_cache` para inicializar una sesión, lo que permite almacenar respuestas en caché. Por @Mikejmnez en #438
* Nueva propiedad `.grids()` para identificar todos los objetos de tipo Grid dentro del pydap.dataset. Por @Mikejmnez en #446
* Corrección de error: Se reemplaza dap2 con http al usar esquemas para determinar el protocolo DAP. Por @Mikejmnez en #451
* Se agrega soporte para devolver un objeto de sesión como atributo en pydap.dataset. Ahora, los usuarios pueden recuperar la sesión. Por @Mikejmnez en #447
* Se recopila y proporciona más metadatos sobre los nombres de las dimensiones por variable. Por @Mikejmnez en #453
* Se eliminan atributos globales NC_GLOBAL y DODS_EXTRA heredados del analizador das. Por @Mikejmnez en #455
* Cambio predeterminado: Ahora output_grid=False es el argumento predeterminado para open_url. Por @Mikejmnez en #457

3.5.3
------
*Fecha de lanzamiento: 6 de enero de 2025*

* Se mejora el paralelismo en la lectura de fragmentos de datos binarios. Este problema afectaba especialmente a datasets con `chunks` muy pequeños, pero ya no es el caso. Por @Mikejmnez en #419
* Limpieza de documentación por @Mikejmnez en #420
* Nuevo soporte para analizar dmr con variables de tipo String. Por @Mikejmnez en #423
* Se permite que el analizador dmr maneje múltiples valores en un solo atributo. Por @Mikejmnez en #421
* Se agrega soporte para escapar espacios en blanco en nombres de grupos/variables. Por @Mikejmnez en #426
* Se agrega soporte para decodificar encabezados de fragmentos y establecer la longitud del DMR de forma genérica, además de detectar automáticamente la endianidad de los datos. Esto permite a pydap analizar respuestas DAP4 de TDS y Hyrax sin necesidad de lógica adicional para identificar el servidor que generó la respuesta. Por @Mikejmnez en #428


3.5.2
------
*Fecha de lanzamiento: 19 de noviembre de 2024*

* Se agrega insignia de Zenodo por @Mikejmnez https://github.com/pydap/pydap/pull/405
* Actualización de `pre-commit` hooks por @pre-commit-ci en https://github.com/pydap/pydap/pull/408
* Se agregan versiones más recientes de Python a la metadata y los flujos de prueba. Por @Mikejmnez en https://github.com/pydap/pydap/pull/410
* Se incluye `cas-extras` como dependencia mínima requerida para usar pydap solo como cliente. Por @Mikejmnez en https://github.com/pydap/pydap/pull/413
* Actualización de documentación: Se añade información sobre DAP4 y Expresiones de Restricción en "Pydap como Cliente". Por @Mikejmnez en https://github.com/pydap/pydap/pull/414
* Corrección rápida: Se implementa un parche temporal para analizar respuestas DAP4 de TDS, con un mensaje de advertencia recomendando el uso de DAP2. Por @Mikejmnez en https://github.com/pydap/pydap/pull/415


3.5.1
-----
*Fecha de lanzamiento: 28 de octubre de 2024*

- Soporte para DAP4:
  * Mejora en la documentación de Expresiones de Restricción (se incluyen dimensiones compartidas). Por @Mikejmnez en https://github.com/pydap/pydap/pull/357
  * Configuración de dimensiones a nivel de Group. Por @Mikejmnez en https://github.com/pydap/pydap/pull/360
  * Creación de un método para generar objetos DAP. Por @Mikejmnez en  https://github.com/pydap/pydap/pull/362
  * Soporte para servir datos nc4 con Groups. Por @Mikejmnez en https://github.com/pydap/pydap/pull/367
  * Función `get.Dap` y una corrección. Por @Mikejmnez en https://github.com/pydap/pydap/pull/373.
  * Se permite el uso de dimensiones repetidas. Por @Mikejmnez en https://github.com/pydap/pydap/pull/381
  * Eliminación de GridType del manejador de NetCDF. Por @Mikejmnez en https://github.com/pydap/pydap/pull/395
  * Análisis de elementos de atributos con tipos atómicos en `root`. Por @Mikejmnez en https://github.com/pydap/pydap/pull/403

- Simplificación instalación de `pydap`

- Otros cambios:
  * Se actualiza el logotipo y su referencia. Por @Mikejmnez en https://github.com/pydap/pydap/pull/366
  * Reducción en las dependencias requeridas para la instalación. Por @Mikejmnez en https://github.com/pydap/pydap/pull/369
  * Actualización del README. Por @Mikejmnez en https://github.com/pydap/pydap/pull/375 and https://github.com/pydap/pydap/pull/376
  * Mejoras en workflows. Por @Mikejmnez https://github.com/pydap/pydap/pull/377
  * Mejoras en la documentación @Mikejmnez in https://github.com/pydap/pydap/pull/378
  * Se permite que `dds` y el analizador de `DMR` manejen datasets remotos con `Flatten Groups`. Por @Mikejmnez en https://github.com/pydap/pydap/pull/399
  * Corrección en la variable usada para graficar y decodificar. @Mikejmnez in https://github.com/pydap/pydap/pull/383
  * Eliminación de espacios en blanco en ci/env. Por @Mikejmnez in https://github.com/pydap/pydap/pull/386
  * Bump mamba-org/setup-micromamba from 1 to 2 by @dependabot in https://github.com/pydap/pydap/pull/384
  * Update pre-commit hooks by @pre-commit-ci in https://github.com/pydap/pydap/pull/387
  * Update README.md by @Mikejmnez in https://github.com/pydap/pydap/pull/396


3.5.0
-----
*Fecha de lanzamiento: 16-Aug-2024*

- Soporte de DAP4:
  * Nuevo argumento para `client.open_url` : `protocol='dap2'|'dap4'`. Si ninguno se proporcional se usa `protocol='dap2'`.
  * Escape de los caracteres '[' and ']' por @Mikejmnez in https://github.com/pydap/pydap/pull/310
  * Include nuevo metodo para visualizar la estructura de arbol de el pydap dataset. Por @Mikejmnez in https://github.com/pydap/pydap/pull/324
  * Simplification del model del Dataset en DAP4 by @Mikejmnez in https://github.com/pydap/pydap/pull/327
  * Correccion de las Expresiones de Restriccion (CEs) de Arreglos en DAP4 by @Mikejmnez in https://github.com/pydap/pydap/pull/336
  * Iss339 por @Mikejmnez in https://github.com/pydap/pydap/pull/340
  * Suporte para atributos con valores NaNen el DMR (DAP4). Por @Mikejmnez in https://github.com/pydap/pydap/pull/345
  * Corrije la definicion de `named dimensions` a nivel `root`por @Mikejmnez in https://github.com/pydap/pydap/pull/348

- General updates:
  * Tests fix by @jgallagher59701 in https://github.com/pydap/pydap/pull/275
  * Clean up test workflows. by @owenlittlejohns in https://github.com/pydap/pydap/pull/283
  * `Import Mapping` from `collections.abc` by @rbeucher in https://github.com/pydap/pydap/pull/272
  * Allow newer python versions to test on MacOS mimicking Ubuntu workflows by @Mikejmnez in https://github.com/pydap/pydap/pull/293
  * Includes templates for PRs and Issues, fixes broken links in documentation, adds dependabots by @Mikejmnez in https://github.com/pydap/pydap/pull/296
  * Bump `actions/setup-python` from 4 to 5 by @dependabot in https://github.com/pydap/pydap/pull/300
  * Bump `actions/checkout` from 3 to 4 by @dependabot in https://github.com/pydap/pydap/pull/301
  * Removes dependency of `six` (for python 2.7) by @Mikejmnez in https://github.com/pydap/pydap/pull/304
  * `Pydap` now uses `pyproject.toml` by @Mikejmnez in https://github.com/pydap/pydap/pull/307
  * Includes `pre-commit`  by @Mikejmnez in https://github.com/pydap/pydap/pull/309
  * Set up `pre-commit` on github actions by @Mikejmnez in https://github.com/pydap/pydap/pull/312
  * Bump `actions/setup-python` from 3 to 5 by @dependabot in https://github.com/pydap/pydap/pull/316
  * Bump `actions/checkout` from 3 to 4 by @dependabot in https://github.com/pydap/pydap/pull/317
  * Fixes #207: `Pydap` can now use `PasterApp` and serve data  by @Mikejmnez in https://github.com/pydap/pydap/pull/318
  * Include compatibility with Numpy=2.0 @Mikejmnez in https://github.com/pydap/pydap/pull/322
  * Removes deprecation warnings by @Mikejmnez in https://github.com/pydap/pydap/pull/325
  * Point to `main` branch on GH/workflows by @Mikejmnez in https://github.com/pydap/pydap/pull/330
  * add authentication notebook by @Mikejmnez in https://github.com/pydap/pydap/pull/341
  * docs fix by @Mikejmnez in https://github.com/pydap/pydap/pull/342
  * resolve Numpy>1.25 deprecation error by @Mikejmnez in https://github.com/pydap/pydap/pull/343
  * include numpy attributes to BaseType to compute arraysize in bytes (uncompressed) by @Mikejmnez in https://github.com/pydap/pydap/pull/329
  * Modernize the documentation with jupyter-books  by @Mikejmnez in https://github.com/pydap/pydap/pull/337
  * Implicit discovery of entry points by @Mikejmnez in https://github.com/pydap/pydap/pull/346

Para ver una lista mas completa de lanzamientos anteriores, acuda a: https://github.com/pydap/pydap/releases

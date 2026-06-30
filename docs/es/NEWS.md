Novedades
=========



3.5.9
------
*Fecha de publicación: 2026-Marzo*

* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #579
* `get_cmr url`: habilita búsquedas usando versión y shortname por @Mikejmnez en #580
* Mejora la documentación para usar más Xarray y buenas prácticas por @Mikejmnez en #581
* Correcciones menores en la documentación por @Mikejmnez en #583
* Reemplaza las pruebas de SimpleGroup.nc4.h5 por SimpleGroup3.nc4.h5 por @Mikejmnez en #585
* Corrección menor por @Mikejmnez en #586
* Omite pruebas para un archivo que ya no está disponible en el servidor de pruebas por @Mikejmnez en #588
* Ya no es necesario especificar user_charset porque la codificación forma parte del contenido dmr por @Mikejmnez en #589
* Actualiza cómo se cuentan los bytes al deserializar arreglos String por @Mikejmnez en #592
* Usa algunos archivos tds para probar datos con jerarquías por @Mikejmnez en #591
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #593
* Parser DMRPP al modelo de dataset de Pydap por @Mikejmnez en #594
* Agrega jinja2 a la lista de dependencias por @malmans2 en #597
* Desaprueba batch=True|False al consolidar metadatos por @Mikejmnez en #599
* Actualiza actions/checkout de 5 a 6 por @dependabot[bot] en #600
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #601
* Habilita transmitir una respuesta dap hacia un netcdf4 por @Mikejmnez en #602
* Agrega un reintento cuando falla la obtención de una dimensión antes de devolver un error por @Mikejmnez en #604
* Asegura que los workers se creen como en macos y no se bifurquen como en Linu… por @Mikejmnez en #606
* Separa la descarga de concat_dims antes del manejo especial de claves por @Mikejmnez en #610
* Iss607 por @Mikejmnez en #608
* Restaura la sesión y refactoriza por @Mikejmnez en #611
* Cambia a nc4 el sufijo de los archivos al almacenar respuestas dap mientras se deserializan por @Mikejmnez en #613
* Permite pasar keep_variables sin dim_slices definidos por @Mikejmnez en #615
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #617
* Habilita soporte inicial para estructuras y secuencias en dap4 por @Mikejmnez en #618
* Aumenta el análisis de dmrVersion para distinguir dos enfoques de deserialización por @Mikejmnez en #619
* Corrige problemas con Groups vacíos anidados por @Mikejmnez en #624
* Habilita dimensiones ficticias al transmitir datos a un archivo (netcdf4 requiere dimensiones con nombre) por @Mikejmnez en #626
* Devuelve variables sin escapar por @Mikejmnez en #622
* Logo estático por @aaron-kaplan en #627
* Ajusta los elementos de valid_range para que coincidan con los de ncvariable al escribir una respuesta dap deserializada en un archivo nc4 por @Mikejmnez en #629
* Iss630 por @Mikejmnez en #631
* Omite prueba por @Mikejmnez en #632
* Elimina advertencias sobre cómo las estructuras pueden escaparse/accederse en la vista de árbol … por @Mikejmnez en #635
* Iss620 por @Mikejmnez en #625
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #638
* Devuelve grupos con FQN cuando se solicitan por @Mikejmnez en #640
* Habilita el análisis de Groups cuando no hay Variables (Atomic Types) en el DMR por @Mikejmnez en #637
* Fija jupyterbook por @Mikejmnez en #642
* Restaura el uso de Processes al transmitir respuestas dap en paralelo por @Mikejmnez en #643
* dmrpp: mejoras por @Mikejmnez en #645
* Corrige la asignación de atributos al archivo nc por @Mikejmnez en #648
* Soporta valor de datos en línea/faltante por @Mikejmnez en #649
* Habilita N dim_slices al transmitir N respuestas dap por @Mikejmnez en #652
* Habilita phony_dims dentro de jerarquías / grupos por @Mikejmnez en #654
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en #655
* fix: fuerza dmrVersion=2 para respuestas dap desde ngap de Hyrax de una compilación específica cuando dmrpp está en caché por @Mikejmnez en #657
* Actualiza el parser dmrpp: incorpora contribuciones de virtualizarr por @Mikejmnez en #658
* Incluye la entrada inline en el diccionario de metadatos solo si existe una por @Mikejmnez en #659
* Habilita deserializar una respuesta dap completa con uno o más arreglos String por @Mikejmnez en #661


3.5.8
------
*Fecha de publicación: 2025-Oct*

* Habilita usar un sqlite3 persistente como objeto de sesión de base de datos para pruebas por @Mikejmnez en https://github.com/pydap/pydap/pull/570
* Usa `GET` en lugar de una sesión compartida por @Mikejmnez en https://github.com/pydap/pydap/pull/572
* Habilita batch=False|True al consolidar metadatos por @Mikejmnez en https://github.com/pydap/pydap/pull/574
* Actualiza la documentación por @Mikejmnez en https://github.com/pydap/pydap/pull/569


3.5.7
------
*Fecha de publicación: 2025-Sept*

* Habilita actualizar las credenciales de sesión desde una sesión diferente por @Mikejmnez en https://github.com/pydap/pydap/pull/537
* Agrega una condición extra a get_cmr_urls para usarla si la anterior devuelve None por @Mikejmnez en https://github.com/pydap/pydap/pull/539
* fix: get_cmr_urls por @Mikejmnez en https://github.com/pydap/pydap/pull/540
* Habilita la opción de dimensiones compartidas al consolidar datos por @Mikejmnez en https://github.com/pydap/pydap/pull/541
* Lanza una excepción al intentar agrupar múltiples variables en el p… dap2 por @Mikejmnez en https://github.com/pydap/pydap/pull/544
* Reorganiza el agrupamiento para devolver None -> agregar datos al dataset pydap en su lugar por @Mikejmnez en https://github.com/pydap/pydap/pull/546
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en https://github.com/pydap/pydap/pull/548
* Actualiza actions/setup-python de 5 a 6 por @dependabot[bot] en https://github.com/pydap/pydap/pull/552
* Corrección para analizar CEs con subconjuntos por @Mikejmnez en https://github.com/pydap/pydap/pull/556
* Agrega slice como argumento para crear una sola URL dap con múltiples variables por @Mikejmnez en https://github.com/pydap/pydap/pull/554
* Mejora la gestión de memoria por @Mikejmnez en https://github.com/pydap/pydap/pull/560
* Agrega un verificador de datos por @Mikejmnez en https://github.com/pydap/pydap/pull/561
* Mejora el manejo de dimensiones para datasets con grupos anidados por @Mikejmnez en https://github.com/pydap/pydap/pull/563
* Elimina definiciones globales de URL: hace que las pruebas sean autocontenidas por @Mikejmnez en https://github.com/pydap/pydap/pull/564
* Mejora la seguridad en hilos y el comportamiento de caché por @Mikejmnez en https://github.com/pydap/pydap/pull/566
* Mejora el parser dmr y la deserialización por @Mikejmnez en https://github.com/pydap/pydap/pull/567


3.5.6
------
*Fecha de publicación: 2025-Ago-13*

* Actualiza la documentación con un xarray más reciente por @Mikejmnez en https://github.com/pydap/pydap/pull/487
* Actualiza la figura Why Pydap para mostrar xarray usando pydap por @Mikejmnez en https://github.com/pydap/pydap/pull/491
* Define https como el esquema de URL predeterminado cuando se usan dap2 o dap4 por @Mikejmnez en https://github.com/pydap/pydap/pull/493
* Mejoras a consolidate_metadata por @Mikejmnez en https://github.com/pydap/pydap/pull/488
* Agrega función para consultar URLs opendap desde CMR por @Mikejmnez en https://github.com/pydap/pydap/pull/495
* Elimina barras de los nombres de dimensiones al crear respuestas dds (servidor pydap) por @Mikejmnez en https://github.com/pydap/pydap/pull/503
* Compatibilidad hacia atrás por @Mikejmnez en https://github.com/pydap/pydap/pull/502
* Mejora el soporte para concat_dims con tamaño mayor que 1 por @Mikejmnez en https://github.com/pydap/pydap/pull/505
* Consolidación de dimensiones con nombre por @Mikejmnez en https://github.com/pydap/pydap/pull/507
* Transmite a un archivo temporal usando un gestor de chunks al descargar respuestas dap por @Mikejmnez en https://github.com/pydap/pydap/pull/509
* Libera memoria al descargar con dataset remoto por @Mikejmnez en https://github.com/pydap/pydap/pull/511
* Deshabilita caché excepto cuando se usa Consolidate_metadata por @Mikejmnez en https://github.com/pydap/pydap/pull/513
* Habilita caché cuando no se ejecuta consolidated-metadata por @Mikejmnez en https://github.com/pydap/pydap/pull/514
* Arreglos String por @Mikejmnez en https://github.com/pydap/pydap/pull/517
* Habilita opción para solicitar/omitir checksums por @Mikejmnez en https://github.com/pydap/pydap/pull/519
* Agrega referencias Parent para Groups (anidados) y BaseTypes (arreglos) por @Mikejmnez en https://github.com/pydap/pydap/pull/523
* Actualiza los hooks de pre-commit por @pre-commit-ci[bot] en https://github.com/pydap/pydap/pull/524
* Habilita desempaquetar respuestas desde httpx por @Mikejmnez en https://github.com/pydap/pydap/pull/527
* Habilita agrupar múltiples solicitudes de variables en una sola URL dap por @Mikejmnez en https://github.com/pydap/pydap/pull/525
* Asegura que consolidate_metadata y batch_mode estén bien integrados por @Mikejmnez en https://github.com/pydap/pydap/pull/530
* Mejora el manejo de Maps al consolidar metadatos por @Mikejmnez en https://github.com/pydap/pydap/pull/531
* Actualiza actions/checkout de 4 a 5 por @dependabot[bot] en https://github.com/pydap/pydap/pull/532
* Habilita cachear URLs en batch_mode, con fines de depuración, por @Mikejmnez en https://github.com/pydap/pydap/pull/533
* Impone checksums=True, pero expone la opción a usuarios por @Mikejmnez en https://github.com/pydap/pydap/pull/535


3.5.5
------
*Fecha de publicación: 2025-Abril-13*

* Actualiza la documentación por @Mikejmnez en #461 #462, #464, #465, #467, #469,
* Elimina archivo innecesario por @Mikejmnez en #463
* Establece `decode_times=False` al leer en paralelo por @Mikejmnez en #470
* Agrega python 3.13 a las pruebas por @Mikejmnez en #472
* Define dimensiones globales al iniciar el dataset por @Mikejmnez en #475
* Actualiza los hooks de pre-commit por @pre-commit-ci en #476
* Habilita caché de múltiples URLs dap4 y una clave de caché personalizada para respuestas dap de dimensiones por @Mikejmnez en #473
* Agrega metadatos de Python3.13 y corrige errores ortográficos por @Zeitsperre en #477
* Actualiza la referencia de BaseType a dimensiones en DAP2 por @Mikejmnez en #481
* Actualiza el handler netcdf para que sea consistente con el parser dmr al crear … por @Mikejmnez en #479
* Renombra datacube_urls a consolidate_metadata por @Mikejmnez en #483
* Corrige advertencia de prueba por @Mikejmnez en #484


3.5.4
------
*Fecha de publicación: 2025-Marzo-18*

* Actualiza los hooks de pre-commit por @pre-commit-ci en #431
* Elimina Webob del uso cliente de pydap. En su lugar usa la biblioteca requests, que maneja autenticación, por @Mikejmnez en #434
* Actualiza los hooks de pre-commit por @pre-commit-ci en #436
* `Nueva funcionalidad`: pydap ahora usa `request_cache` para inicializar una sesión. Por lo tanto, las respuestas ahora se pueden cachear por @Mikejmnez en #438
* Nueva propiedad `.grids()` para identificar todos los objetos grid dentro del dataset por @Mikejmnez en #446
* Bug corregido: reemplaza `dap2` por `http` al usar el esquema para determinar el protocolo dap por @Mikejmnez en #451
* Soporte para devolver un objeto de sesión como atributo de `pydap.dataset`. La sesión ahora puede ser recuperada por el usuario por @Mikejmnez en #447
* Recopila/proporciona más metadatos sobre nombres de dimensiones por variable por @Mikejmnez en #453
* Aplana atributos globales NC_GLOBAL y DODS_EXTRA heredados del parser das por @Mikejmnez en #455
* Cambia el valor predeterminado: `output_grid=False` ahora es el argumento predeterminado para `open_url` por @Mikejmnez en #457


3.5.3
------
*Fecha de publicación: 2025-Ene-6*

* Paralelismo mejorado para el lector de chunks de datos binarios. Esto se volvió un problema especialmente para datasets con muchos chunks muy pequeños. Ya no es el caso por @Mikejmnez en #419
* Limpieza de documentación por @Mikejmnez en #420
* Nuevo soporte para analizar dmr con variables String por @Mikejmnez en #423
* Nuevo soporte para que el parser dmr permita múltiples valores en un solo atributo por @Mikejmnez en #421
* Nuevo soporte para escapar espacios en blanco en nombres de Groups/Variables por @Mikejmnez en #426
* Soporte para decodificar el encabezado de chunk para establecer la longitud del DMR de forma genérica y la endianidad de los datos. Esto permite que pydap analice eficientemente respuestas dap DAP4 de TDS y Hyrax de forma genérica, sin lógica extra para distinguir qué servidor produjo la respuesta dap. Por @Mikejmnez en #428


3.5.2
------

*Fecha de publicación: 2024-Nov-19*


* Agrega badge de Zenodo por @Mikejmnez en https://github.com/pydap/pydap/pull/405
* Actualiza hooks de `pre-commit` por @pre-commit-ci en https://github.com/pydap/pydap/pull/408
* Agrega versiones más nuevas de `python` a los metadatos y flujos de trabajo de pruebas por @Mikejmnez en https://github.com/pydap/pydap/pull/410
* Incluye `cas-extras` como dependencias mínimas requeridas para usar pydap solo como cliente por @Mikejmnez en https://github.com/pydap/pydap/pull/413
* Actualiza la documentación, agregando información sobre DAP4 y Constraint Expressions bajo `Pydap as a Client` por @Mikejmnez en https://github.com/pydap/pydap/pull/414
* Parche rápido para analizar respuestas TDS DAP4, con mensaje de advertencia apropiado para usar dap2 en su lugar por @Mikejmnez en https://github.com/pydap/pydap/pull/415



3.5.1
-----

*Fecha de publicación: 2024-Oct-28*

- Soporte DAP4:
  * Mejora la descripción de Constraint Expressions en la documentación (incluye dimensiones compartidas) por @Mikejmnez en https://github.com/pydap/pydap/pull/357
  * Define dimensiones a nivel de `Group` por @Mikejmnez en https://github.com/pydap/pydap/pull/360
  * Crea método para generar objetos dap por @Mikejmnez en https://github.com/pydap/pydap/pull/362
  * Sirve datos nc4 con `Groups` por @Mikejmnez en https://github.com/pydap/pydap/pull/367
  * Función de objetos `get.Dap` (y una corrección) por @Mikejmnez en https://github.com/pydap/pydap/pull/373.
  * Permite dimensiones repetidas por @Mikejmnez en https://github.com/pydap/pydap/pull/381
  * Elimina `GridType` del handler netcdf por @Mikejmnez en https://github.com/pydap/pydap/pull/395
  * Analiza elementos de atributo con tipos atómicos en la raíz por @Mikejmnez en https://github.com/pydap/pydap/pull/403

- Instalación reducida de `pydap`:
  - Para usos de solo `client`, ejecuta: `pip install pydap`, o `conda install pydap` si usas `conda`.
  - Si necesitas usar el servidor de `pydap`, ejecuta: `pip install "pydap[server,netcdf]"`, o `conda install pydap-server`.

- Otros cambios:
  * Actualiza el archivo de logo y apunta a él por @Mikejmnez en https://github.com/pydap/pydap/pull/366
  * Reduce las dependencias requeridas para instalar por @Mikejmnez en https://github.com/pydap/pydap/pull/369
  * Actualiza readme por @Mikejmnez en https://github.com/pydap/pydap/pull/375 y https://github.com/pydap/pydap/pull/376
  * Workflows por @Mikejmnez en https://github.com/pydap/pydap/pull/377
  * Actualización de documentación por @Mikejmnez en https://github.com/pydap/pydap/pull/378
  * Permite el parser `dds` y `DMR` de datasets remotos con grupos `Flatten` (barras en el nombre) por @Mikejmnez en https://github.com/pydap/pydap/pull/399
  * Cambia variable para graficar y decodificar por @Mikejmnez en https://github.com/pydap/pydap/pull/383
  * Elimina espacios en blanco en archivo ci/env por @Mikejmnez en https://github.com/pydap/pydap/pull/386
  * Actualiza mamba-org/setup-micromamba de 1 a 2 por @dependabot en https://github.com/pydap/pydap/pull/384
  * Actualiza hooks de pre-commit por @pre-commit-ci en https://github.com/pydap/pydap/pull/387
  * Actualiza README.md por @Mikejmnez en https://github.com/pydap/pydap/pull/396


3.5.0
-----

*Fecha de publicación: 2024-Ago-16*

- Soporte DAP4:
  * Nuevo argumento extra para `client.open_url`: `protocol='dap2'|'dap4'`. El valor predeterminado es `protocol='dap2'`.
  * Permite escapar caracteres '[' y ']' al abrir datasets remotos con protocolo dap4 por @Mikejmnez en https://github.com/pydap/pydap/pull/310
  * Agrega un método tree para inspeccionar datos dentro de un dataset pydap por @Mikejmnez en https://github.com/pydap/pydap/pull/324
  * Simplifica el modelo Dataset en DAP4 por @Mikejmnez en https://github.com/pydap/pydap/pull/327
  * Analiza correctamente proyecciones (CEs) con Arrays en DAP4 por @Mikejmnez en https://github.com/pydap/pydap/pull/336
  * Iss339 por @Mikejmnez en https://github.com/pydap/pydap/pull/340
  * Analiza valores de atributo NaN en DMR (DAP4) por @Mikejmnez en https://github.com/pydap/pydap/pull/345
  * Define correctamente `named dimensions` a nivel `root` por @Mikejmnez en https://github.com/pydap/pydap/pull/348

- Actualizaciones generales:
  * Corrección de pruebas por @jgallagher59701 en https://github.com/pydap/pydap/pull/275
  * Limpia los workflows de pruebas por @owenlittlejohns en https://github.com/pydap/pydap/pull/283
  * `Import Mapping` desde `collections.abc` por @rbeucher en https://github.com/pydap/pydap/pull/272
  * Permite probar versiones más nuevas de python en MacOS imitando workflows de Ubuntu por @Mikejmnez en https://github.com/pydap/pydap/pull/293
  * Incluye plantillas para PRs e Issues, corrige enlaces rotos en la documentación y agrega dependabots por @Mikejmnez en https://github.com/pydap/pydap/pull/296
  * Actualiza `actions/setup-python` de 4 a 5 por @dependabot en https://github.com/pydap/pydap/pull/300
  * Actualiza `actions/checkout` de 3 a 4 por @dependabot en https://github.com/pydap/pydap/pull/301
  * Elimina dependencia de `six` (para python 2.7) por @Mikejmnez en https://github.com/pydap/pydap/pull/304
  * `Pydap` ahora usa `pyproject.toml` por @Mikejmnez en https://github.com/pydap/pydap/pull/307
  * Incluye `pre-commit` por @Mikejmnez en https://github.com/pydap/pydap/pull/309
  * Configura `pre-commit` en github actions por @Mikejmnez en https://github.com/pydap/pydap/pull/312
  * Actualiza `actions/setup-python` de 3 a 5 por @dependabot en https://github.com/pydap/pydap/pull/316
  * Actualiza `actions/checkout` de 3 a 4 por @dependabot en https://github.com/pydap/pydap/pull/317
  * Corrige #207: `Pydap` ahora puede usar `PasterApp` y servir datos por @Mikejmnez en https://github.com/pydap/pydap/pull/318
  * Incluye compatibilidad con Numpy=2.0 @Mikejmnez en https://github.com/pydap/pydap/pull/322
  * Elimina advertencias de deprecación por @Mikejmnez en https://github.com/pydap/pydap/pull/325
  * Apunta a la rama `main` en GH/workflows por @Mikejmnez en https://github.com/pydap/pydap/pull/330
  * Agrega notebook de autenticación por @Mikejmnez en https://github.com/pydap/pydap/pull/341
  * Corrección de documentación por @Mikejmnez en https://github.com/pydap/pydap/pull/342
  * Resuelve error de deprecación Numpy>1.25 por @Mikejmnez en https://github.com/pydap/pydap/pull/343
  * Incluye atributos numpy en BaseType para calcular arraysize en bytes (sin comprimir) por @Mikejmnez en https://github.com/pydap/pydap/pull/329
  * Moderniza la documentación con jupyter-books por @Mikejmnez en https://github.com/pydap/pydap/pull/337
  * Descubrimiento implícito de entry points por @Mikejmnez en https://github.com/pydap/pydap/pull/346


3.4.0
-----

*Fecha de publicación: 2023-Abril-5*

* Parche DAP4/DAS (#278)
  * Corrige un tipo que hacía que contenido DAP4 se ingiriera en un objeto DAP2 con malos resultados.
  * Retira pruebas para Python 3.6 porque ya no está disponible en ubuntu. Agrega pruebas para Python 3.10 y 3.11.
  * Elimina 3.7 y 3.8 de la matriz de versiones.
  * Corrige regex de test_response_error.
  * Corrige test_response_error para 3.10 y 3.9.
  * Cambia la versión de python_macro a 3.9.
  * Actualiza .gitignore para archivos de OSX Finder.

* Dap4 beta (#271)
  * Soporte inicial para DAP4.
  * Estos cambios son útiles, pero no representan conformidad del 100% con DAP4.

3.3.0
-----

*Fecha de publicación: 2022-Feb-1*

* Hay muchos cambios al pasar de 3.2.0 a 3.3.0

  - Fusiona pull request #259 desde pydap/ejh_readme: corrige enlaces de documentación en README.

  - Fusiona pull request #258 desde pydap/ejh_version: cambia la versión a 3.3.0.

  - Fusiona pull request #253 desde pydap/ejh_remove_python_2: intento inicial de eliminar soporte para python 2.

  - Fusiona pull request #209 desde shreddd/master: corrección para acelerar listados de directorios.

  - Fusiona pull request #257 desde pydap/ejh_macos_2: agrega macos a GitHub CI.

  - Fusiona la rama 'timeout' de github.com:cskarby/pydap.
  - Fusiona la rama 'float_inf' de github.com:d70-t/pydap en ejh_inf.

  - Fusiona pull request #247 desde pydap/ejh_warn2: corrige advertencias tostring.

  - Fusiona pull request #246 desde pydap/ejh_warn: corrige advertencias pytest.

  - Fusiona pull request #243 desde pydap/ejh_collections: importa ABC desde collections.abc en lugar de collections para compatibilidad con Python 3 (agregando más versiones de python).

  - Fusiona pull request #241 desde pydap/ejh_t1: agrega workflow de GitHub actions CI.

  - corrige pos arg (#225)

  - WIP: agrega user_charset arg (#223)

  - Agrega 'default_charset' a open_url, para servidores que no lo especifican (#222): pero sirven utf-8.

  - client: Bugfix - pasa session a funciones del servidor.
  - self.session se configuraba en None en lugar de usar el objeto session pasado.

  - client: pasa timeout desde open_url también a funciones del servidor: corrige pydap/pydap#220.

  - Maneja KeyErrors como se describe en issue #128 (#201).

  - No emite líneas DAS defectuosas (#195): corrige #194.
  - `sudo` ya no es necesario (#193): https://blog.travis-ci.com/2018-11-19-required-linux-infrastructure-migration

  - Evita aplicar scale factor para consistencia con dtype (#191).
  - Corrige #190.
  - Corrige Travis CI (#192).
  - Corrige PEP 479.
  - Corrige PEP8.
  - agrega entry point de handler netcdf (#179).
  - correcciones menores de documentación del cliente (#181).
  - agrega logo pydap (#178).

  - Fusiona pull request #177 desde tomkralidis/add-tomkralidis-to-contributors.

  - Prueba explícitamente instalaciones solo cliente (resuelve #120) (#124).
  0 Agrega una opción ``verify`` a ``open_url`` (#112).

  - Agrega una interfaz netcdf4-python para pruebas (#106).
  - Elimina funciones server-side en el servidor de desarrollo (#123).
  - Elimina entrada inexistente en el índice (#115).
  - hace que pydap sea el nombre canónico del proyecto (#174).
  - simplifica HTML (#144).
  - Corrige compresión gzip (#126) (#152).
  - agrega soporte para THREDDS Catalog XML (#136) (#138).
  - agrega soporte para THREDDS Catalog XML (#136).
  - agrega capacidad pydap.__version__ (#133) (#135).

  - Fusiona pull request #172 desde rsignell-usgs/patch-1.
  - Crea CODE_OF_CONDUCT.md.

  - Fusiona pull request #173 desde betodealmeida/fix_ci_35.
  - Corrige pruebas unitarias en Python 3.5.

  - Crea CODE_OF_CONDUCT.md.

  - Fusiona pull request #161 desde flackdl/patch-1.
  - Corrige enlace roto en README.

  - agrega archivo LICENSE (#142) (#143).

  - Maneja respuestas comprimidas con gzip (resuelve #126) (#127).
  - agrega requests a dependencias core (#145) (#120) (#146).
  - Corrige #121, corrige advertencias de deprecación e incorpora cambios flake8 (#159).
  - Corrige inconsistencia de nivel de título (#117).
  - Cierra #116.
  - Excluye el directorio de construcción de Sphinx de sdist (#114).
  - No requiere mock para Python 3.3 o posterior (#113).
  - `unittest.mock` está disponible desde Python 3.3.

  - Fusiona pull request #34 desde laliberte/merging/handlers.csv.
  - Fusiona el handler CSV en el repositorio principal.

  - Fusiona la rama 'release/3.2.2'.
  - Agrega PasteDeploy como dependencia opcional. Corrige #53.
  - Nueva forma de ejecutar un servidor Paste con Gunicorn. Corrige #52.

3.2.2
-----

*Fecha de publicación: 2017-Mayo-24*

* Python 3.3 ya no es compatible. Esto está alineado con otros proyectos similares (Numpy, Xarray, ...) y anticipa el fin de vida esperado de python 3.3 en septiembre de 2017.
* Mejoras del servidor
  * Fusiona pydap.handlers.netcdf en la base de código principal.
  * Agrega un servidor ligero de pruebas/desarrollo.
  * Reescribe la documentación del servidor para reflejar un mundo posterior a paster.
* Correcciones misceláneas de bugs
  * Asegura que el uso de Byte sea consistente con los estándares DAP2.
  * Corrige autenticación del cliente hacia CEDA del Reino Unido.
  * Corrige comunicación del cliente con servidores ERDDAP.
  * Corrige bug de regresión en model.GridType (#43).
  * Corrige bug donde la iteración no reemplaza previous_chunk.
  * Corrige bugs en el servidor de línea de comandos (#52 y #53).
* Corrige esquema de mapeo para SequenceType (PR #89)
  * Hace que todos los tipos sean un mapping y protege la semántica de mapping para datos de secuencia.
  * Convierte dict en StructureType a OrderedDict, cambiando el manejo de _original_keys (#3) y convierte test_model.py a semántica pytest (#82).
  * Actualiza documentación y docstrings. Agrega doctests automáticos básicos. Los doctests usan enteros para facilitar la integración continua.
  * 100% de cobertura de pruebas en src/pydap/model.py.
* Varias mejoras de la base de código
  * Transición de pruebas de nose a pytest.
  * Pruebas con flake8 en todas las versiones de Python.
* Agrega opción timeout a open_urls y open_dods.


3.2.1
-----

*Fecha de publicación: 2017-Mar-28*

* Correcciones del cliente PyDAP
  * Agrega workaround en el cliente al hacer solicitudes a servidores OPENDAP ESGF antiguos.
  * Corrige un bug donde mechanicalsoup no cerraba su navegador.
  * Agrega manejo para valores de -NaN.
  * Rehace la autenticación URS para usar la biblioteca requests.
  * Define un charset predeterminado al conectarse a servidores que no lo hacen.
* Correcciones de empaquetado
  * Mueve gunicorn a la lista de dependencias server_extras.
  * Agrega datos de prueba al tarball de lanzamiento.
* Mejoras de la base de código
  * Agrega linting/checking con flake8 a la base de código.
  * Mejora pruebas para autenticación del cliente.
  * Elimina soporte para Python < 2.7.
  * Convierte imports internos a relativos explícitos.
* Correcciones misceláneas de bugs
  * Corrige bug en fix_slices() cuando `stop` > len.
  * Corrige aplanamiento inesperado de arreglos rebanados (#41).
  * Corrige bug donde los atributos no se propagaban a estructuras anidadas (#75).


3.2.0
-----

*Fecha de publicación: 2016-Dic-01*

* Agrega algunas optimizaciones al servidor para secuencias DAP.
* Reescritura del cliente para que ahora pueda transmitir datos en tiempo real.
* Simplifica el diseño de handlers, eliminando detalles relacionados con DAP (para que los desarrolladores puedan enfocarse solo en el análisis de datos al crear nuevos handlers).
* Cobertura completa de pruebas e integración continua.
* Agrega soporte para versiones de Python 3.3 a 3.5.
* Agrega soporte para autenticación federada mediante Earth System Grid Federation (ESGF) y NASA User Registration System (URS).
* Corrige la respuesta HTML para mostrar todas las dimensiones de variables BaseType.

3.1.1
-----

*Fecha de publicación: 14-Nov-2013*

* Lanzamiento final hecho por Roberto De Almeida

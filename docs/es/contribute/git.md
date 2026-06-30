# Guía de control de versiones

Hay muchas formas de contribuir a un proyecto de código abierto. Como pydap ya está alojado en Github, recomendamos usar [Git](https://git-scm.com) para llevar el seguimiento de los cambios y contribuir al proyecto. Hay muchos tutoriales en línea sobre buenas prácticas con git, así que aquí damos un enfoque resumido. Asumiremos que tienes una cuenta de [GitHub](https://github.com) y que has iniciado sesión.

## Usar git y GitHub

Ve a [pydap](https://github.com/pydap/pydap) y haz un [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo). Si ya tienes un fork, asegúrate de que tu proyecto derivado esté actualizado con el proyecto remoto. Si no lo está, [sincroniza](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork) tu fork.


Abre tu terminal. Configura tu nombre de usuario de GitHub y dirección de correo electrónico con los siguientes comandos:

```shell
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

Crea un clon local de tu fork de la siguiente manera:

```shell
git clone https://github.com/<your_username_here>/pydap.git
```

Entra al directorio de tu clon local y configura un remoto que apunte al repositorio original:

```shell
cd pydap
git remote add upstream https://github.com/pydap/pydap
git fetch upstream/main
```

Una gran característica de git es la capacidad de trabajar en ramas al desarrollar un proyecto. Una rama ayuda a llevar el seguimiento de los cambios manteniendo una copia local del código remoto sin modificar. Para iniciar una rama y hacer una contribución a pydap:

```shell
git checkout -b <name_of_branch>
```

Ahora estás en una rama y puedes hacer cambios de forma segura en tu clon local. Para hacerlos visibles a otras personas contribuidoras, necesitas subir tu rama a tu proyecto derivado. Para lograrlo, ejecuta:

```shell
git push --set-upstream origin <name_of_branch>
```

Ahora puedes hacer cambios, crear commits y subirlos a tu proyecto derivado. Para crear un commit con tus cambios locales en la rama, ejecuta:

```shell
git add .
git commit -m 'Minimal message describing changes'
```

Esto creará un punto al que puedes volver. Cuando termines tus cambios, o quieras que tus colaboradores conozcan tu trabajo en el proyecto derivado, ejecuta:

```shell
git push
```

Puedes ir a tu directorio remoto en GitHub y encontrar tus cambios.

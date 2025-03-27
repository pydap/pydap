#!/bin/bash
set -e  # Exit on error

# Build English version
cd en
jupyter-book clean . --all
jupyter-book build .
cd ..
mkdir -p _build/html/en
rsync -a --delete en/_build/html/ _build/html/en/


# Build Spanish version
cd es
jupyter-book clean . --all
jupyter-book build .
cd ..
mkdir -p _build/html/es
rsync -a --delete es/_build/html/ _build/html/es/

# Create index.html to redirect to en/intro.html
echo '<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="refresh" content="0; url=en/intro.html">
    <title>Redirecting...</title>
</head>
<body>
    <p>If you are not redirected, <a href="en/intro.html">click here</a>.</p>
</body>
</html>' > index.html

# Copy index.html to the build directory
cp index.html _build/html/index.html


echo "Both versions of the documentations were built successfully!"
echo '

For English version:
1. Navigate to `docs` folder
2. Run the following on the terminal:

open _build/html/index.html

'


echo '
Para la version en Espanol:
1. Naviga al folder llamado `docs`
2. Ejecuta en la terminal lo siguiente:

open _build/html/es/intro.html

'

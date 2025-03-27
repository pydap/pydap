#!/bin/zsh
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

#### create redirects

# Define an associative array of redirects
typeset -A redirects
redirects=(
    "index.html" "en/intro.html"
    "intro.html" "en/intro.html"
    "how_to_install.html" "en/how_to_install.html"
    "get_started.html" "en/get_started.html"
    "5_minute_tutorial.html" "en/5_minute_tutorial.html"
    "notebooks/Authentication.html" "en/notebooks/Authentication.html"
    "notebooks/ECCO.html" "en/notebooks/ECCO.html"
    "notebooks/PACE.html" "en/notebooks/PACE.html"
    "notebooks/SWOT.html" "en/notebooks/SWOT.html"
    "notebooks/CMIP6.html" "en/notebooks/CMIP6.html"
    "PydapAsClient.html" "en/PydapAsClient.html"
    "DAP_Protocol.html" "en/DAP_Protocol.html"
    "ConstraintExpressions.html" "en/ConstraintExpressions.html"
    "responses.html" "en/responses.html"
    "server.html" "en/server.html"
    "handlers.html" "en/handlers.html"
    "developer/data_model.html" "en/developer/data_model.html"
    "developer/handlers.html" "en/developer/handlers.html"
    "developer/responses.html" "en/developer/responses.html"
    "guide_to_developer.html" "en/guide_to_developer.html"
    "contribute/git.html" "en/contribute/git.html"
    "contribute/contr_cod.html" "en/contribute/contr_cod.html"
    "contribute/contr_issues.html" "en/contribute/contr_issues.html"
    "contribute/contr_docs.html" "en/contribute/contr_docs.html"
)

# Loop through each key-value pair
for src dest in "${(@kv)redirects}"; do
    # Ensure the directory structure exists in _build/html
    mkdir -p "_build/html/$(dirname "$src")"

    # Create the redirect HTML file
    echo '<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="refresh" content="0; url='"$dest"'">
    <title>Redirecting...</title>
</head>
<body>
    <p>If you are not redirected, <a href="'"$dest"'">click here</a>.</p>
</body>
</html>' > "_build/html/$src"
done

echo "Redirect files created successfully."



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

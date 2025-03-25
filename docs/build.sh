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

echo "Both versions built successfully!"

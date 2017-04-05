# Define which file to ignore in tests:
collect_ignore = ["setup.py", "bootstrap.py", "docs/conf.py"]

# This line should be deleted once the online documentation is
# fixed:
collect_ignore.append("docs/client.rst")

# These lines should be deleted when all examples use local files:
collect_ignore.append("docs/index.rst")
collect_ignore.append("src/pydap/client.py")

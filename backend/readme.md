# Overview

The backend implementation for moneta.

The project is managed by pyproject.toml.

* To init the .venv  [install uv](https://docs.astral.sh/uv/getting-started/installation/) package manager"
* To create requirements.txt out of pyproject.toml:
    ```shell
    uv pip compile pyproject.toml --no-deps | grep -v '# via' > requirements.txt
    ```

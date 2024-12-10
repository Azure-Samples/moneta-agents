# Overview
Moneta frontend.

The project is managed by pyproject.toml.

* To init the .venv  install [uv package manager](https://docs.astral.sh/uv/getting-started/installation/) package manager"
* Run `uv sync`

# Prepare requirements.txt
* To create requirements.txt out of pyproject.toml:
    ```shell
    uv pip compile pyproject.toml --no-deps |\
        grep -v '# via' |\
        grep -v ipykernel > requirements.txt 
    ```

# Run locally

* Activate .venv as per above
* Configure .env as per sample.env

```shell
streamlit run app.py
```
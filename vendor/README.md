# vendor

`pyproject.toml` installs fbs (the [fman build system](https://build-system.fman.io/), Pro
edition) from `vendor/fbs-1.2.7.tar.gz`. The file is not committed: `tools/fbs_pro.py`
downloads it from `FBS_URL`, and `install.bat` / `update.bat` run that script before
`uv sync`. On macOS and Linux run it yourself:

    uv run --no-project python tools/fbs_pro.py
    uv sync

uv cannot install from `FBS_URL` directly: the URL has no archive extension, and uv does not
read the server's `Content-Disposition` filename the way pip does. The server names the file
`fbs_pro-1.2.7.tar.gz`; it is saved as `fbs-…` so the sdist filename matches the package name
`fbs`. `uv.lock` pins its sha256.

To update fbs: change `FBS_VERSION` in `tools/fbs_pro.py`, the `fbs` pin and the source path
in `pyproject.toml`, delete the old archive here, run `tools/fbs_pro.py`, then `uv lock`.

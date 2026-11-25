#!/usr/bin/env bash
# Build the working tree and verify both artifacts in separate, clean environments.
set -euo pipefail

unset CDPATH PYTHONPATH
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$repo_dir"
python_request=${UV_PYTHON:-$(cat .python-version)}

temp_root=$(cd -- "${TMPDIR:-/tmp}" && pwd -P)
if [[ "$temp_root" == "$repo_dir" || "$temp_root" == "$repo_dir/"* ]]; then
    printf 'Set TMPDIR to a directory outside the checkout.\n' >&2
    exit 1
fi
temp_dir=$(mktemp -d "$temp_root/networka-install.XXXXXX")
trap 'rm -rf -- "$temp_dir"' EXIT
build_dir="$temp_dir/dist"
uv build --no-sources --python "$python_request" --out-dir "$build_dir"

shopt -s nullglob
wheels=("$build_dir"/*.whl)
sdists=("$build_dir"/*.tar.gz)
if [[ ${#wheels[@]} != 1 || ${#sdists[@]} != 1 ]]; then
    printf 'Expected one wheel and one source archive in %s\n' "$build_dir" >&2
    exit 1
fi

# Use the new environment for each archive, even when the caller has one active.
verify_install() (
    artifact=$1
    export VIRTUAL_ENV="$temp_dir/$2"
    uv venv --python "$python_request" "$VIRTUAL_ENV"
    uv pip install --python "$VIRTUAL_ENV/bin/python" "$artifact"
    uv pip check --python "$VIRTUAL_ENV/bin/python"

    export NO_COLOR=1
    version=$(uv run --no-project --active --python "$VIRTUAL_ENV/bin/python" "$VIRTUAL_ENV/bin/nw" --version)
    help=$(uv run --no-project --active --python "$VIRTUAL_ENV/bin/python" "$VIRTUAL_ENV/bin/nw" --help)
    if [[ "$help" != *"Usage:"* || "$help" != *"--version"* ]]; then
        printf 'Expected CLI usage and the version option:\n%s\n' "$help" >&2
        exit 1
    fi
    uv run --no-project --active --python "$VIRTUAL_ENV/bin/python" python -I - "$artifact" "$version" <<'PY'
import hashlib
import os
import sys
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import yaml
from scrapli import Cli

import network_toolkit
from network_toolkit import NetworkaClient

artifact = Path(sys.argv[1])
environment = Path(os.environ["VIRTUAL_ENV"]).resolve()
assert Path(sys.prefix).resolve() == environment
assert Path(network_toolkit.__file__).resolve().is_relative_to(environment)
assert sys.argv[2] == f"Networka (nw) version {version('networka')}", sys.argv[2]

package = files("network_toolkit")
assert package.joinpath("py.typed").is_file(), "Missing py.typed"
platforms = ("arista_eos", "cisco_iosxe", "cisco_nxos", "juniper_junos", "mikrotik_routeros")
for platform in platforms:
    resource = package.joinpath("builtin_sequences", platform, "common.yml")
    assert yaml.safe_load(resource.read_text(encoding="utf-8"))["sequences"], platform

print(f"{artifact.name} sha256={hashlib.sha256(artifact.read_bytes()).hexdigest()}")
print(f"Python {sys.version.split()[0]}: {sys.argv[2]}")
print(
    f"CLI help, {NetworkaClient.__name__} and Scrapli {Cli.__name__} imports, "
    "py.typed, and built-in YAML passed."
)
PY
)

cd "$temp_dir"
verify_install "${wheels[0]}" wheel
verify_install "${sdists[0]}" sdist

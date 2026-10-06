#!/bin/sh
set -eu

python_bin=${GGEZ_PYTHON:-python3}
if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "ggez: Python 3.9+ is required. Install Python and retry." >&2
    exit 1
fi
if ! "$python_bin" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    echo "ggez: Python 3.9+ is required." >&2
    exit 1
fi

# A checkout can be installed without downloading unpublished changes.
if [ "${1:-}" = "--source" ]; then
    if [ -z "${2:-}" ] || [ ! -f "$2/scripts/install.py" ]; then
        echo "ggez: --source needs a ggez checkout." >&2
        exit 1
    fi
    exec "$python_bin" -B "$2/scripts/install.py" "$@"
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "ggez: curl is required to download the installer." >&2
    exit 1
fi
installer=$(mktemp "${TMPDIR:-/tmp}/ggez-install.XXXXXX")
trap 'rm -f "$installer"' EXIT HUP INT TERM
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
    https://raw.githubusercontent.com/varelycode/ggez/main/scripts/install.py > "$installer"
"$python_bin" -B "$installer" "$@"

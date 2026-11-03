#!/bin/bash
# Install into this checkout and configure an ADB profile without game inputs.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Darwin ]]; then
    echo "This script is for macOS." >&2
    exit 1
fi
maa_cli="${MAA_AGENT_CLI:-maa}"
for tool in "$maa_cli" adb; do
    if ! command -v "$tool" >/dev/null; then
        echo "Missing $tool. Install maa-cli and android-platform-tools with Homebrew first (see docs/macos.md)." >&2
        exit 1
    fi
done

if command -v uv >/dev/null; then
    if [[ ! -x .venv/bin/python ]]; then
        uv venv --python 3.12 .venv
    fi
    uv pip install --python .venv/bin/python -e .
else
    python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required; install uv or a newer Python"'
    if [[ ! -x .venv/bin/python ]]; then
        python3 -m venv .venv
    fi
    .venv/bin/python -m pip install -e .
fi

if [[ -n "${MAA_AGENT_CONFIG_DIR:-}" ]]; then
    export MAA_CONFIG_DIR="$MAA_AGENT_CONFIG_DIR"
fi
if [[ -n "${MAA_AGENT_DATA_DIR:-}" ]]; then
    export MAA_DATA_DIR="$MAA_AGENT_DATA_DIR"
fi

if ! "$maa_cli" dir resource >/dev/null 2>&1 || ! "$maa_cli" dir lib >/dev/null 2>&1; then
    "$maa_cli" install stable --batch
fi

# Configure through the JSON CLI; existing profiles are never overwritten.
if [[ $# -gt 1 ]]; then
    echo "Usage: bash scripts/setup_macos.sh [ADB_ADDRESS]" >&2
    exit 1
fi
if [[ $# -eq 1 ]]; then
    .venv/bin/python -m maa_agent setup-macos --address "$1"
else
    .venv/bin/python -m maa_agent setup-macos
fi
.venv/bin/python -m maa_agent doctor
echo "Ready. Log into the game, then run: .venv/bin/python -m maa_agent observe"

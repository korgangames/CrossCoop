#!/usr/bin/env bash
# Helper script to launch Nucleus Co-op using Wine on Linux
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/nucleus_coop" || exit 1

# Note: Nucleus Co-op requires .NET Framework 4.7.2+ and Visual C++ redistributables in the Wine prefix
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
echo "Launching Nucleus Co-op from $DIR/nucleus_coop with Wine (Prefix: $WINEPREFIX)..."
wine NucleusCoop.exe "$@"

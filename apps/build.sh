#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -rf build && mkdir build
javac --release 11 -cp "$(hadoop classpath)" -d build $(find src -name '*.java')
jar cf compression-apps.jar -C build .
echo "built $(pwd)/compression-apps.jar"

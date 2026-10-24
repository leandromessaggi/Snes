#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
JDK="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
g++ -std=c++17 -Wall -Wextra -Werror -fPIC -shared   "$ROOT/tests/integration/mock_libretro.cpp" -o "$TMP/libmock_snes.so"
g++ -std=c++17 -Wall -Wextra -Werror -fPIC -shared -pthread   -I "$JDK/include" -I "$JDK/include/linux"   "$ROOT/app/src/main/cpp/core_bridge.cpp" -o "$TMP/libdesert_bridge.so" -ldl
mkdir -p "$TMP/classes"
javac -d "$TMP/classes"   "$ROOT/tests/integration/java/br/com/desertstrike/NativeCore.java"   "$ROOT/tests/integration/java/br/com/desertstrike/JniSmokeJava.java"
java -Djava.library.path="$TMP" -cp "$TMP/classes" br.com.desertstrike.JniSmokeJava "$TMP/libmock_snes.so"

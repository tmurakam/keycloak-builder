#!/usr/bin/env bash
# Build an already-checked-out Keycloak source tree.
#
# Usage:
#   ./build.sh <path-to-keycloak-checkout> [extra ./mvnw args...]
#
# Examples:
#   ./build.sh ~/src/keycloak
#   ./build.sh ~/src/keycloak -rf :keycloak-saml-adapter-galleon-pack
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path-to-keycloak-checkout> [extra ./mvnw args...]" >&2
  exit 1
fi

KEYCLOAK_DIR="$1"
shift

cd "$KEYCLOAK_DIR"

# docs/guides copies its own generated output into itself on every non-clean
# rebuild, nesting target/generated-guides one level deeper each time until
# it fills the disk. Wipe it before every build since we don't run "clean".
rm -rf docs/guides/target

REF="$(git rev-parse --abbrev-ref HEAD)"
LOG_FILE="build-${REF//\//_}-$(date +%Y%m%d-%H%M%S).log"

java -version
./mvnw -v

echo "Building $REF ... log: $LOG_FILE"
# No "clean" on purpose: re-running after a partial failure should reuse
# whatever already built successfully instead of starting over.
./mvnw install -DskipTests -Pdistribution "$@" 2>&1 | tee "$LOG_FILE"

echo
echo "Done. Distribution ZIP:"
find quarkus/dist/target -maxdepth 1 -name '*.zip'

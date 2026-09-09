#!/bin/bash
# invenio-stats-dashboard JS tests (pnpm). From the monorepo, prefer
# ``./run-tests.sh --js-only`` / ``scripts/run-js-suites.sh`` which also run
# the root suite.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
pnpm run test "$@"

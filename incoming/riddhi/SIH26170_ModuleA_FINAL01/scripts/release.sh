#!/usr/bin/env bash
# The release step. Runs ONCE, after two canonical analysis runs have been compared.
#
#   scripts/release.sh <release-root> <other-run-results-dir>
set -euo pipefail
R="${1:?usage: release.sh /path/to/release /path/to/other-run/results}"
OTHER="${2:?path to the second independent run results directory}"
export SIH26170_RELEASE="$R"
python3 scripts/19_reproducibility_check.py --a results --b "$OTHER" \
        --out results/19_reproducibility.csv
python3 scripts/18_build_packets.py --release "$R"
python3 scripts/10_verify_claims.py --with-packets
# The manifest goes after the packet ledger so it records the COMPLETE claim count.
# Stage 18 reads its test count from 00_selfcheck.csv rather than the manifest, which
# is what lets this order work without a cycle.
python3 scripts/11_release_manifest.py --release "$R" >/dev/null
# Then build the packets once more. The owner packet contains a copy of the release,
# including the manifest, so without this pass his archive would depend on whether it
# was built before or after the manifest was written - and an archive whose hash moves
# on a rebuild cannot be verified by whoever receives it. The other five are already
# idempotent; this pass leaves them byte-identical.
python3 scripts/18_build_packets.py --release "$R" >/dev/null
echo "release complete"

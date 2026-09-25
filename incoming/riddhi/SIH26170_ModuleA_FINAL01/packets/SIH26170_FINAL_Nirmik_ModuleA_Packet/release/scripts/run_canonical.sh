#!/usr/bin/env bash
# The canonical ANALYSIS run. Everything that reads the dataset and writes to results/.
#
# Deliberately stops before the release steps. Packets and the release manifest embed
# the reproducibility verdict, which is produced by COMPARING two of these runs — so a
# run that also built packets could never be compared against another one. Analysis is
# what gets compared; release is what happens once, afterwards, with the verdict in hand.
#
#   scripts/run_canonical.sh <release-root> [<module-b-packet-root>]
set -euo pipefail
R="${1:?usage: run_canonical.sh /path/to/SIH26170_FINAL_RELEASE_01 [/path/to/moduleB/packet]}"
MB="${2:-}"
export SIH26170_RELEASE="$R"
python3 run_all.py --release "$R"
python3 scripts/09_evaluate_holdout.py --release "$R"
for cap in 0.01 0.03; do
  python3 scripts/04_nested_validation.py --release "$R" --cap "$cap" >/dev/null
  cp results/04_nested_validation.csv "results/04_nested_validation_cap${cap#0.}.csv"
  cp results/04_selected_weights_per_fold.csv "results/04_selected_weights_cap${cap#0.}.csv"
done
python3 scripts/04_nested_validation.py --release "$R" >/dev/null   # canonical: shipped budget
[ -n "$MB" ] && python3 scripts/15_fusion_dryrun.py --module-b-packet "$MB"
python3 scripts/17_provenance.py
rm -rf packets                      # so the ledger never depends on a previous build
python3 scripts/10_verify_claims.py
echo "canonical analysis run complete"

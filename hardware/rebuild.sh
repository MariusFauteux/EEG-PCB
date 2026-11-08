#!/usr/bin/env bash
# Regenerate the Rev C schematic and every check output from source.
# Usage: hardware/rebuild.sh   (from anywhere; needs ../.venv and KiCad 10 or later for the footprint library)
set -euo pipefail
HW="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-$HW/../.venv/bin/python}"
if [[ -z "${KICAD_CLI:-}" ]]; then
  KICAD_CLI="$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)"
fi
SCH="$HW/EEG_RevC.kicad_sch"
cd "$HW"
echo "== build schematic";  "$PY" scripts/build.py
echo "== export netlist";   "$KICAD_CLI" sch export netlist --format kicadxml -o checks/netlist.xml "$SCH" 2>/dev/null
echo "== ERC";              "$KICAD_CLI" sch erc -o checks/erc.rpt "$SCH" 2>/dev/null | tail -1
echo "== SVG previews";     rm -rf preview && "$KICAD_CLI" sch export svg -o preview "$SCH" >/dev/null 2>&1
echo "== netlist checks";   "$PY" scripts/validate.py
echo "== footprint audit";  "$PY" scripts/check_footprints.py
echo "== corner review";    "$PY" scripts/review_corners.py | grep -E "^(FAIL|OPEN)|rules" ; "$PY" -c "import json;d=json.load(open('checks/corner_review.json'));r=d['rules'];print(sum(x['ok'] for x in r),'of',len(r),'corner rules pass');exit(0 if all(x['ok'] for x in r) else 1)"
echo "== BOM cost";         "$PY" scripts/bom_cost.py
echo "== input and REF analysis"; "$PY" scripts/analyze_inputs.py | grep -E "^(PASS|FAIL)"
echo "== backfeed analysis"; "$PY" scripts/analyze_backfeed.py | grep -E "^(PASS|FAIL)"
echo "== BIAS loop analysis"; "$PY" scripts/analyze_bias.py | grep -E "^(C4_TI|C5_sel)"
echo "== timing analysis";   "$PY" scripts/analyze_timing.py >/dev/null && echo "checks/timing_analysis.json written"
echo "== power analysis";    "$PY" scripts/analyze_power.py | grep -E "^(PASS|FAIL)"
echo "== host codec tests"; (cd "$HW/../host" && "$PY" -m unittest -q test_record_format test_event_timing 2>&1 | tail -1)

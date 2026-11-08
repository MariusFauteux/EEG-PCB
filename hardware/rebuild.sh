#!/usr/bin/env bash
# Regenerate the Rev C schematic and every check output from source.
# Usage: hardware/rebuild.sh   (from anywhere; needs ../.venv and KiCad 9 or later)
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
echo "== input analysis";   "$PY" scripts/analyze_inputs.py >/dev/null && echo "checks/input_analysis.json written"
echo "== host codec tests"; (cd "$HW/../host" && "$PY" -m unittest -q test_record_format 2>&1 | tail -1)

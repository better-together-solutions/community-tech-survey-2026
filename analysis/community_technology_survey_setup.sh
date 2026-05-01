#!/usr/bin/env bash
# community_technology_survey_setup.sh
# Install analysis dependencies and verify input file.
# Run once before first analysis.
#
# Usage:
#   ./analysis/community_technology_survey_setup.sh [path/to/survey.xlsx]
#   ./analysis/community_technology_survey_setup.sh  # uses latest in data/original/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Community Technology Survey — Environment Setup ==="
echo "Repository: ${REPO_ROOT}"
echo ""

# ── 1. Python version check ──────────────────────────────────────────────────
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
  echo "ERROR: python3 not found"; exit 1
fi
PY_VER=$($PYTHON --version 2>&1)
echo "Python: ${PY_VER}"

# ── 2. Install pinned dependencies ───────────────────────────────────────────
echo ""
echo "Installing dependencies from requirements.txt..."
$PYTHON -m pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"
echo "Dependencies installed."

# ── 3. Verify installed packages ─────────────────────────────────────────────
echo ""
echo "Verifying packages:"
$PYTHON -c "
import pandas, matplotlib, seaborn, wordcloud, scipy, numpy, openpyxl, pingouin, krippendorff, markdown
print(f'  pandas       {pandas.__version__}')
print(f'  matplotlib   {matplotlib.__version__}')
print(f'  seaborn      {seaborn.__version__}')
print(f'  scipy        {scipy.__version__}')
print(f'  numpy        {numpy.__version__}')
print(f'  openpyxl     {openpyxl.__version__}')
print(f'  pingouin     {pingouin.__version__}')
print(f'  krippendorff {krippendorff.__version__}')
print(f'  markdown     {markdown.__version__}')
print('  wordcloud    ok')
print('All required packages verified.')
"

# ── 4. Verify / locate input file ────────────────────────────────────────────
echo ""
INPUT_FILE="${1:-}"
if [ -z "$INPUT_FILE" ]; then
  INPUT_FILE=$(ls -t "${REPO_ROOT}/data/original/"*.xlsx 2>/dev/null | head -1 || true)
fi

if [ -z "$INPUT_FILE" ]; then
  echo "WARNING: No .xlsx input file found in data/original/"
  echo "  Copy the survey export to: ${REPO_ROOT}/data/original/"
  echo "  Then re-run setup or pass the path as an argument."
else
  echo "Input file: ${INPUT_FILE}"
  SHA256=$(sha256sum "${INPUT_FILE}" | awk '{print $1}')
  echo "SHA256: ${SHA256}"
  ROW_COUNT=$($PYTHON -c "
import openpyxl
wb = openpyxl.load_workbook('${INPUT_FILE}')
ws = wb.active
print(ws.max_row - 1, 'data rows,', ws.max_column, 'columns')
")
  echo "Contents: ${ROW_COUNT}"
fi

echo ""
echo "=== Setup complete. ==="
echo ""
echo "To run the full analysis pipeline:"
echo "  python3 analysis/community_technology_survey_analysis.py all \\"
echo "    --input data/original/<survey>.xlsx"
echo ""
echo "To check privacy compliance:"
echo "  python3 analysis/community_technology_survey_privacy.py --run-id <run_id>"

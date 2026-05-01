# Reproducibility Guide

**Community Technology Survey — Better Together Solutions, May 2026**

This document provides complete step-by-step instructions for independently replicating all reported findings. Any researcher with Python 3.10+ and access to an LLM API can replicate the full analysis.

---

## What Is Reproduced

| Component | Reproducible? | Notes |
|-----------|--------------|-------|
| All quantitative statistics | Fully (deterministic) | Fixed seed = 42; exact library versions pinned |
| All visualisations | Fully (deterministic) | Same seed, same palette |
| Qualitative codes and themes | Approximately | LLM outputs vary slightly across runs; prompts are fixed |
| Intercoder reliability (α_K) | Approximately | Depends on LLM sampling |
| Published report (HTML) | Fully, given above | Assembled from JSON outputs |

**Note on qualitative reproducibility.** LLM outputs are stochastic. The *prompts* are the fixed, reproducible artifact. A second researcher using identical prompts and the same model should produce qualitatively similar but not byte-for-byte identical themes. This is consistent with Braun & Clarke (2021): themes are researcher constructions, and the prompts define the analytical lens.

---

## Requirements

- Python 3.10 or later
- Ollama (for qualitative analysis): https://ollama.com
  - Required model: `llama3.2:latest` (or configure via `--ollama-model`)
  - Default endpoint: `http://localhost:11435` (configure via `OLLAMA_HOST`)
- For quantitative analysis only: Ollama is **not required**

---

## Step-by-Step Replication

### Step 0: Clone the repository

```bash
git clone <repo-url>
cd community-tech-survey-2026
```

### Step 1: Copy the survey data

Copy the survey Excel export to `data/original/`:

```bash
cp /path/to/survey.xlsx data/original/
```

The file used in the original analysis:
- **Filename:** `export-community_technology_survey-2026-04-14-23-01-37.xlsx`
- **SHA256:** _(see `output/<run_id>/audit/manifest.json` → `input.sha256`)_
- **Rows:** 112 responses (67 complete, 45 partial)
- **Columns:** 115

### Step 2: Install dependencies

```bash
chmod +x analysis/community_technology_survey_setup.sh
./analysis/community_technology_survey_setup.sh
```

Or manually:

```bash
pip install -r analysis/requirements.txt
```

### Step 3: (Optional) Start Ollama for qualitative analysis

```bash
ollama serve
ollama pull llama3.2:latest
```

If using a different Ollama host or model, set environment variables:

```bash
export OLLAMA_HOST=http://localhost:11435
export OLLAMA_MODEL=llama3.2:latest
```

### Step 4: Run the full pipeline

```bash
python3 analysis/community_technology_survey_analysis.py all \
  --input data/original/export-community_technology_survey-2026-04-14-23-01-37.xlsx
```

This runs all stages sequentially and prints the run ID. The full run takes approximately 15–45 minutes depending on LLM speed.

### Step 5: Run only quantitative analysis (no LLM required)

```bash
# Ingest
python3 analysis/community_technology_survey_analysis.py ingest \
  --input data/original/<survey>.xlsx

# Quantitative analysis
python3 analysis/community_technology_survey_analysis.py quant \
  --run-id <run_id_from_ingest>

# Visualise
python3 analysis/community_technology_survey_analysis.py visualize \
  --run-id <run_id>

# Assemble report (qual sections will show placeholder text)
python3 analysis/community_technology_survey_analysis.py report \
  --run-id <run_id>

# Render HTML
python3 analysis/community_technology_survey_analysis.py render \
  --run-id <run_id>
```

### Step 6: Verify privacy compliance

```bash
python3 analysis/community_technology_survey_privacy.py \
  --run-id <run_id>
```

Exit code 0 = passes privacy checks. Exit code 1 = privacy requirements not met.

### Step 7: Check output checksums

```bash
# Verify all outputs match the published SHA256SUMS
sha256sum --check output/package/SHA256SUMS
```

---

## Output Structure

```
output/<run_id>/
  audit/
    manifest.json       # SHA256 of all inputs and outputs
    run.jsonl           # Timestamped event log
    privacy_report.json # K-anonymity and PII check results
  data/
    raw.csv             # PII-free row-for-row export
    normalized.json     # Typed, alias-renamed data
  quant/
    quant_results.json  # All quantitative statistics
  qual/
    <q_col>.json        # Per-question codes, themes, IRR
    irr_results.json    # Krippendorff's alpha per question
  charts/
    *.png               # All generated charts
  report.md             # Source markdown report
  report.html           # Standalone HTML (charts embedded)
  package/
    SHA256SUMS          # Checksums of all tracked files
```

---

## Verifying a Specific Statistic

Every statistic in the report traces to a key in `output/<run_id>/quant/quant_results.json`.

Example: to verify the mean tool satisfaction score:
```python
import json
with open("output/<run_id>/quant/quant_results.json") as f:
    q = json.load(f)
print(q["q5_tool_satisfaction"]["mean"])   # → e.g., 3.646
print(q["q5_tool_satisfaction"]["bootstrap_95ci_mean"])
```

---

## Citing This Work

```
Better Together Solutions. (2026). Community Technology Survey: Community demand
and trust conditions for a platform co-operative (Version 1.0) [Data set and report].
https://github.com/bts/<repo>

Analysis code: MIT License
Data and report: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
```

---

## Questions and Challenges

To raise a question, challenge a finding, or report a replication discrepancy:
- Open an issue in this repository
- Email rob@bettertogethersolutions.com
- We commit to responding to substantive methodological challenges within 30 days

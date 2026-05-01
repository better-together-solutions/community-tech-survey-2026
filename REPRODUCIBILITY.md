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
git clone https://github.com/better-together-solutions/community-tech-survey-2026
cd community-tech-survey-2026
```

### Step 1: Copy the survey data

Copy the survey Excel export to `data/original/`:

```bash
cp /path/to/survey.xlsx data/original/
```

The file used in the original analysis (full dataset):
- **Filename:** `export-community_technology_survey-2026-05-01-00-08-26.xlsx`
- **SHA256:** `7e34c488746cd6f1a3b92b0d00437a20382d618e383af6507d55183924b05d4e`
- **Rows:** 137 responses (80 complete, 57 partial)
- **Columns:** 115

An earlier partial export is also retained for reference:
- **Filename:** `export-community_technology_survey-2026-04-14-23-01-37.xlsx`
- **SHA256:** `27332bd6f4d8b6ba2fc7b5878638a5a9bf1baa4b998b242708bad0437aa5bd64`
- **Rows:** 112 responses (67 complete, 45 partial)

Both files are listed in `data/checksums/SHA256SUMS`.

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
  --input data/original/export-community_technology_survey-2026-05-01-00-08-26.xlsx
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

### Step 7: Check input and sanitized dataset checksums

```bash
# Verify input files and sanitized dataset against published checksums
sha256sum --check data/checksums/SHA256SUMS
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
    alt_text.json       # Accessibility alt text + data tables for each chart
  report_part1.md       # Quantitative report (source markdown)
  report_part1.html     # Quantitative report (standalone HTML, charts embedded)
  report_part2.md       # Qualitative report (source markdown)
  report_part2.html     # Qualitative report (standalone HTML)
  ce_page_blocks.json   # CE page_block IDs for --update-existing publishes
```

---

## Verifying a Specific Statistic

Every statistic in the report traces to a key in `output/<run_id>/quant/quant_results.json`.

Example: to verify the mean tool satisfaction score:
```python
import json
with open("output/<run_id>/quant/quant_results.json") as f:
    q = json.load(f)
print(q["q5_tool_satisfaction"]["mean"])   # → 3.8 (N=80 completed responses)
print(q["q5_tool_satisfaction"]["bootstrap_95ci_mean"])
```

---

## Citing This Work

```
Better Together Solutions. (2026). Community Technology Survey: Community demand
and trust conditions for a platform co-operative (Version 1.0) [Data set and report].
https://github.com/better-together-solutions/community-tech-survey-2026

Analysis code: MIT License
Data and report: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
```

---

## Questions and Challenges

To raise a question, challenge a finding, or report a replication discrepancy:
- Open an issue in this repository
- Email rob@bettertogethersolutions.com
- We commit to responding to substantive methodological challenges within 30 days

---

## Qualitative Tranche Reproducibility Note

The qualitative analysis (Part 2) is **not fully deterministic** due to the use of a local LLM (Ollama `llama3.2:latest`) for initial theme extraction. LLM outputs vary between runs even with `temperature=0`, due to floating-point non-determinism across hardware and model versions.

**What this means for replication:**
- Theme *labels* may differ between runs; theme *substance* (content, representative quotes) is stable
- Intercoder reliability (Krippendorff's alpha) was computed by comparing two independent LLM passes; reported values (−0.14 to 0.37) are specific to the original run
- The underlying verbatim quotes are deterministic — they are drawn directly from the sanitized survey data
- The quantitative analysis (Part 1) is fully deterministic and replicable to the bit level

**Recommended practice:** When replicating the qualitative analysis, treat LLM outputs as a starting point for human analyst review rather than ground truth. Compare theme substance (not labels) to the published codebook (`docs/codebook.md`).

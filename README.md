# Community Technology Survey 2026

**Community demand and trust conditions for a platform co-operative**
Better Together Solutions (BTS) | Newfoundland & Labrador, Canada | May 1, 2026

[![License: CC BY 4.0](https://img.shields.io/badge/Data%20%26%20Report-CC%20BY%204.0-blue)](https://creativecommons.org/licenses/by/4.0/)
[![License: MIT](https://img.shields.io/badge/Code-MIT-green)](LICENSE-CODE)

---

## About This Repository

This repository is the complete, self-contained publication package for the BTS Community Technology Survey, released on May Day 2026. It contains:

- **Survey data** — anonymised (k-anonymised, PII-free) dataset
- **Analysis code** — full Python pipeline, reproducible
- **Report** — `output/report.html` (standalone, all charts embedded)
- **Methodology** — full statistical and qualitative methods documentation
- **Privacy assessment** — PIPEDA compliance and k-anonymity verification
- **Codebook** — qualitative coding prompts published verbatim
- **Reproducibility guide** — step-by-step replication instructions

## Quick Start

```bash
./analysis/community_technology_survey_setup.sh
python3 analysis/community_technology_survey_analysis.py all \
  --input data/original/<survey>.xlsx
open output/<run_id>/report.html
```

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for full instructions.

## Repository Structure

```
community-tech-survey-2026/
  analysis/
    community_technology_survey_analysis.py   # Main pipeline
    community_technology_survey_privacy.py    # Privacy checks
    community_technology_survey_setup.sh      # Dependency install
    requirements.txt                          # Pinned versions
  data/
    original/      # Raw xlsx exports (not in public repo)
    sanitized/     # Published k-anonymised dataset
    checksums/     # SHA256SUMS
  docs/
    methodology.md    # Statistical and qualitative methods
    codebook.md       # Qualitative coding prompts (operational codebook)
    privacy.md        # Privacy impact assessment
    limitations.md    # Limitations and threats to validity
  schemas/
    quant_results.schema.json
    qual_results.schema.json
  output/           # Generated reports and analysis (gitignored except package/)
  REPRODUCIBILITY.md
  README.md
```

## Key Findings

See `output/report.html` for the full report. Headlines:
- N = 112 responses (67 complete); 8 sector types
- Strong support for community ownership: majority rate it "very" or "extremely" important
- Co-operative model increases trust and adoption likelihood for a large majority
- Top platform priority: accessibility and ease of use

## Licence

- **Data and report:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — you may share and adapt with attribution
- **Analysis code:** [MIT](LICENSE-CODE)

## Citation

```
Better Together Solutions. (2026). Community Technology Survey: Community demand
and trust conditions for a platform co-operative. Newfoundland & Labrador, Canada.
https://github.com/bts/community-tech-survey-2026
```

## Contact

rob@bettertogethersolutions.com | Better Together Solutions

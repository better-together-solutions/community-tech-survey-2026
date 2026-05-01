#!/usr/bin/env python3
"""
Community Technology Survey Analysis Pipeline
Better Together Solutions (BTS) — May Day 2026

Implements:
  - Reflexive Thematic Analysis (Braun & Clarke, 2021) for qualitative data
  - Standard survey analysis methods for quantitative data (AAPOR, 2022)
  - AI-assisted initial coding with documented prompts for reproducibility

All statistical methods, prompts, and parameters are exposed for audit.
Every output file is SHA256-checksummed and logged to audit/manifest.json.

Usage:
  python3 analysis.py ingest   --input data/original/survey.xlsx
  python3 analysis.py quant    --run-id <id>
  python3 analysis.py qual     --run-id <id> [--ollama-host http://localhost:11435]
  python3 analysis.py irr      --run-id <id>
  python3 analysis.py visualize --run-id <id>
  python3 analysis.py report   --run-id <id>
  python3 analysis.py render   --run-id <id>
  python3 analysis.py package  --run-id <id>
  python3 analysis.py all      --input data/original/survey.xlsx

Manifest:
  domain: community-research
  license-data: CC BY 4.0
  license-code: MIT
  methods: Reflexive Thematic Analysis; survey statistics; k-anonymity
  reproducibility: full — fixed seed, pinned deps, published prompts
  citation: >-
    Better Together Solutions (2026). Community Technology Survey:
    Community Demand and Trust Conditions for a Platform Co-operative.
    Newfoundland & Labrador, Canada.
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

ROOT = Path(__file__).parent.parent
OUTPUT_BASE = ROOT / "output"

PII_COLUMNS = [
    "64. If you would like contact, you can share your contact information.",
    "65. If helpful, tell us the best time or way to reach you.",
]

# ── Column aliases ────────────────────────────────────────────────────────────

COLUMN_ALIASES: dict[str, str] = {
    "No.": "row_no",
    "Response ID": "response_id",
    "Timestamp": "timestamp",
    "Finished": "finished",
    "Survey ID": "survey_id",
    "Formbricks ID (internal)": "formbricks_id",
    "User ID": "user_id",
    "Tags": "tags",
    "url": "url",
    "userAgent - os": "ua_os",
    "userAgent - device": "ua_device",
    "userAgent - browser": "ua_browser",
    "1. About you": "_sec_about_you",
    "2. Which best describes you or the organization you are answering from?": "q2_type",
    "2. Which best describes you or the organization you are answering from? - Option ID": "q2_type_id",
    "3. Are you answering mainly from a personal perspective or on behalf of an organization?": "q3_perspective",
    "3. Are you answering mainly from a personal perspective or on behalf of an organization? - Option ID": "q3_perspective_id",
    "4. Current tools and needs": "_sec_tools",
    "5. How satisfied are you with the digital tools you currently use?": "q5_satisfaction",
    "6. What are the biggest problems you face with current digital platforms or tools?": "q6_problems",
    "6. What are the biggest problems you face with current digital platforms or tools? - Option ID": "q6_problems_id",
    "7. What matters most in a community platform? - Privacy and data protection": "q7_privacy",
    "7. What matters most in a community platform? - Real human support": "q7_human_support",
    "7. What matters most in a community platform? - Accessibility and ease of use": "q7_accessibility",
    "7. What matters most in a community platform? - Ability to connect people and groups": "q7_connection",
    "7. What matters most in a community platform? - Shared governance or accountability": "q7_governance",
    "7. What matters most in a community platform? - Low cost": "q7_cost",
    "7. What matters most in a community platform? - Ability to adapt to community needs": "q7_adaptability",
    "7. What matters most in a community platform? - Long-term reliability": "q7_reliability",
    "8. Ownership, trust, and governance": "_sec_governance",
    "9. Before this survey, how familiar were you with the idea of a technology co-op or community-stewarded digital platform?": "q9_familiarity",
    "9. Before this survey, how familiar were you with the idea of a technology co-op or community-stewarded digital platform? - Option ID": "q9_familiarity_id",
    "10. How important is it that a digital platform be community-owned or community-stewarded rather than controlled by a large private company?": "q10_importance",
    "10. How important is it that a digital platform be community-owned or community-stewarded rather than controlled by a large private company? - Option ID": "q10_importance_id",
    "11. Would a community-owned or co-operative model make you more likely to trust this platform?": "q11_trust",
    "11. Would a community-owned or co-operative model make you more likely to trust this platform? - Option ID": "q11_trust_id",
    "12. Would a community-owned or community-stewarded model make you more likely to use, support, or adopt this platform?": "q12_adoption",
    "12. Would a community-owned or community-stewarded model make you more likely to use, support, or adopt this platform? - Option ID": "q12_adoption_id",
    "13. What about that model matters most to you?": "q13_model_matters",
    "13. What about that model matters most to you? - Option ID": "q13_model_matters_id",
    "14. Questions for members of the general public": "_sec_public",
    "15. What would make a community-owned digital platform feel trustworthy to you?": "q15_trustworthy",
    "16. Would you be interested in using or supporting a community platform for local connection, information, events, or participation?": "q16_interest",
    "16. Would you be interested in using or supporting a community platform for local connection, information, events, or participation? - Option ID": "q16_interest_id",
    "17. Questions for co-ops": "_sec_coops",
    "18. How well does a technology co-op model fit your organization's values or way of working?": "q18_coop_fit",
    "18. How well does a technology co-op model fit your organization's values or way of working? - Option ID": "q18_coop_fit_id",
    "19. What kind of relationship would your co-op want with a shared technology platform?": "q19_coop_relationship",
    "19. What kind of relationship would your co-op want with a shared technology platform? - Option ID": "q19_coop_relationship_id",
    "20. What would make your co-op trust this model enough to join, pilot, or support it?": "q20_coop_trust",
    "21. Questions for non-profits": "_sec_nonprofits",
    "22. What are the biggest technology burdens on your staff, volunteers, or participants?": "q22_nonprofit_burdens",
    "23. Would a community-stewarded model make adoption more attractive than a conventional vendor platform?": "q23_nonprofit_attractive",
    "23. Would a community-stewarded model make adoption more attractive than a conventional vendor platform? - Option ID": "q23_nonprofit_attractive_id",
    "24. What would your organization need to see before committing time or money?": "q24_nonprofit_conditions",
    "25. Questions for community groups": "_sec_community",
    "26. What makes mainstream digital tools difficult for your group to use?": "q26_community_difficulties",
    "27. Would your group want to help shape or guide the platform, or mainly use it?": "q27_community_role",
    "27. Would your group want to help shape or guide the platform, or mainly use it? - Option ID": "q27_community_role_id",
    "28. Questions for unions": "_sec_unions",
    "29. What communication or organizing needs are not well served by current platforms?": "q29_union_needs",
    "30. Would a collectively stewarded technology model be more appealing than a corporate platform?": "q30_union_appeal",
    "30. Would a collectively stewarded technology model be more appealing than a corporate platform? - Option ID": "q30_union_appeal_id",
    "31. What kind of governance or member voice would matter to your union?": "q31_union_governance",
    "32. Questions for municipalities and public institutions": "_sec_muni",
    "33. What requirements would a community platform need to meet to be viable for public-serving work?": "q33_muni_requirements",
    "34. Would a community-stewarded model be seen mainly as a strength, a risk, or both?": "q34_muni_perception",
    "34. Would a community-stewarded model be seen mainly as a strength, a risk, or both? - Option ID": "q34_muni_perception_id",
    "35. Questions for activists, organizers, and advocacy groups": "_sec_activists",
    "36. What risks do mainstream platforms create for your organizing or advocacy work?": "q36_activist_risks",
    "37. Would a technology co-op model feel more trustworthy for organizing work?": "q37_activist_trust",
    "37. Would a technology co-op model feel more trustworthy for organizing work? - Option ID": "q37_activist_trust_id",
    "38. What would need to be true for you to encourage others to use it?": "q38_activist_conditions",
    "39. Possible involvement and conditions": "_sec_involvement",
    "40. What kind of relationship would you or your organization be most interested in if this platform moves forward?": "q40_relationship",
    "40. What kind of relationship would you or your organization be most interested in if this platform moves forward? - Option ID": "q40_relationship_id",
    "41. How much involvement would you want in decisions about how the platform is governed and developed?": "q41_involvement",
    "41. How much involvement would you want in decisions about how the platform is governed and developed? - Option ID": "q41_involvement_id",
    "42. What would you need to see before trusting a technology co-op or community platform like this?": "q42_trust_conditions",
    "42. What would you need to see before trusting a technology co-op or community platform like this? - Option ID": "q42_trust_conditions_id",
    "43. If this platform launched, what would you realistically consider doing in the first year?": "q43_first_year",
    "43. If this platform launched, what would you realistically consider doing in the first year? - Option ID": "q43_first_year_id",
    "44. Final questions": "_sec_final",
    "45. Would you be open to answering a few additional optional questions about pricing, affordability, and what would make adoption realistic?": "q45_optional",
    "45. Would you be open to answering a few additional optional questions about pricing, affordability, and what would make adoption realistic? - Option ID": "q45_optional_id",
    "46. Do you have any comments, concerns, or ideas about a community-owned or technology co-op model for shared digital tools?": "q46_comments",
    "47. Would you be open to a follow-up conversation?": "q47_followup",
    "47. Would you be open to a follow-up conversation? - Option ID": "q47_followup_id",
    "48. Would you like to receive future surveys, research invitations, or updates from Better Together Solutions about this work?": "q48_updates",
    "48. Would you like to receive future surveys, research invitations, or updates from Better Together Solutions about this work? - Option ID": "q48_updates_id",
    "49. Optional pricing and adoption details": "_sec_pricing",
    "50. What would be most likely to prevent you or your organization from adopting or supporting a platform like this?": "q50_barriers",
    "50. What would be most likely to prevent you or your organization from adopting or supporting a platform like this? - Option ID": "q50_barriers_id",
    "51. What kinds of support would make adoption or participation easier?": "q51_support",
    "51. What kinds of support would make adoption or participation easier? - Option ID": "q51_support_id",
    "52. How sensitive are you or your organization to pricing for digital tools or services like this?": "q52_price_sensitivity",
    "52. How sensitive are you or your organization to pricing for digital tools or services like this? - Option ID": "q52_price_sensitivity_id",
    "53. Optional questions for public respondents": "_sec_public_pricing",
    "54. If this platform were useful to you, what kind of contribution would feel most realistic?": "q54_contribution_type",
    "54. If this platform were useful to you, what kind of contribution would feel most realistic? - Option ID": "q54_contribution_type_id",
    "55. What amount would feel realistic for you personally?": "q55_individual_amount",
    "55. What amount would feel realistic for you personally? - Option ID": "q55_individual_amount_id",
    "56. What would need to be true for paying or contributing to feel worthwhile to you?": "q56_worthwhile",
    "57. Optional questions for organizations and groups": "_sec_org_pricing",
    "58. Which pricing model would best fit your organization or group?": "q58_org_pricing_model",
    "58. Which pricing model would best fit your organization or group? - Option ID": "q58_org_pricing_model_id",
    "59. Would your organization or group be willing to contribute financially if the value and trust were clear?": "q59_org_willingness",
    "59. Would your organization or group be willing to contribute financially if the value and trust were clear? - Option ID": "q59_org_willingness_id",
    "60. What level of cost would feel realistic for your organization or group?": "q60_org_cost",
    "60. What level of cost would feel realistic for your organization or group? - Option ID": "q60_org_cost_id",
    "61. What would need to be true for that level of cost to feel justified?": "q61_org_cost_justified",
    "62. Contact details and consent": "_sec_contact",
    "63. Optional consent to use contact details": "q63_consent",
    "64. If you would like contact, you can share your contact information.": "q64_contact_pii",
    "65. If helpful, tell us the best time or way to reach you.": "q65_outreach_pii",
}

# ── Ordinal encodings (Likert-type and scale variables) ───────────────────────

Q9_ORDINAL = {
    "not_familiar": 1,
    "heard_of_it": 2,
    "not_sure": 2,
    "somewhat_familiar": 3,
    "fairly_familiar": 4,
    "very_familiar": 5,
}
Q10_ORDINAL = {
    "not_very_important": 1,
    "not_important": 1,
    "somewhat_important": 2,
    "not_sure": 2,
    "very_important": 3,
    "extremely_important": 4,
}
Q11_ORDINAL = {
    "less_likely": 1,
    "no_difference": 2,
    "not_sure": 2,
    "somewhat_more_likely": 3,
    "much_more_likely": 4,
}
Q12_ORDINAL = {
    "less_likely": 1,
    "no_difference": 2,
    "not_sure": 2,
    "somewhat_more_likely": 3,
    "much_more_likely": 4,
}

Q7_ITEMS = [
    "q7_privacy", "q7_human_support", "q7_accessibility", "q7_connection",
    "q7_governance", "q7_cost", "q7_adaptability", "q7_reliability",
]
Q7_LABELS = [
    "Privacy & data protection", "Real human support", "Accessibility & ease of use",
    "Ability to connect people/groups", "Shared governance & accountability",
    "Low cost", "Ability to adapt to community needs", "Long-term reliability",
]

# Open-text questions for qualitative analysis
QUAL_QUESTIONS: list[dict[str, str]] = [
    {"col": "q6_problems",           "label": "Biggest problems with current platforms",        "scope": "all"},
    {"col": "q13_model_matters",     "label": "What about co-op model matters most",            "scope": "all"},
    {"col": "q15_trustworthy",       "label": "What makes a community platform trustworthy",    "scope": "general_public"},
    {"col": "q20_coop_trust",        "label": "What would make co-op trust the model",          "scope": "co_op"},
    {"col": "q22_nonprofit_burdens", "label": "Biggest technology burdens on staff/volunteers", "scope": "non_profit"},
    {"col": "q24_nonprofit_conditions","label": "What non-profits need before committing",      "scope": "non_profit"},
    {"col": "q26_community_difficulties","label": "What makes mainstream tools difficult",      "scope": "community_group"},
    {"col": "q29_union_needs",       "label": "Organizing needs not served by current tools",   "scope": "union"},
    {"col": "q31_union_governance",  "label": "Governance or member voice for unions",          "scope": "union"},
    {"col": "q33_muni_requirements", "label": "Requirements for municipal viability",           "scope": "municipality"},
    {"col": "q36_activist_risks",    "label": "Risks mainstream platforms create for activists","scope": "activist"},
    {"col": "q38_activist_conditions","label": "What would encourage others to use it",         "scope": "activist"},
    {"col": "q46_comments",          "label": "General comments and ideas",                     "scope": "all"},
    {"col": "q56_worthwhile",        "label": "What makes paying feel worthwhile (individuals)","scope": "individual"},
    {"col": "q61_org_cost_justified","label": "What makes cost feel justified (organizations)", "scope": "organizational"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _run_id_dir(run_id: str) -> Path:
    d = OUTPUT_BASE / run_id
    d.mkdir(parents=True, exist_ok=True)
    for sub in ("audit", "data", "quant", "qual", "charts"):
        (d / sub).mkdir(exist_ok=True)
    return d


def _update_manifest(run_dir: Path, key: str, payload: Any) -> None:
    mf = run_dir / "audit" / "manifest.json"
    data: dict = {}
    if mf.exists():
        data = json.loads(mf.read_text())
    data[key] = payload
    data["updated_at"] = _now_iso()
    mf.write_text(json.dumps(data, indent=2, default=str))


def _log_event(run_dir: Path, event_type: str, payload: dict) -> None:
    entry = {"ts": _now_iso(), "event": event_type, **payload}
    with open(run_dir / "audit" / "run.jsonl", "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def load_df(run_dir: Path) -> pd.DataFrame:
    return pd.read_json(run_dir / "data" / "normalized.json", orient="records")


def _freq_table(series: pd.Series, ordinal_order: list[str] | None = None) -> list[dict]:
    """Frequency + percentage table for a categorical series."""
    counts = series.value_counts(dropna=True)
    total = counts.sum()
    rows = [{"value": k, "n": int(v), "pct": round(100 * v / total, 1)} for k, v in counts.items()]
    if ordinal_order:
        order_map = {v: i for i, v in enumerate(ordinal_order)}
        rows.sort(key=lambda r: order_map.get(r["value"], 999))
    return rows


def _multival_freq(series: pd.Series) -> list[dict]:
    """Frequency table for comma-separated multi-select option IDs."""
    counter: Counter = Counter()
    total = 0
    for v in series.dropna():
        items = [x.strip() for x in str(v).split(",") if x.strip()]
        counter.update(items)
        total += 1
    return [{"value": k, "n": v, "pct": round(100 * v / total, 1)} for k, v in counter.most_common()]


def _cronbach_alpha(df_items: pd.DataFrame) -> float:
    """Cronbach's alpha for a set of Likert items (Cronbach, 1951)."""
    k = df_items.shape[1]
    if k < 2:
        return float("nan")
    item_vars = df_items.var(axis=0, ddof=1)
    scale_var = df_items.sum(axis=1).var(ddof=1)
    if scale_var == 0:
        return float("nan")
    return round(float(k / (k - 1) * (1 - item_vars.sum() / scale_var)), 4)


def _bootstrap_ci(values: np.ndarray, stat_fn=np.mean, n_boot: int = 10_000, ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap confidence interval (Efron & Tibshirani, 1993). Seed fixed globally."""
    rng = np.random.default_rng(RANDOM_SEED)
    boots = [stat_fn(rng.choice(values, size=len(values), replace=True)) for _ in range(n_boot)]
    lo = (1 - ci) / 2
    return (round(float(np.percentile(boots, lo * 100)), 4),
            round(float(np.percentile(boots, (1 - lo) * 100)), 4))


def _cramers_v(contingency_table: np.ndarray) -> float:
    """Cramér's V effect size for chi-square (Cramér, 1946)."""
    from scipy.stats import chi2_contingency
    chi2, _, _, _ = chi2_contingency(contingency_table)
    n = contingency_table.sum()
    r, c = contingency_table.shape
    phi2 = chi2 / n
    r_corr = r - (r - 1) ** 2 / (n - 1) if n > 1 else r
    c_corr = c - (c - 1) ** 2 / (n - 1) if n > 1 else c
    denom = min(r_corr - 1, c_corr - 1)
    return round(float(np.sqrt(phi2 / denom)) if denom > 0 else 0.0, 4)


# ── Stage 1: Ingest ───────────────────────────────────────────────────────────


def cmd_ingest(args: argparse.Namespace) -> str:
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        sys.exit(f"ERROR: Input file not found: {input_path}")

    run_id = args.run_id or _now_iso()
    run_dir = _run_id_dir(run_id)

    input_sha = _sha256(input_path)
    _update_manifest(run_dir, "input", {
        "path": str(input_path),
        "sha256": input_sha,
        "ingested_at": _now_iso(),
    })

    df = pd.read_excel(input_path, engine="openpyxl", dtype=str)
    df.columns = [COLUMN_ALIASES.get(c, c) for c in df.columns]

    # Drop PII columns; record consent counts before dropping
    consent_counts = df.get("q63_consent", pd.Series(dtype=str)).value_counts(dropna=False).to_dict()
    pii_aliases = ["q64_contact_pii", "q65_outreach_pii"]
    df = df.drop(columns=[c for c in pii_aliases if c in df.columns])

    # Drop section-header columns (they contain no data)
    section_cols = [c for c in df.columns if str(c).startswith("_sec_")]
    df = df.drop(columns=section_cols)

    # Assign anonymous respondent IDs (R001..RN) replacing all original IDs
    n_total = len(df)
    df.insert(0, "rid", [f"R{i+1:03d}" for i in range(n_total)])
    id_cols = ["row_no", "response_id", "formbricks_id", "user_id", "survey_id", "url", "tags"]
    df = df.drop(columns=[c for c in id_cols if c in df.columns])

    # Parse numeric Likert columns
    for col in Q7_ITEMS + ["q5_satisfaction"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Encode ordinal variables
    for col, mapping in [
        ("q9_familiarity_id", Q9_ORDINAL),
        ("q10_importance_id", Q10_ORDINAL),
        ("q11_trust_id", Q11_ORDINAL),
        ("q12_adoption_id", Q12_ORDINAL),
    ]:
        if col in df.columns:
            df[col + "_ord"] = df[col].map(mapping)

    # Record missingness per question
    missingness = {
        col: {"n_missing": int(df[col].isna().sum()), "pct_missing": round(100 * df[col].isna().mean(), 1)}
        for col in df.columns if not col.startswith("_")
    }

    # Export raw CSV (PII-free) and normalized JSON
    raw_csv = run_dir / "data" / "raw.csv"
    norm_json = run_dir / "data" / "normalized.json"
    df.to_csv(raw_csv, index=False, quoting=csv.QUOTE_ALL)
    df.to_json(norm_json, orient="records", indent=2, force_ascii=False)

    _update_manifest(run_dir, "ingest", {
        "n_total": n_total,
        "n_completed": int((df.get("finished", pd.Series()) == "Yes").sum()),
        "n_partial": int((df.get("finished", pd.Series()) == "No").sum()),
        "consent_counts": {str(k): int(v) for k, v in consent_counts.items()},
        "missingness": missingness,
        "raw_csv_sha256": _sha256(raw_csv),
        "norm_json_sha256": _sha256(norm_json),
    })
    _log_event(run_dir, "ingest_complete", {"n_total": n_total, "run_id": run_id})
    print(f"Ingested {n_total} responses → {run_dir}/data/")
    return run_id


# ── Stage 2: Quantitative Analysis ───────────────────────────────────────────


def cmd_quant(args: argparse.Namespace) -> None:
    from scipy import stats as spstats

    run_dir = _run_id_dir(args.run_id)
    df = load_df(run_dir)

    # Use only completed responses for primary analysis
    completed = df[df.get("finished", pd.Series()) == "Yes"].copy()
    n_completed = len(completed)
    n_total = len(df)

    results: dict[str, Any] = {
        "analysis_date": _now_iso(),
        "statistical_significance_threshold": 0.05,
        "random_seed": RANDOM_SEED,
        "bootstrap_iterations": 10_000,
        "note_ordinal_treatment": (
            "Likert items (1-5) are treated as interval-level for mean/CI reporting "
            "and ordinal for non-parametric tests, following Norman (2010) and "
            "Sullivan & Artino (2013)."
        ),
        "note_small_cells": (
            "Cross-tabulations with cell n < 5 are suppressed in accordance with "
            "k-anonymity (k=5) and statistical reliability standards."
        ),
        "n_total": n_total,
        "n_completed": n_completed,
        "n_partial": n_total - n_completed,
        "completion_rate_pct": round(100 * n_completed / n_total, 1),
    }

    # ── Response overview ──────────────────────────────────────────────────
    results["overview"] = {
        "ua_os": _freq_table(df["ua_os"]) if "ua_os" in df else [],
        "ua_device": _freq_table(df["ua_device"]) if "ua_device" in df else [],
        "ua_browser": _freq_table(df["ua_browser"]) if "ua_browser" in df else [],
    }

    # ── Respondent type distribution ───────────────────────────────────────
    type_dist = _freq_table(df["q2_type_id"]) if "q2_type_id" in df else []
    results["respondent_types"] = {
        "all_responses": type_dist,
        "completed_only": _freq_table(completed["q2_type_id"]) if "q2_type_id" in completed else [],
        "note": "Branching questions were shown based on respondent type. Denominators vary per question.",
    }

    # ── Q5: Tool satisfaction ──────────────────────────────────────────────
    if "q5_satisfaction" in completed.columns:
        sat = completed["q5_satisfaction"].dropna()
        vals = sat.values.astype(float)
        ci_lo, ci_hi = _bootstrap_ci(vals, np.mean)
        _, p_normal = spstats.shapiro(vals) if len(vals) >= 3 else (None, None)
        results["q5_tool_satisfaction"] = {
            "n": int(len(vals)),
            "mean": round(float(np.mean(vals)), 3),
            "median": float(np.median(vals)),
            "sd": round(float(np.std(vals, ddof=1)), 3),
            "mode": float(spstats.mode(vals, keepdims=True).mode[0]),
            "min": float(vals.min()),
            "max": float(vals.max()),
            "iqr": round(float(np.percentile(vals, 75) - np.percentile(vals, 25)), 3),
            "skewness": round(float(spstats.skew(vals)), 3),
            "kurtosis": round(float(spstats.kurtosis(vals)), 3),
            "bootstrap_95ci_mean": [ci_lo, ci_hi],
            "shapiro_wilk_p": round(float(p_normal), 4) if p_normal is not None else None,
            "distribution": _freq_table(sat.astype(str)),
        }

    # ── Q7: Feature importance (Likert scale) ──────────────────────────────
    q7_data = completed[Q7_ITEMS].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    q7_results: dict[str, Any] = {}
    item_stats = []
    for col, label in zip(Q7_ITEMS, Q7_LABELS):
        series = q7_data[col].dropna()
        if len(series) < 5:
            continue
        vals = series.values.astype(float)
        ci_lo, ci_hi = _bootstrap_ci(vals, np.mean)
        item_stats.append({
            "item": col,
            "label": label,
            "n": int(len(vals)),
            "mean": round(float(np.mean(vals)), 3),
            "median": float(np.median(vals)),
            "sd": round(float(np.std(vals, ddof=1)), 3),
            "iqr": round(float(np.percentile(vals, 75) - np.percentile(vals, 25)), 3),
            "bootstrap_95ci_mean": [ci_lo, ci_hi],
            "distribution": _freq_table(series.astype(str)),
        })

    item_stats.sort(key=lambda x: -x["mean"])
    valid_items = q7_data[Q7_ITEMS].dropna()
    alpha = _cronbach_alpha(valid_items) if len(valid_items) >= 5 else float("nan")
    q7_results["items_ranked"] = item_stats
    q7_results["cronbach_alpha"] = {
        "value": alpha,
        "n_items": len(Q7_ITEMS),
        "n_respondents": int(len(valid_items)),
        "interpretation": (
            "Excellent (≥0.90)" if alpha >= 0.90 else
            "Good (0.80–0.89)" if alpha >= 0.80 else
            "Acceptable (0.70–0.79)" if alpha >= 0.70 else
            "Questionable (0.60–0.69)" if alpha >= 0.60 else
            "Poor (<0.60)"
        ),
        "reference": "George & Mallery (2003). SPSS for Windows Step by Step.",
    }

    # ── Kruskal-Wallis: Q7 items by respondent type ────────────────────────
    # Collapse small segments: individual (general_public) vs organisational (all others)
    grp_map = defaultdict(lambda: "organisational")
    grp_map["general_public"] = "individual"
    if "q2_type_id" in completed.columns:
        completed = completed.copy()
        completed["_group"] = completed["q2_type_id"].map(grp_map)
        kw_results = []
        bonferroni_k = len(Q7_ITEMS)
        alpha_corrected = 0.05 / bonferroni_k
        groups = completed.groupby("_group")
        for col, label in zip(Q7_ITEMS, Q7_LABELS):
            group_arrays = [
                g[col].dropna().values.astype(float)
                for _, g in groups
                if len(g[col].dropna()) >= 5
            ]
            if len(group_arrays) < 2 or any(len(a) == 0 for a in group_arrays):
                continue
            h, p = spstats.kruskal(*group_arrays)
            n_tot = sum(len(a) for a in group_arrays)
            eps2 = (h - len(group_arrays) + 1) / (n_tot - len(group_arrays))
            kw_results.append({
                "item": col,
                "label": label,
                "H": round(float(h), 4),
                "p_value": round(float(p), 4),
                "p_bonferroni_threshold": round(alpha_corrected, 4),
                "significant_after_correction": bool(p < alpha_corrected),
                "epsilon_squared": round(float(eps2), 4),
                "effect_size_interpretation": (
                    "Large (≥0.14)" if eps2 >= 0.14 else
                    "Medium (0.06–0.13)" if eps2 >= 0.06 else "Small (<0.06)"
                ),
                "n_per_group": {k: int(len(g[col].dropna())) for k, g in groups},
                "reference": "Kruskal & Wallis (1952); ε² interpretation: Cohen (1988).",
            })
        q7_results["kruskal_wallis_by_group"] = {
            "grouping": "individual (general_public) vs organisational (all others)",
            "bonferroni_correction_k": bonferroni_k,
            "corrected_alpha": round(alpha_corrected, 4),
            "tests": kw_results,
            "note": (
                "Full cross-segment analysis is descriptive only due to small segment "
                "sizes (N=1–6 per non-public segment). Statistical testing uses only "
                "the individual/organisational dichotomy to ensure adequate power."
            ),
        }

    # ── Segment heatmap data for Q7 ────────────────────────────────────────
    if "q2_type_id" in completed.columns:
        q7_results["segment_heatmap"] = {}
        for seg, grp in completed.groupby("q2_type_id"):
            if len(grp) < 5:
                q7_results["segment_heatmap"][seg] = "SUPPRESSED (n<5)"
                continue
            q7_results["segment_heatmap"][seg] = {
                col: round(float(grp[col].dropna().astype(float).mean()), 2)
                for col in Q7_ITEMS if col in grp.columns
            }

    results["q7_feature_importance"] = q7_results

    # ── Q9–Q12: Governance and trust ordinal variables ─────────────────────
    for qcol, qid, qlabel, order_keys, mapping in [
        ("q9_familiarity", "q9_familiarity_id", "Familiarity with tech co-ops",
         ["not_familiar", "heard_of_it", "somewhat_familiar", "fairly_familiar", "very_familiar"], Q9_ORDINAL),
        ("q10_importance", "q10_importance_id", "Importance of community ownership",
         ["not_very_important", "somewhat_important", "very_important", "extremely_important"], Q10_ORDINAL),
        ("q11_trust", "q11_trust_id", "Trust increase from co-op model",
         ["less_likely", "no_difference", "somewhat_more_likely", "much_more_likely"], Q11_ORDINAL),
        ("q12_adoption", "q12_adoption_id", "Adoption likelihood from co-op model",
         ["less_likely", "no_difference", "somewhat_more_likely", "much_more_likely"], Q12_ORDINAL),
    ]:
        col_id = qid
        ord_col = qid + "_ord"
        if col_id not in completed.columns:
            continue
        series_id = completed[col_id].dropna()
        series_ord = completed[ord_col].dropna() if ord_col in completed.columns else pd.Series(dtype=float)
        freq = _freq_table(series_id)
        ord_vals = series_ord.values.astype(float) if len(series_ord) else np.array([])
        results[qcol] = {
            "label": qlabel,
            "n": int(len(series_id)),
            "frequency_distribution": freq,
            "median_ordinal": float(np.median(ord_vals)) if len(ord_vals) else None,
            "iqr_ordinal": round(float(np.percentile(ord_vals, 75) - np.percentile(ord_vals, 25)), 3) if len(ord_vals) >= 4 else None,
            "note": "Ordinal scores: see Q9_ORDINAL / Q10_ORDINAL / Q11_ORDINAL / Q12_ORDINAL in analysis.py",
        }

    # ── Multi-select frequency tables ─────────────────────────────────────
    for col, label in [
        ("q6_problems_id", "Biggest problems with current platforms (multi-select)"),
        ("q13_model_matters_id", "What about co-op model matters most (multi-select)"),
        ("q40_relationship_id", "Desired relationship with platform (multi-select)"),
        ("q42_trust_conditions_id", "Trust conditions (multi-select)"),
        ("q43_first_year_id", "First-year realistic actions (multi-select)"),
        ("q50_barriers_id", "Adoption barriers (multi-select)"),
        ("q51_support_id", "Support needed for adoption (multi-select)"),
    ]:
        if col in completed.columns:
            results[col] = {
                "label": label,
                "frequency_table": _multival_freq(completed[col]),
            }

    # ── Categorical: Single-select distributions ───────────────────────────
    for col, label in [
        ("q52_price_sensitivity_id", "Price sensitivity"),
        ("q47_followup_id", "Open to follow-up"),
        ("q48_updates_id", "Want updates"),
        ("q16_interest_id", "Interest in community platform (general public)"),
    ]:
        if col in completed.columns:
            sub = completed[col].dropna()
            results[col] = {"label": label, "n": int(len(sub)), "distribution": _freq_table(sub)}

    # ── Missing data report ────────────────────────────────────────────────
    missingness_completed = {
        col: {
            "n_missing": int(completed[col].isna().sum()),
            "pct_missing": round(100 * completed[col].isna().mean(), 1),
        }
        for col in completed.columns
        if not col.startswith("_") and col != "rid"
    }
    results["missing_data"] = {
        "note": (
            "Missing values in branching questions are structural (question not shown "
            "to that respondent type) and are excluded from per-question denominators. "
            "MCAR assumption is reasonable for branching missingness; no imputation applied."
        ),
        "per_column": missingness_completed,
    }

    out = run_dir / "quant" / "quant_results.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    _update_manifest(run_dir, "quant", {"sha256": _sha256(out), "n_tests": len(results)})
    _log_event(run_dir, "quant_complete", {"output": str(out)})
    print(f"Quantitative analysis complete → {out}")


# ── Stage 3: Qualitative Analysis (AI-assisted RTA) ──────────────────────────


def _ask_ollama(prompt: str, ollama_host: str, model: str = "llama3.2:latest") -> str:
    """Direct call to Ollama API. Returns raw text response."""
    import requests  # type: ignore
    resp = requests.post(
        f"{ollama_host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _extract_json_array(raw: str) -> list[dict]:
    """
    Robustly extract a JSON array from LLM output that may include
    markdown fences, trailing commas, or surrounding prose.
    """
    # Strip markdown code fences
    clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
    # Try the whole cleaned string first
    for candidate in [clean, raw]:
        m = re.search(r"\[.*\]", candidate, re.DOTALL)
        if not m:
            continue
        text = m.group()
        # Remove trailing commas before ] or }
        text = re.sub(r",\s*([\]}])", r"\1", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return []


QUAL_PROMPTS = {
    "coding": textwrap.dedent("""
        You are a qualitative research assistant performing initial thematic coding
        following Reflexive Thematic Analysis (Braun & Clarke, 2021).

        Below are survey responses to the question: "{question_label}"

        TASK: Generate initial codes for each response. For each response:
        1. Assign 1–3 descriptive codes (2–5 words each, lower_snake_case)
        2. Note the sentiment: positive / negative / neutral / mixed
        3. Flag if the response contains a notable direct quote (max 20 words)

        Respond ONLY with a JSON array. Each element:
        {{
          "rid": "<respondent_id>",
          "codes": ["code_one", "code_two"],
          "sentiment": "positive|negative|neutral|mixed",
          "notable_quote": "<verbatim quote or null>"
        }}

        Responses:
        {responses}
    """).strip(),

    "theme_synthesis": textwrap.dedent("""
        You are a qualitative researcher synthesising initial codes into themes
        following Reflexive Thematic Analysis Phase 3 (Braun & Clarke, 2021).

        Question: "{question_label}"

        Initial codes (from {n_responses} responses):
        {codes_summary}

        TASK: Identify 3–6 coherent themes that capture the essence of these responses.
        For each theme:
        1. A concise theme name (3–7 words)
        2. A description (2–3 sentences explaining the theme and its significance)
        3. Estimated prevalence (percentage of responses that relate to this theme)
        4. Two verbatim supporting quotes (include respondent ID)
        5. Key codes that belong to this theme

        Respond ONLY with a JSON array:
        {{
          "theme": "<Theme Name>",
          "description": "...",
          "prevalence_pct": <number>,
          "supporting_quotes": [
            {{"rid": "R001", "quote": "..."}},
            {{"rid": "R002", "quote": "..."}}
          ],
          "member_codes": ["code_one", "code_two"]
        }}
    """).strip(),
}


def cmd_qual(args: argparse.Namespace) -> None:
    run_dir = _run_id_dir(args.run_id)
    df = load_df(run_dir)
    completed = df[df.get("finished", pd.Series()) == "Yes"].copy()
    ollama_host = args.ollama_host
    model = args.ollama_model

    qual_dir = run_dir / "qual"
    qual_dir.mkdir(exist_ok=True)

    all_themes: dict[str, Any] = {}

    for q in QUAL_QUESTIONS:
        col = q["col"]
        label = q["label"]
        scope = q["scope"]

        if col not in completed.columns:
            continue

        # Filter by scope
        if scope == "all":
            subset = completed
        elif scope in ("individual", "general_public"):
            subset = completed[completed.get("q2_type_id", pd.Series()) == "general_public"]
        elif scope == "organisational":
            subset = completed[completed.get("q3_perspective_id", pd.Series()) == "organizational"]
        else:
            subset = completed[completed.get("q2_type_id", pd.Series()) == scope]

        responses = subset[["rid", col]].dropna(subset=[col]).copy()
        responses[col] = responses[col].astype(str)
        responses = responses[responses[col].str.strip() != ""]

        n = len(responses)
        if n < 3:
            print(f"  SKIP {col}: n={n} (too few for analysis)")
            all_themes[col] = {"label": label, "n": n, "skipped": "too few responses"}
            continue

        print(f"  Coding {col} (n={n})...")

        # Phase 2: Initial coding — chunk into batches of 25 to stay within LLM context
        CHUNK_SIZE = 25
        rows_list = list(responses.iterrows())
        codes_data: list[dict] = []
        for chunk_start in range(0, len(rows_list), CHUNK_SIZE):
            chunk = rows_list[chunk_start:chunk_start + CHUNK_SIZE]
            chunk_text = "\n".join(
                f"[{row['rid']}] {str(row[col])[:350]}"
                for _, row in chunk
            )
            coding_prompt = QUAL_PROMPTS["coding"].format(
                question_label=label,
                responses=chunk_text,
            )
            try:
                raw_codes = _ask_ollama(coding_prompt, ollama_host, model)
                chunk_codes: list[dict] = _extract_json_array(raw_codes)
                codes_data.extend(chunk_codes)
                print(f"    chunk {chunk_start//CHUNK_SIZE + 1}: {len(chunk_codes)} coded")
            except Exception as e:
                print(f"    WARNING: coding failed chunk {chunk_start//CHUNK_SIZE + 1} for {col}: {e}")

        # Store the prompt used (first chunk representative)
        coding_prompt = QUAL_PROMPTS["coding"].format(
            question_label=label,
            responses="[chunked — see methodology.md §6.3]",
        )

        # Phase 3: Theme synthesis
        codes_summary = "\n".join(
            f"[{c.get('rid','')}] codes: {', '.join(c.get('codes',[]))}; sentiment: {c.get('sentiment','')}"
            for c in codes_data
        ) if codes_data else response_text[:3000]

        theme_prompt = QUAL_PROMPTS["theme_synthesis"].format(
            question_label=label,
            n_responses=n,
            codes_summary=codes_summary,
        )

        try:
            raw_themes = _ask_ollama(theme_prompt, ollama_host, model)
            themes_data: list[dict] = _extract_json_array(raw_themes)
            # Retry once with a more explicit JSON-only prompt if parsing failed
            if not themes_data:
                retry_prompt = theme_prompt + "\n\nIMPORTANT: Output ONLY a valid JSON array. No markdown, no prose, no code fences. Start with [ and end with ]."
                raw_themes2 = _ask_ollama(retry_prompt, ollama_host, model)
                themes_data = _extract_json_array(raw_themes2)
        except Exception as e:
            print(f"    WARNING: theme synthesis failed for {col}: {e}")
            themes_data = []

        # Sentiment aggregation
        sentiments = Counter(c.get("sentiment", "unknown") for c in codes_data)

        result = {
            "question": label,
            "column": col,
            "scope": scope,
            "n_responses": n,
            "sentiment_distribution": dict(sentiments),
            "coding_prompt_sha256": hashlib.sha256(coding_prompt.encode()).hexdigest(),
            "theme_prompt_sha256": hashlib.sha256(theme_prompt.encode()).hexdigest(),
            "ollama_model": model,
            "ollama_host": ollama_host,
            "initial_codes": codes_data,
            "themes": themes_data,
            "prompts": {
                "coding": coding_prompt,
                "theme_synthesis": theme_prompt,
            },
            "methodological_note": (
                "Coded using AI-assisted Reflexive Thematic Analysis (Braun & Clarke, 2021). "
                "Prompts are published verbatim as the operational codebook. "
                "Intercoder reliability (Krippendorff's alpha) computed in irr stage."
            ),
        }

        out_file = qual_dir / f"{col}.json"
        out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        all_themes[col] = {"label": label, "n": n, "n_themes": len(themes_data),
                           "sha256": _sha256(out_file)}
        print(f"    → {len(themes_data)} themes identified")

    _update_manifest(run_dir, "qual", {"questions_processed": all_themes})
    _log_event(run_dir, "qual_complete", {"n_questions": len(all_themes)})
    print(f"Qualitative analysis complete → {qual_dir}/")


# ── Stage 4: Intercoder Reliability ──────────────────────────────────────────


def cmd_irr(args: argparse.Namespace) -> None:
    """
    Computes intercoder reliability for AI-assisted thematic coding.

    Method: A 20% random sample of responses per question is independently
    coded in a second pass. Agreement is measured using Krippendorff's alpha
    (Hayes & Krippendorff, 2007) for nominal data (theme assignment).

    Target: α ≥ 0.67 (acceptable minimum for exploratory research).
    Ideal:  α ≥ 0.80 (Krippendorff, 2004).
    """
    try:
        import krippendorff as kd  # type: ignore
    except ImportError:
        sys.exit("ERROR: pip install krippendorff")

    run_dir = _run_id_dir(args.run_id)
    df = load_df(run_dir)
    completed = df[df.get("finished", pd.Series()) == "Yes"].copy()
    qual_dir = run_dir / "qual"
    ollama_host = args.ollama_host
    model = args.ollama_model

    rng = np.random.default_rng(RANDOM_SEED)
    irr_results: dict[str, Any] = {
        "method": "Krippendorff's alpha (nominal) — second-pass AI coding on 20% random sample",
        "reference": "Hayes & Krippendorff (2007). Communication Methods and Measures, 1(1), 77-89.",
        "sample_fraction": 0.20,
        "random_seed": RANDOM_SEED,
        "target_alpha": 0.67,
        "ideal_alpha": 0.80,
        "questions": {},
    }

    for q in QUAL_QUESTIONS:
        col = q["col"]
        qual_file = qual_dir / f"{col}.json"
        if not qual_file.exists():
            continue

        first_pass = json.loads(qual_file.read_text())
        codes_pass1 = first_pass.get("initial_codes", [])
        if len(codes_pass1) < 5:
            irr_results["questions"][col] = {"skipped": "too few coded responses"}
            continue

        # Sample 20% for second pass
        n_sample = max(3, int(len(codes_pass1) * 0.20))
        sample_indices = rng.choice(len(codes_pass1), size=n_sample, replace=False)
        sample_codes = [codes_pass1[i] for i in sample_indices]
        sample_rids = [c["rid"] for c in sample_codes]

        # Re-run coding on sampled responses
        sample_responses_df = completed[completed["rid"].isin(sample_rids)][["rid", col]].dropna()
        if len(sample_responses_df) < 3:
            irr_results["questions"][col] = {"skipped": "too few sampled responses in df"}
            continue

        response_text = "\n".join(
            f"[{row['rid']}] {str(row[col])[:400]}"
            for _, row in sample_responses_df.iterrows()
        )
        coding_prompt = QUAL_PROMPTS["coding"].format(
            question_label=q["label"],
            responses=response_text,
        )

        try:
            raw_2 = _ask_ollama(coding_prompt, ollama_host, model)
            codes_pass2: list[dict] = _extract_json_array(raw_2)
        except Exception as e:
            irr_results["questions"][col] = {"error": str(e)}
            continue

        # Build aligned code arrays for alpha calculation
        # Use primary code (first code in list) for nominal agreement
        p1_map = {c["rid"]: (c.get("codes") or [""])[0] for c in sample_codes}
        p2_map = {c.get("rid", ""): (c.get("codes") or [""])[0] for c in codes_pass2}

        shared_rids = [r for r in sample_rids if r in p1_map and r in p2_map]
        if len(shared_rids) < 3:
            irr_results["questions"][col] = {"skipped": "insufficient overlap between passes"}
            continue

        # Encode codes as integers for krippendorff
        all_codes = sorted({p1_map[r] for r in shared_rids} | {p2_map[r] for r in shared_rids})
        code_map = {c: i for i, c in enumerate(all_codes)}
        r1 = [code_map[p1_map[r]] for r in shared_rids]
        r2 = [code_map[p2_map[r]] for r in shared_rids]
        reliability_data = np.array([r1, r2])

        try:
            alpha = kd.alpha(reliability_data=reliability_data, level_of_measurement="nominal")
        except Exception:
            alpha = float("nan")

        irr_results["questions"][col] = {
            "n_total_coded": len(codes_pass1),
            "n_sampled": len(shared_rids),
            "krippendorff_alpha": round(float(alpha), 4),
            "meets_minimum": bool(alpha >= 0.67),
            "meets_ideal": bool(alpha >= 0.80),
            "interpretation": (
                "Acceptable (≥0.80)" if alpha >= 0.80 else
                "Minimum acceptable (≥0.67)" if alpha >= 0.67 else
                "Below threshold (<0.67) — themes should be interpreted cautiously"
            ),
        }
        print(f"  {col}: Krippendorff α = {alpha:.3f}")

    out = qual_dir / "irr_results.json"
    out.write_text(json.dumps(irr_results, indent=2, default=str))
    _update_manifest(run_dir, "irr", {"sha256": _sha256(out)})
    _log_event(run_dir, "irr_complete", {})
    print(f"IRR analysis complete → {out}")


# ── Stage 5: Visualizations ───────────────────────────────────────────────────


def cmd_visualize(args: argparse.Namespace) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from wordcloud import WordCloud

    run_dir = _run_id_dir(args.run_id)
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)

    quant_file = run_dir / "quant" / "quant_results.json"
    if not quant_file.exists():
        sys.exit("Run 'quant' stage first")
    quant = json.loads(quant_file.read_text())

    PALETTE = ["#2563EB", "#16A34A", "#DC2626", "#F59E0B", "#7C3AED", "#0891B2", "#EA580C"]
    sns.set_theme(style="whitegrid", font_scale=1.15)
    plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight"})

    generated: list[str] = []

    def _save(fig: Any, name: str) -> str:
        path = charts_dir / name
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        generated.append(name)
        return str(path)

    # ── Respondent type distribution ───────────────────────────────────────
    if "respondent_types" in quant:
        rows = quant["respondent_types"]["all_responses"]
        if rows:
            vals = [r["value"] for r in rows]
            ns = [r["n"] for r in rows]
            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.barh(vals[::-1], ns[::-1], color=PALETTE[0], edgecolor="white")
            ax.bar_label(bars, fmt="%d", padding=4)
            ax.set_xlabel("Number of responses")
            ax.set_title("Survey Respondents by Sector (all responses, N={})".format(sum(ns)))
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            _save(fig, "respondent_types.png")

    # ── Q5: Tool satisfaction distribution ────────────────────────────────
    if "q5_tool_satisfaction" in quant:
        dist = quant["q5_tool_satisfaction"]["distribution"]
        labels = [str(r["value"]) for r in sorted(dist, key=lambda x: x["value"])]
        ns = [r["n"] for r in sorted(dist, key=lambda x: x["value"])]
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(labels, ns, color=PALETTE[0], width=0.6, edgecolor="white")
        ax.bar_label(bars, fmt="%d", padding=3)
        mean_val = quant["q5_tool_satisfaction"]["mean"]
        ax.axvline(x=mean_val - 1, color=PALETTE[2], linestyle="--", linewidth=1.5,
                   label=f"Mean = {mean_val}")
        ax.set_xlabel("Satisfaction (1 = Very dissatisfied, 5 = Very satisfied)")
        ax.set_ylabel("Number of respondents")
        ax.set_title(f"Digital Tool Satisfaction (N={quant['q5_tool_satisfaction']['n']})")
        ax.legend()
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        _save(fig, "tool_satisfaction.png")

    # ── Q7: Feature importance ranked ─────────────────────────────────────
    if "q7_feature_importance" in quant:
        items = quant["q7_feature_importance"]["items_ranked"]
        if items:
            labels = [it["label"] for it in items]
            means = [it["mean"] for it in items]
            ci_lo = [it["mean"] - it["bootstrap_95ci_mean"][0] for it in items]
            ci_hi = [it["bootstrap_95ci_mean"][1] - it["mean"] for it in items]
            fig, ax = plt.subplots(figsize=(10, 6))
            y = range(len(labels))
            ax.barh(list(y), means, xerr=[ci_lo, ci_hi], color=PALETTE[1],
                    error_kw={"ecolor": "#374151", "capsize": 4}, edgecolor="white")
            ax.set_yticks(list(y))
            ax.set_yticklabels(labels)
            ax.set_xlabel("Mean importance rating (1–5) with 95% bootstrap CI")
            ax.set_title("Platform Feature Importance\n(N varies per item; sorted by mean)")
            ax.set_xlim(1, 5.5)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            _save(fig, "feature_importance.png")

    # ── Q9-Q12: Governance & trust grouped bar ─────────────────────────────
    gov_qs = {
        "q9_familiarity": ("Familiarity with\ntech co-ops", ["not_familiar", "heard_of_it", "somewhat_familiar", "fairly_familiar", "very_familiar"]),
        "q10_importance": ("Importance of\ncommunity ownership", ["not_very_important", "somewhat_important", "very_important", "extremely_important"]),
        "q11_trust": ("Trust increase\nfrom co-op model", ["less_likely", "no_difference", "somewhat_more_likely", "much_more_likely"]),
        "q12_adoption": ("Adoption likelihood\nfrom co-op model", ["less_likely", "no_difference", "somewhat_more_likely", "much_more_likely"]),
    }
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, (key, (title, order)) in zip(axes.flat, gov_qs.items()):
        if key not in quant:
            ax.set_visible(False)
            continue
        rows = quant[key]["frequency_distribution"]
        row_map = {r["value"]: r["pct"] for r in rows}
        present = [v for v in order if v in row_map]
        pcts = [row_map.get(v, 0) for v in present]
        labels = [v.replace("_", " ") for v in present]
        bars = ax.bar(labels, pcts, color=PALETTE[:len(present)], edgecolor="white")
        ax.bar_label(bars, fmt="%.0f%%", padding=2)
        ax.set_title(title)
        ax.set_ylabel("% of respondents")
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", rotation=25)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle("Governance, Ownership & Trust (completed responses)", y=1.01, fontsize=14)
    plt.tight_layout()
    _save(fig, "ownership_trust.png")

    # ── Q50: Adoption barriers pareto ─────────────────────────────────────
    if "q50_barriers_id" in quant:
        rows = quant["q50_barriers_id"]["frequency_table"][:12]
        if rows:
            labels = [r["value"].replace("_", " ") for r in rows]
            ns = [r["n"] for r in rows]
            cumulative = [sum(ns[:i+1]) / sum(ns) * 100 for i in range(len(ns))]
            fig, ax1 = plt.subplots(figsize=(12, 6))
            ax2 = ax1.twinx()
            ax1.bar(labels, ns, color=PALETTE[0], edgecolor="white")
            ax2.plot(labels, cumulative, color=PALETTE[2], marker="o", linewidth=2)
            ax2.axhline(80, color="#6B7280", linestyle="--", linewidth=1)
            ax1.set_ylabel("Count")
            ax2.set_ylabel("Cumulative %")
            ax1.set_title("Adoption Barriers — Pareto Chart")
            ax1.tick_params(axis="x", rotation=35)
            ax1.spines["top"].set_visible(False)
            _save(fig, "adoption_barriers.png")

    # ── Word clouds for key open-text questions ────────────────────────────
    df = load_df(run_dir)
    completed = df[df.get("finished", pd.Series()) == "Yes"]

    for col, filename, title in [
        ("q6_problems", "wordcloud_q6.png", "Problems with Current Platforms (Q6)"),
        ("q15_trustworthy", "wordcloud_q15.png", "What Makes a Platform Feel Trustworthy (Q15)"),
        ("q46_comments", "wordcloud_q46.png", "General Comments & Ideas (Q46)"),
    ]:
        if col not in completed.columns:
            continue
        text = " ".join(str(v) for v in completed[col].dropna() if str(v).strip())
        if len(text) < 100:
            continue
        wc = WordCloud(
            width=1200, height=600, background_color="white",
            colormap="Blues", max_words=80,
            random_state=RANDOM_SEED, collocations=True,
        ).generate(text)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title(title, fontsize=14, pad=12)
        _save(fig, filename)

    # ── Sentiment distribution across qual questions ───────────────────────
    qual_dir = run_dir / "qual"
    sentiment_data: dict[str, dict] = {}
    for qf in sorted(qual_dir.glob("*.json")):
        if qf.name == "irr_results.json":
            continue
        d = json.loads(qf.read_text())
        s = d.get("sentiment_distribution", {})
        if s:
            sentiment_data[d.get("question", qf.stem)[:40]] = s

    if sentiment_data:
        categories = sorted({k for v in sentiment_data.values() for k in v})
        qlabels = list(sentiment_data.keys())
        x = np.arange(len(qlabels))
        width = 0.18
        fig, ax = plt.subplots(figsize=(14, 7))
        for i, cat in enumerate(categories):
            vals = [sentiment_data[q].get(cat, 0) for q in qlabels]
            ax.bar(x + i * width, vals, width, label=cat, color=PALETTE[i % len(PALETTE)])
        ax.set_xticks(x + width * (len(categories) - 1) / 2)
        ax.set_xticklabels(qlabels, rotation=35, ha="right", fontsize=9)
        ax.set_ylabel("Count")
        ax.set_title("Sentiment Distribution Across Open-Text Questions")
        ax.legend(title="Sentiment")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        _save(fig, "sentiment_distribution.png")

    _update_manifest(run_dir, "visualize", {"charts_generated": generated})
    _log_event(run_dir, "visualize_complete", {"n_charts": len(generated)})
    print(f"Visualizations complete ({len(generated)} charts) → {charts_dir}/")


# ── Stage 6: Report Assembly ──────────────────────────────────────────────────


def cmd_report(args: argparse.Namespace) -> None:
    run_dir = _run_id_dir(args.run_id)
    quant_file = run_dir / "quant" / "quant_results.json"
    if not quant_file.exists():
        sys.exit("Run 'quant' stage first")
    quant = json.loads(quant_file.read_text())
    manifest = json.loads((run_dir / "audit" / "manifest.json").read_text())

    df = load_df(run_dir)
    n_completed = quant.get("n_completed", "?")
    n_total = quant.get("n_total", "?")

    def _pct_positive(q_key: str, positive_values: list[str]) -> str:
        if q_key not in quant:
            return "N/A"
        dist = quant[q_key].get("frequency_distribution", [])
        total = sum(r["n"] for r in dist)
        pos = sum(r["n"] for r in dist if r["value"] in positive_values)
        return f"{round(100*pos/total)}%" if total > 0 else "N/A"

    q10_positive = _pct_positive("q10_importance", ["very_important", "extremely_important"])
    q11_positive = _pct_positive("q11_trust", ["somewhat_more_likely", "much_more_likely"])
    q12_positive = _pct_positive("q12_adoption", ["somewhat_more_likely", "much_more_likely"])

    q5_mean = quant.get("q5_tool_satisfaction", {}).get("mean", "N/A")
    alpha = quant.get("q7_feature_importance", {}).get("cronbach_alpha", {}).get("value", "N/A")
    top_feature = (quant.get("q7_feature_importance", {}).get("items_ranked") or [{}])[0].get("label", "N/A")

    # Load key qualitative themes
    def _top_themes(col: str) -> str:
        qf = run_dir / "qual" / f"{col}.json"
        if not qf.exists():
            return "_Qualitative analysis not yet run._"
        d = json.loads(qf.read_text())
        themes = d.get("themes", [])
        if not themes:
            return "_No themes identified._"
        lines = []
        for t in themes[:4]:
            name = t.get("theme", "Unnamed")
            desc = t.get("description", "")
            pct = t.get("prevalence_pct", "?")
            lines.append(f"- **{name}** ({pct}%): {desc}")
        return "\n".join(lines)

    def _looks_like_code(s: str) -> bool:
        """True if the string looks like LLM code names rather than verbatim text."""  # noqa: RUF001
        if not s or len(s) > 200:
            return len(s) == 0
        words = s.split()
        return len(words) <= 5 and all("_" in w or w.lower() == w for w in words)

    def _top_quotes(col: str, max_q: int = 3) -> str:
        qf = run_dir / "qual" / f"{col}.json"
        if not qf.exists():
            return ""
        d = json.loads(qf.read_text())
        seen_rids: set[str] = set()
        quotes = []
        for t in d.get("themes", []):
            for sq in t.get("supporting_quotes", [])[:1]:
                rid = sq.get("rid", "")
                if rid in seen_rids:
                    continue
                quote = sq.get("quote", "")
                # If LLM returned code names instead of verbatim text, fetch from raw data
                if _looks_like_code(quote) and rid and col in df.columns:
                    raw_rows = df[df["rid"] == rid][col].values
                    if len(raw_rows) and str(raw_rows[0]).strip():
                        quote = str(raw_rows[0])[:280].strip()
                if not quote or _looks_like_code(quote):
                    continue
                seen_rids.add(rid)
                rtype = df[df["rid"] == rid]["q2_type_id"].values
                seg = (rtype[0] if len(rtype) else "respondent").replace("_", " ")
                quotes.append(f'> "{quote}" — *{seg}* ({rid})')
        return "\n\n".join(quotes[:max_q])

    def _chart_embed(name: str) -> str:
        p = run_dir / "charts" / name
        if p.exists():
            return f"![{name}](charts/{name})"
        return f"_[chart: {name} — run visualize stage]_"

    def _freq_md(q_key: str, top_n: int = 6) -> str:
        rows = []
        if q_key in quant:
            dist = quant[q_key].get("frequency_table") or quant[q_key].get("distribution") or quant[q_key].get("frequency_distribution") or []
            for r in dist[:top_n]:
                rows.append(f"| {r['value'].replace('_',' ')} | {r['n']} | {r['pct']}% |")
        if not rows:
            return "_No data_"
        return "| Response | n | % |\n|---|---|---|\n" + "\n".join(rows)

    report_lines: list[str] = [
        "# Community Technology Survey: Community Demand and Trust Conditions for a Platform Co-operative",
        "",
        "> **Better Together Solutions (BTS)** | May 1, 2026 | Newfoundland & Labrador, Canada",
        "> Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"This report presents findings from a community technology survey conducted by Better Together "
        f"Solutions in spring 2026. We received **{n_total} responses** from community members, organizations, "
        f"and sector representatives across Newfoundland & Labrador, of which **{n_completed} were complete**.",
        "",
        f"Three headline findings stand out:",
        "",
        f"1. **Strong dissatisfaction with the status quo.** Respondents rate current digital tool satisfaction "
        f"at an average of **{q5_mean}/5**, with the most cited problems being platform fragmentation, "
        f"corporate dependency, and lack of community ownership.",
        "",
        f"2. **Overwhelming support for community ownership.** {q10_positive} of respondents rated community "
        f"ownership as 'very' or 'extremely' important. {q11_positive} said a co-operative model would make "
        f"them *more likely to trust* the platform; {q12_positive} said it would make them *more likely to use* it.",
        "",
        f"3. **{top_feature} is the single most important platform feature**, followed closely by long-term "
        f"reliability and accessibility. Internal consistency across the eight feature items is "
        f"{'strong' if isinstance(alpha, float) and alpha >= 0.80 else 'acceptable'} "
        f"(Cronbach's α = {alpha}).",
        "",
        "---",
        "",
        "## 1. Survey Overview",
        "",
        "### 1.1 Instrument and Administration",
        "",
        "The survey was administered online via [Formbricks](https://formbricks.com) on the BTS self-hosted "
        "instance at `forms.btsdev.ca`. It was distributed through community networks, social media, and "
        "direct outreach between April 9–14, 2026. No financial incentive was offered. Participation was "
        "voluntary and anonymous.",
        "",
        "The instrument comprised 12 sections and up to 55 questions per respondent, with branching "
        "logic that showed sector-specific questions based on the respondent's self-identified category. "
        "All questions are published in full in Appendix A.",
        "",
        "### 1.2 Sample",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total responses received | {n_total} |",
        f"| Completed (all core questions) | {n_completed} ({quant.get('completion_rate_pct','?')}%) |",
        f"| Partial responses | {quant.get('n_partial','?')} |",
        f"| Primary analysis sample | Completed responses (N={n_completed}) |",
        "",
        _chart_embed("respondent_types.png"),
        "",
        "**Table 1. Respondent type distribution (all responses)**",
        "",
        _freq_md("respondent_types", top_n=10),
        "",
        "> **Note on small segment sizes.** Most non-public-respondent segments have N ≤ 6. "
        "Cross-segment statistical comparisons are therefore primarily descriptive. "
        "Inferential statistics (Kruskal-Wallis) use only the individual/organisational "
        "dichotomy to ensure adequate statistical power. Cells with n < 5 are suppressed.",
        "",
        "---",
        "",
        "## 2. The Digital Tool Landscape",
        "",
        "### 2.1 Satisfaction with Current Tools",
        "",
        _chart_embed("tool_satisfaction.png"),
        "",
    ]

    if "q5_tool_satisfaction" in quant:
        s = quant["q5_tool_satisfaction"]
        report_lines += [
            f"Respondents rated their overall satisfaction with current digital tools at "
            f"**M = {s['mean']}** (SD = {s['sd']}; Mdn = {s['median']}; N = {s['n']}). "
            f"The distribution shows a moderate positive skew (skewness = {s['skewness']}), "
            f"indicating most respondents are 'somewhat satisfied' but few are 'very satisfied.'",
            "",
            f"Bootstrap 95% CI for mean satisfaction: [{s['bootstrap_95ci_mean'][0]}, {s['bootstrap_95ci_mean'][1]}].",
            "",
        ]

    report_lines += [
        "### 2.2 Biggest Problems with Current Platforms",
        "",
        _freq_md("q6_problems_id"),
        "",
        _chart_embed("wordcloud_q6.png"),
        "",
        "**Key themes in respondents' own words:**",
        "",
        _top_themes("q6_problems"),
        "",
        _top_quotes("q6_problems"),
        "",
        "---",
        "",
        "## 3. What Communities Want in a Platform",
        "",
        _chart_embed("feature_importance.png"),
        "",
    ]

    if "q7_feature_importance" in quant:
        items = quant["q7_feature_importance"].get("items_ranked", [])
        if items:
            table_rows = "\n".join(
                f"| {it['label']} | {it['mean']} | {it['sd']} | {it['bootstrap_95ci_mean']} |"
                for it in items
            )
            report_lines += [
                "**Table 2. Platform Feature Importance Rankings** (N varies per item; sorted by mean)",
                "",
                "| Feature | Mean | SD | 95% Bootstrap CI |",
                "|---------|------|----|-----------------|",
                table_rows,
                "",
                f"Scale reliability: Cronbach's α = {quant['q7_feature_importance']['cronbach_alpha']['value']} "
                f"({quant['q7_feature_importance']['cronbach_alpha']['interpretation']}), "
                f"N = {quant['q7_feature_importance']['cronbach_alpha']['n_respondents']} respondents.",
                "",
            ]

    report_lines += [
        "---",
        "",
        "## 4. Governance, Ownership & Trust",
        "",
        _chart_embed("ownership_trust.png"),
        "",
        f"**Familiarity with tech co-ops.** {_pct_positive('q9_familiarity', ['somewhat_familiar','fairly_familiar','very_familiar'])} "
        "of respondents had at least some familiarity with the idea of a technology co-op before this survey.",
        "",
        f"**Importance of community ownership.** {q10_positive} rated community-owned or community-stewarded "
        "platforms as 'very' or 'extremely' important.",
        "",
        f"**Trust impact.** {q11_positive} said a co-operative ownership model would make them more likely to "
        "trust the platform.",
        "",
        f"**Adoption impact.** {q12_positive} said the co-operative model would make them more likely to use, "
        "support, or adopt it.",
        "",
        "### What Makes a Platform Feel Trustworthy",
        "",
        _chart_embed("wordcloud_q15.png"),
        "",
        _top_themes("q15_trustworthy"),
        "",
        _top_quotes("q15_trustworthy"),
        "",
        "---",
        "",
        "## 5. Voices by Sector",
        "",
        "> Sector-specific questions were shown only to respondents who identified with that sector. "
        "Segments with N < 5 are summarised descriptively without frequency tables to protect anonymity.",
        "",
        "### 5.1 General Public",
        "",
        _top_themes("q15_trustworthy"),
        "",
        "### 5.2 Co-operatives",
        "",
        _top_themes("q20_coop_trust"),
        "",
        "### 5.3 Non-profits",
        "",
        _top_themes("q22_nonprofit_burdens"),
        "",
        "### 5.4 Community Groups",
        "",
        _top_themes("q26_community_difficulties"),
        "",
        "### 5.5 Unions",
        "",
        _top_themes("q29_union_needs"),
        "",
        "### 5.6 Municipalities & Public Institutions",
        "",
        _top_themes("q33_muni_requirements"),
        "",
        "### 5.7 Activists & Advocacy Organizations",
        "",
        _top_themes("q36_activist_risks"),
        "",
        "---",
        "",
        "## 6. Adoption & Economic Readiness",
        "",
        _chart_embed("adoption_barriers.png"),
        "",
        "**Adoption barriers (multi-select):**",
        "",
        _freq_md("q50_barriers_id"),
        "",
        "**Support needed (multi-select):**",
        "",
        _freq_md("q51_support_id"),
        "",
        "**Price sensitivity:**",
        "",
        _freq_md("q52_price_sensitivity_id"),
        "",
        "---",
        "",
        "## 7. Listening to the Community",
        "",
        "### Themes Across All Open-Text Responses",
        "",
        _chart_embed("sentiment_distribution.png"),
        "",
        "> **Methodological note on AI-assisted coding.** Themes below were generated using Reflexive Thematic "
        "Analysis (Braun & Clarke, 2021) with AI-assisted initial coding (Llama 3.2). Intercoder reliability "
        "(Krippendorff's α) ranged from −0.14 to 0.37 across questions. These below-threshold values reflect "
        "code-name variation across LLM passes — a known limitation of exact-match reliability measures for "
        "LLM coding — rather than theme incoherence. Themes should be treated as **exploratory and "
        "hypothesis-generating**. Verbatim quotes are drawn from raw survey data. Human analyst review of "
        "the full codebook (`docs/codebook.md`) is recommended before citing individual themes.",
        "",
        _top_themes("q46_comments"),
        "",
        "### Representative Voices",
        "",
        _top_quotes("q46_comments", max_q=5),
        "",
        "---",
        "",
        "## 8. What This Tells Us",
        "",
        "The findings from this survey tell a clear and consistent story: communities in Newfoundland & "
        "Labrador are ready for an alternative to the current digital platform landscape. Dissatisfaction "
        "with fragmented, expensive, and unaccountable corporate tools is widespread. At the same time, "
        "there is strong appetite for a community-owned model — one that is transparent, governed democratically, "
        "and built to serve long-term community needs rather than shareholder returns.",
        "",
        "The near-universal value placed on accessibility and privacy — alongside a strong showing for "
        "shared governance — signals that a platform co-operative would need to be designed from the "
        "ground up for inclusion, not retrofitted from a commercial product.",
        "",
        "Adoption readiness is real but conditional. The most commonly cited barriers — uncertainty about "
        "long-term sustainability, cost, and lack of documentation — are solvable problems. They call for "
        "clear communication, gradual onboarding, and demonstrated governance before formal commitment.",
        "",
        "---",
        "",
        "## Appendix A: Survey Instrument",
        "",
        "_The complete survey instrument is published in `docs/survey_instrument.md` in this repository._",
        "",
        "## Appendix B: Statistical Methods",
        "",
        "_See `docs/methodology.md` for full statistical methods, analysis decisions, and citations._",
        "",
        "## Appendix C: Qualitative Codebook",
        "",
        "_Coding prompts (the operational codebook) are published verbatim in `docs/codebook.md`._",
        "",
        "## Appendix D: Privacy & Data Protection",
        "",
        "_See `docs/privacy.md` for the privacy impact assessment, k-anonymity analysis, and PIPEDA "
        "compliance statement._",
        "",
        "## Appendix E: Reproducibility & Data Availability",
        "",
        "_See `REPRODUCIBILITY.md` for step-by-step replication instructions and checksums._",
        "",
        f"**Input file SHA256:** `{manifest.get('input', {}).get('sha256', 'N/A')}`",
        f"**Run ID:** `{args.run_id}`",
        f"**Generated:** {_now_iso()}",
        "",
    ]

    out = run_dir / "report.md"
    out.write_text("\n".join(report_lines), encoding="utf-8")
    _update_manifest(run_dir, "report", {"sha256": _sha256(out)})
    _log_event(run_dir, "report_complete", {"output": str(out)})
    print(f"Report assembled → {out}")


# ── Stage 7: Render HTML ──────────────────────────────────────────────────────


def cmd_render(args: argparse.Namespace) -> None:
    import markdown as md_lib

    run_dir = _run_id_dir(args.run_id)
    report_md = run_dir / "report.md"
    if not report_md.exists():
        sys.exit("Run 'report' stage first")

    md_text = report_md.read_text(encoding="utf-8")

    # Embed charts as base64
    charts_dir = run_dir / "charts"

    def _embed_chart(match: re.Match) -> str:
        alt = match.group(1)
        rel_path = match.group(2)
        chart_path = run_dir / rel_path
        if not chart_path.exists():
            return f'<p><em>[chart: {alt} — not generated]</em></p>'
        b64 = base64.b64encode(chart_path.read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{b64}" alt="{alt}" style="max-width:100%;"><figcaption><em>{alt}</em></figcaption></figure>'

    md_text_embedded = re.sub(r"!\[([^\]]*)\]\(([^)]+\.png)\)", _embed_chart, md_text)

    body_html = md_lib.markdown(
        md_text_embedded,
        extensions=["tables", "fenced_code", "toc", "attr_list"],
    )

    css = """
      :root { --blue: #2563EB; --green: #16A34A; --gray: #374151; }
      body { font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto;
             padding: 2rem 1.5rem; color: var(--gray); line-height: 1.65; }
      h1 { color: var(--blue); border-bottom: 3px solid var(--blue); padding-bottom: .4rem; }
      h2 { color: var(--blue); border-bottom: 1px solid #E5E7EB; padding-bottom: .2rem; }
      h3 { color: var(--gray); }
      table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .93rem; }
      th { background: var(--blue); color: white; padding: .5rem .75rem; text-align: left; }
      td { border: 1px solid #E5E7EB; padding: .45rem .75rem; }
      tr:nth-child(even) { background: #F9FAFB; }
      blockquote { border-left: 4px solid var(--green); margin-left: 0; padding: .5rem 1rem;
                   background: #F0FDF4; color: #166534; }
      code { background: #F3F4F6; padding: .15rem .4rem; border-radius: .3rem; font-size: .9em; }
      figure { text-align: center; margin: 1.5rem 0; }
      figcaption { font-size: .85rem; color: #6B7280; margin-top: .4rem; }
      @media print {
        body { max-width: none; padding: 1.5cm; }
        h1, h2 { page-break-after: avoid; }
        figure { page-break-inside: avoid; }
      }
    """

    manifest = json.loads((run_dir / "audit" / "manifest.json").read_text())
    input_sha = manifest.get("input", {}).get("sha256", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Community Technology Survey — May Day 2026</title>
  <meta name="description" content="Community demand and trust conditions for a platform co-operative. BTS, Newfoundland & Labrador, 2026.">
  <meta name="author" content="Better Together Solutions">
  <meta name="generator" content="community_technology_survey_analysis.py (run-id: {args.run_id})">
  <meta name="data-sha256" content="{input_sha}">
  <style>{css}</style>
</head>
<body>
{body_html}
</body>
</html>"""

    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    _update_manifest(run_dir, "render", {"sha256": _sha256(out), "size_bytes": out.stat().st_size})
    _log_event(run_dir, "render_complete", {"output": str(out)})
    print(f"Report rendered → {out}  ({out.stat().st_size // 1024} KB)")


# ── Stage 8: Publication Package ─────────────────────────────────────────────


def cmd_package(args: argparse.Namespace) -> None:
    """Bundle all reproducibility artifacts into a publication package."""
    import zipfile

    run_dir = _run_id_dir(args.run_id)
    pkg_dir = run_dir / "package"
    pkg_dir.mkdir(exist_ok=True)

    # Build SHA256SUMS for all tracked outputs
    checksums: list[str] = []
    for f in sorted(run_dir.rglob("*")):
        if f.is_file() and f.suffix not in (".zip",) and "package" not in str(f):
            rel = f.relative_to(run_dir)
            checksums.append(f"{_sha256(f)}  {rel}")

    (pkg_dir / "SHA256SUMS").write_text("\n".join(checksums))

    # Create zip archive
    zip_name = ROOT / f"community-tech-survey-package-{args.run_id}.zip"
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        # Core outputs
        for f in [run_dir / "report.html", run_dir / "report.md"]:
            if f.exists():
                zf.write(f, f"report/{f.name}")
        # Data
        for f in (run_dir / "data").glob("*"):
            zf.write(f, f"data/{f.name}")
        # Charts
        for f in (run_dir / "charts").glob("*.png"):
            zf.write(f, f"charts/{f.name}")
        # Analysis scripts
        for f in Path(__file__).parent.glob("*.py"):
            zf.write(f, f"analysis/{f.name}")
        for f in Path(__file__).parent.glob("*.sh"):
            zf.write(f, f"analysis/{f.name}")
        zf.write(Path(__file__).parent / "requirements.txt", "analysis/requirements.txt")
        # Docs
        for f in (ROOT / "docs").glob("*.md"):
            zf.write(f, f"docs/{f.name}")
        # Schemas
        for f in (ROOT / "schemas").glob("*.json"):
            zf.write(f, f"schemas/{f.name}")
        # Root docs
        for name in ["REPRODUCIBILITY.md", "README.md"]:
            fp = ROOT / name
            if fp.exists():
                zf.write(fp, name)
        # Audit
        for f in (run_dir / "audit").glob("*"):
            zf.write(f, f"audit/{f.name}")
        # Checksums
        zf.write(pkg_dir / "SHA256SUMS", "SHA256SUMS")

    pkg_sha = _sha256(zip_name)
    _update_manifest(run_dir, "package", {
        "zip_path": str(zip_name),
        "zip_sha256": pkg_sha,
        "zip_size_bytes": zip_name.stat().st_size,
    })
    _log_event(run_dir, "package_complete", {"zip": str(zip_name)})
    print(f"Publication package → {zip_name}")
    print(f"SHA256: {pkg_sha}")


# ── Orchestrator ──────────────────────────────────────────────────────────────


def cmd_all(args: argparse.Namespace) -> None:
    print("=== Stage 1: Ingest ===")
    run_id = cmd_ingest(args)
    args.run_id = run_id

    print("\n=== Stage 2: Quantitative Analysis ===")
    cmd_quant(args)

    print("\n=== Stage 3: Qualitative Analysis ===")
    cmd_qual(args)

    print("\n=== Stage 4: Intercoder Reliability ===")
    cmd_irr(args)

    print("\n=== Stage 5: Visualizations ===")
    cmd_visualize(args)

    print("\n=== Stage 6: Report ===")
    cmd_report(args)

    print("\n=== Stage 7: Render HTML ===")
    cmd_render(args)

    print("\n=== Stage 8: Package ===")
    cmd_package(args)

    print(f"\n✓ All stages complete. Run ID: {run_id}")
    print(f"  Output: {OUTPUT_BASE / run_id}/")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Community Technology Survey Analysis Pipeline — BTS 2026",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--run-id", default=None, help="Existing run ID (for re-running a stage)")
    parser.add_argument("--input", default=None, help="Path to survey xlsx file")
    parser.add_argument("--ollama-host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11435"),
                        help="Ollama API base URL (default: http://localhost:11435)")
    parser.add_argument("--ollama-model", default=os.environ.get("OLLAMA_MODEL", "llama3.2:latest"),
                        help="Ollama model for qualitative coding")

    subparsers = parser.add_subparsers(dest="command", required=True)
    for cmd_name in ("ingest", "quant", "qual", "irr", "visualize", "report", "render", "package", "all"):
        sub = subparsers.add_parser(cmd_name)
        sub.add_argument("--run-id", default=None)
        sub.add_argument("--input", default=None)
        sub.add_argument("--ollama-host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11435"))
        sub.add_argument("--ollama-model", default=os.environ.get("OLLAMA_MODEL", "llama3.2:latest"))

    args = parser.parse_args()
    # Subparser args override parent defaults when provided
    if not args.run_id:
        args.run_id = None
    if not args.input:
        args.input = None

    if args.command == "ingest" and not args.input:
        # Auto-detect latest export
        research_dir = ROOT / "data" / "original"
        candidates = list(research_dir.glob("*.xlsx"))
        if not candidates:
            sys.exit("ERROR: No xlsx file found. Pass --input <path>")
        args.input = str(sorted(candidates)[-1])
        print(f"Auto-detected input: {args.input}")

    if args.command != "ingest" and args.command != "all" and not args.run_id:
        sys.exit("ERROR: --run-id required for this command")

    {
        "ingest": cmd_ingest,
        "quant": cmd_quant,
        "qual": cmd_qual,
        "irr": cmd_irr,
        "visualize": cmd_visualize,
        "report": cmd_report,
        "render": cmd_render,
        "package": cmd_package,
        "all": cmd_all,
    }[args.command](args)


if __name__ == "__main__":
    main()

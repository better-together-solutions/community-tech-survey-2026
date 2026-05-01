#!/usr/bin/env python3
"""
Privacy Impact Assessment and Anonymisation Verification
Community Technology Survey — BTS 2026

Implements:
  - K-anonymity (Sweeney, 2002): ensures no respondent can be uniquely identified
    from the combination of quasi-identifiers in the published dataset (k ≥ 5)
  - L-diversity (Machanavajjhala et al., 2007): ensures sensitive attribute diversity
    within equivalence classes
  - Small cell suppression: cross-tabulation cells with n < MIN_CELL are suppressed
  - PIPEDA compliance summary (Personal Information Protection and Electronic
    Documents Act, S.C. 2000, c. 5)

Usage:
  python3 community_technology_survey_privacy.py --run-id <id>
  python3 community_technology_survey_privacy.py --run-id <id> --min-k 5
  python3 community_technology_survey_privacy.py check --csv data/sanitized/survey.csv

References:
  Sweeney, L. (2002). k-anonymity: A model for protecting privacy.
    International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems, 10(5), 557-570.
  Machanavajjhala, A. et al. (2007). l-diversity: Privacy beyond k-anonymity.
    ACM Transactions on Knowledge Discovery from Data, 1(1), Article 3.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
OUTPUT_BASE = ROOT / "output"
MIN_CELL_DEFAULT = 5

# Quasi-identifiers: attributes that, in combination, could re-identify a respondent.
# These are the columns present in the PUBLISHED sanitized dataset (device metadata
# is stripped before publication — see PUBLISHED_DROP_COLS below).
QUASI_IDENTIFIERS = [
    "q2_type_id",        # respondent sector (general_public, co_op, etc.)
    "q3_perspective_id", # personal vs organisational
    "finished",          # completed vs partial
]

# Columns dropped from the published sanitized CSV.
# Removes: device fingerprint, completion metadata, timestamp, and perspective
# (perspective is derivable from q2_type_id and adds k-anonymity risk for
# small org segments where only 1-2 people answered as 'organizational').
PUBLISHED_DROP_COLS = [
    "ua_os", "ua_device", "ua_browser",   # device fingerprint
    "timestamp",                            # could narrow identity by response date
    "finished",                             # operational metadata
    "q3_perspective", "q3_perspective_id",  # correlated with q2_type_id, adds k risk
]

# Sensitive attributes for l-diversity check
SENSITIVE_ATTRIBUTES = [
    "q9_familiarity_id",
    "q10_importance_id",
    "q11_trust_id",
]


def load_df(run_id: str):
    import pandas as pd
    norm_json = OUTPUT_BASE / run_id / "data" / "normalized.json"
    if not norm_json.exists():
        sys.exit(f"Normalized data not found: {norm_json}. Run 'ingest' first.")
    return pd.read_json(norm_json, orient="records")


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_k_anonymity(df, quasi_ids: list[str], min_k: int = 5) -> dict[str, Any]:
    """
    Checks k-anonymity: every equivalence class (unique combination of
    quasi-identifier values) must have at least k members.
    """
    available_qi = [q for q in quasi_ids if q in df.columns]
    if not available_qi:
        return {"error": "No quasi-identifier columns found in dataset"}

    df_qi = df[available_qi].fillna("__missing__")
    group_sizes = df_qi.groupby(available_qi).size().reset_index(name="_count")

    violations = group_sizes[group_sizes["_count"] < min_k]
    smallest_group = int(group_sizes["_count"].min())
    k_achieved = smallest_group

    return {
        "quasi_identifiers_checked": available_qi,
        "k_target": min_k,
        "k_achieved": k_achieved,
        "passes": bool(k_achieved >= min_k),
        "n_equivalence_classes": int(len(group_sizes)),
        "n_violating_classes": int(len(violations)),
        "violating_classes": violations.to_dict("records") if len(violations) > 0 else [],
        "recommendation": (
            "Dataset meets k-anonymity threshold."
            if k_achieved >= min_k else
            f"WARNING: {len(violations)} equivalence classes have fewer than {min_k} members. "
            "Consider: (1) generalising quasi-identifier values, (2) suppressing rare combinations, "
            "or (3) reducing the number of quasi-identifiers published."
        ),
        "reference": "Sweeney (2002). k-anonymity: A model for protecting privacy.",
    }


def check_l_diversity(df, quasi_ids: list[str], sensitive_attrs: list[str], min_l: int = 2) -> dict[str, Any]:
    """
    Checks l-diversity: within each equivalence class, the sensitive attribute
    must have at least l distinct values (Machanavajjhala et al., 2007).
    """
    available_qi = [q for q in quasi_ids if q in df.columns]
    available_sa = [s for s in sensitive_attrs if s in df.columns]

    if not available_qi or not available_sa:
        return {"skipped": "Insufficient columns for l-diversity check"}

    results_per_attr: dict[str, Any] = {}
    for sa in available_sa:
        df_check = df[available_qi + [sa]].fillna("__missing__")
        diversity = df_check.groupby(available_qi)[sa].nunique().reset_index(name="_diversity")
        violations = diversity[diversity["_diversity"] < min_l]
        results_per_attr[sa] = {
            "l_target": min_l,
            "l_achieved_min": int(diversity["_diversity"].min()),
            "passes": bool(diversity["_diversity"].min() >= min_l),
            "n_violating_classes": int(len(violations)),
        }

    return {
        "quasi_identifiers": available_qi,
        "sensitive_attributes": available_sa,
        "results": results_per_attr,
        "reference": "Machanavajjhala et al. (2007). l-diversity: Privacy beyond k-anonymity.",
    }


def check_pii_removal(df) -> dict[str, Any]:
    """Verify that known PII columns have been removed."""
    pii_aliases = ["q64_contact_pii", "q65_outreach_pii"]
    pii_present = [c for c in pii_aliases if c in df.columns]
    direct_id_cols = ["response_id", "user_id", "formbricks_id", "row_no"]
    id_present = [c for c in direct_id_cols if c in df.columns]

    # Check for email-like patterns in any remaining text field
    import re
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    text_cols = df.select_dtypes(include="object").columns.tolist()
    cols_with_emails: list[str] = []
    for col in text_cols:
        if col in ("rid",):
            continue
        sample = " ".join(str(v) for v in df[col].dropna().values[:200])
        if email_pattern.search(sample):
            cols_with_emails.append(col)

    return {
        "pii_columns_present": pii_present,
        "direct_id_columns_present": id_present,
        "columns_with_email_pattern": cols_with_emails,
        "pii_removed": len(pii_present) == 0 and len(id_present) == 0,
        "warning": (
            f"ALERT: Columns with email-like patterns found: {cols_with_emails}"
            if cols_with_emails else None
        ),
        "note": (
            "Anonymous respondent IDs (R001..RN) replace all original system identifiers. "
            "Name/email fields (q64, q65) are excluded from published dataset."
        ),
    }


def small_cell_suppression_report(df, min_cell: int = 5) -> dict[str, Any]:
    """
    Identifies cross-tabulations that would produce cells below the suppression threshold.
    Reports which segment × question combinations should not be published as frequency tables.
    """
    if "q2_type_id" not in df.columns:
        return {"skipped": "No respondent type column found"}

    segment_counts = df["q2_type_id"].value_counts().to_dict()
    suppress_segments = [seg for seg, n in segment_counts.items() if n < min_cell]

    return {
        "min_cell_threshold": min_cell,
        "segment_counts": {str(k): int(v) for k, v in segment_counts.items()},
        "segments_below_threshold": suppress_segments,
        "suppression_rule": (
            f"Frequency tables disaggregated by respondent type are suppressed for "
            f"segments with n < {min_cell}: {suppress_segments}. "
            "These segments are reported descriptively (qualitative quotes) only."
        ),
        "reference": (
            "Statistics Canada (2012). Suppression and other protective measures "
            "for small cells. Section 5.1."
        ),
    }


def pipeda_compliance_summary() -> dict[str, Any]:
    """Summary of PIPEDA compliance measures for this dataset."""
    return {
        "legislation": "Personal Information Protection and Electronic Documents Act (PIPEDA), S.C. 2000, c. 5",
        "province": "Newfoundland & Labrador, Canada",
        "principles_addressed": {
            "1_accountability": "Better Together Solutions (BTS) is the data controller. Contact: rob@bettertogethersolutions.com",
            "2_identifying_purposes": "Survey purpose was disclosed: research on community demand for a platform co-operative.",
            "3_consent": "Participation was voluntary. Q63 captured optional consent for contact re-use. Consent status recorded.",
            "4_limiting_collection": "Only data relevant to the research purpose was collected. Contact fields were optional.",
            "5_limiting_use": "Data used only for published community research. No sale or transfer to third parties.",
            "6_accuracy": "Responses published verbatim (anonymised). No imputation of missing values.",
            "7_safeguards": "Raw data stored on BTS self-hosted infrastructure. Published dataset is k-anonymised (k≥5).",
            "8_openness": "Analysis methodology, privacy measures, and data availability statement are published.",
            "9_individual_access": "Respondents who provided contact details may request their record. Contact BTS.",
            "10_challenging_compliance": "Privacy concerns can be raised with BTS or the OPC (Office of the Privacy Commissioner of Canada).",
        },
        "data_retention": "Raw survey data retained for 3 years from collection date, then securely deleted.",
        "published_dataset": "Anonymised (k≥5) CSV only. No direct identifiers. No contact information.",
        "consent_for_quotes": (
            "All verbatim quotes in the published report are identified only by respondent sector and "
            "anonymous ID (R001..RN). Respondents who provided contact details (Q63 = 'accepted') may "
            "be contacted for follow-up but are not attributed by name in published outputs without "
            "separate written consent."
        ),
    }


def export_sanitized_csv(df, run_id: str, min_k: int = MIN_CELL_DEFAULT) -> Path:
    """
    Export a k-anonymity-compliant sanitized CSV for public release.

    Applies:
    1. Device fingerprint columns stripped (PUBLISHED_DROP_COLS)
    2. Respondent types with n < min_k generalised to 'other_organisation'
       (Sweeney, 2002 generalisation hierarchy for k-anonymity)
    """
    import pandas as pd
    sanitized_dir = ROOT / "data" / "sanitized"
    sanitized_dir.mkdir(parents=True, exist_ok=True)

    drop = [c for c in PUBLISHED_DROP_COLS if c in df.columns]
    pub_df = df.drop(columns=drop).copy()

    # Generalise rare respondent types (k-anonymity generalisation step)
    if "q2_type_id" in pub_df.columns:
        counts = pub_df["q2_type_id"].value_counts()
        rare = counts[counts < min_k].index.tolist()
        if rare:
            pub_df["q2_type_id"] = pub_df["q2_type_id"].apply(
                lambda v: "other_organisation" if v in rare else v
            )
            # Same generalisation on the text column for consistency
            if "q2_type" in pub_df.columns:
                pub_df["q2_type"] = pub_df["q2_type"].apply(
                    lambda v: "Other / not specified" if pub_df.loc[
                        pub_df["q2_type"] == v, "q2_type_id"
                    ].eq("other_organisation").any() else v
                )

    out = sanitized_dir / f"community_technology_survey_sanitized_{run_id}.csv"
    pub_df.to_csv(out, index=False, quoting=1)  # QUOTE_ALL
    return out


def cmd_check(args: argparse.Namespace) -> None:
    import pandas as pd

    if args.csv:
        df = pd.read_csv(args.csv, dtype=str)
        run_id = "csv_check"
    else:
        if not args.run_id:
            sys.exit("ERROR: --run-id or --csv required")
        df = load_df(args.run_id)
        run_id = args.run_id

    # For publication k-anonymity check, use only the columns that will be published
    if run_id != "csv_check":
        pub_csv = export_sanitized_csv(df, run_id)
        df_pub = pd.read_csv(pub_csv, dtype=str)
        print(f"Sanitized CSV exported → {pub_csv}")
    else:
        df_pub = df

    min_k = getattr(args, "min_k", MIN_CELL_DEFAULT)

    results: dict[str, Any] = {
        "run_id": run_id,
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "note_published_dataset": (
            "PII check and k-anonymity are applied to the PUBLISHED sanitized dataset "
            f"(device fingerprint columns {PUBLISHED_DROP_COLS} are stripped before publication). "
            "Analysis dataset retains device columns for internal use only."
        ),
        "pii_check": check_pii_removal(df),
        "k_anonymity": check_k_anonymity(df_pub, QUASI_IDENTIFIERS, min_k),
        "l_diversity": check_l_diversity(df_pub, QUASI_IDENTIFIERS, SENSITIVE_ATTRIBUTES),
        "small_cell_suppression": small_cell_suppression_report(df_pub, min_k),
        "pipeda_compliance": pipeda_compliance_summary(),
    }

    overall_pass = (
        results["pii_check"]["pii_removed"]
        and results["k_anonymity"].get("passes", False)
    )
    results["overall_privacy_pass"] = overall_pass
    results["publish_recommendation"] = (
        "APPROVED for publication: PII removed and k-anonymity satisfied."
        if overall_pass else
        "NOT APPROVED: Privacy requirements not fully met. See individual checks above."
    )

    print(json.dumps(results, indent=2, default=str))

    # Save to audit if run_id is a real run
    if run_id != "csv_check":
        out_dir = OUTPUT_BASE / run_id / "audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "privacy_report.json"
        out.write_text(json.dumps(results, indent=2, default=str))
        print(f"\nPrivacy report saved → {out}")

    if not overall_pass:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Privacy impact assessment for community technology survey dataset"
    )
    parser.add_argument("command", nargs="?", default="check", choices=["check"])
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--csv", default=None, help="Path to CSV file (alternative to run-id)")
    parser.add_argument("--min-k", type=int, default=MIN_CELL_DEFAULT,
                        help=f"Minimum k for k-anonymity (default: {MIN_CELL_DEFAULT})")
    args = parser.parse_args()
    cmd_check(args)


if __name__ == "__main__":
    main()

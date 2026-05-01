# Privacy Impact Assessment

**Community Technology Survey — Better Together Solutions, May 2026**

---

## 1. Overview

This document describes the privacy measures applied to the community technology survey dataset in compliance with the *Personal Information Protection and Electronic Documents Act* (PIPEDA, S.C. 2000, c. 5) and best practices in research data protection.

**Data Controller:** Better Together Solutions (BTS)
**Contact:** rob@bettertogethersolutions.com
**Data Protection Officer:** Rob Currie, Director

---

## 2. Information Collected

The survey collected the following categories of information:

| Category | Fields | Sensitivity |
|----------|--------|-------------|
| System metadata | Response ID, Timestamp, Survey ID, Formbricks ID, User ID, URL | Low — system-generated |
| Device metadata | Operating system, device type, browser | Low — aggregate use only |
| Demographic | Respondent type (sector), personal vs. organisational perspective | Medium |
| Opinion/attitude | Satisfaction ratings, Likert scales, categorical preferences | Low-medium |
| Free-text responses | Open-ended opinions and experiences | Medium — may be identifying |
| Contact (optional) | Name, email, organisation, best time to reach | **High — direct PII** |
| Consent | Consent to contact re-use (Q63) | N/A |

---

## 3. Measures Applied

### 3.1 PII Removal

Before any data is published or analysed beyond BTS infrastructure, the following fields are **removed entirely**:
- `q64_contact_pii` — name, email, organisation name
- `q65_outreach_pii` — availability and outreach preferences
- `response_id`, `formbricks_id`, `user_id`, `row_no`, `survey_id`, `url` — system identifiers

These fields are retained only in the raw data held on BTS self-hosted infrastructure and are not included in any published dataset.

**Replacement:** Respondents are assigned sequential anonymous IDs (R001, R002, ..., RN) that have no relationship to the original system-assigned identifiers.

### 3.2 K-Anonymity (Sweeney, 2002)

**K-anonymity** ensures that no respondent can be uniquely identified by the combination of quasi-identifiers (attributes that, while not directly identifying, could re-identify someone in combination).

**Quasi-identifiers used:** respondent type, perspective (personal/organisational), device OS, device type, completed/partial.

**Target:** k ≥ 5 (every combination of quasi-identifier values applies to at least 5 respondents).

Verification is performed by `analysis/community_technology_survey_privacy.py`. Results are in `output/<run_id>/audit/privacy_report.json`.

If k < 5 for any equivalence class, the following mitigations are applied in order:
1. Generalise the quasi-identifier value (e.g., merge rare OS values into "Other")
2. Suppress the row from the published dataset
3. Reduce the set of quasi-identifiers published

### 3.3 Small Cell Suppression

Cross-tabulation cells with n < 5 are suppressed in all published frequency tables. Segments with fewer than 5 respondents are reported descriptively (e.g., "A small number of union respondents...") rather than as counted frequency tables.

This is consistent with Statistics Canada (2012) suppression guidelines and ensures that highly specific combinations cannot be used to infer an individual's responses.

**Affected segments:** co_op (n=6 borderline), non_profit (n=2), union (n=2), activist (n=2), municipality (n=1), other (n=2). Segments with n < 5 are treated descriptively only.

### 3.4 Free-Text Handling

Open-text responses are published verbatim in the analysis outputs but are checked for:
- Email addresses (regex scan)
- Organisation names that are sufficiently unique to identify the respondent
- References that make the respondent's identity apparent in combination with their sector

Where identified, such passages are redacted with `[redacted]` and noted in the audit log. Verbatim quotes in the published report are attributed only by sector and anonymous ID.

### 3.5 Consent Management

Q63 asked respondents for optional consent to use their contact details for follow-up. The consent flag is retained in the analysis dataset (as a binary indicator) but the contact details themselves are removed.

Respondents who consented (Q63 = 'accepted') may be contacted by BTS for follow-up research. They will not be identified by name in any publication without separate, specific written consent.

---

## 4. PIPEDA Compliance Summary

| Principle | Compliance Measure |
|-----------|-------------------|
| Accountability | BTS is data controller; contact: rob@bettertogethersolutions.com |
| Identifying purposes | Purpose stated in survey introduction: community research on co-op platform |
| Consent | Voluntary participation; separate Q63 for contact re-use |
| Limiting collection | Only relevant fields collected; contact was optional |
| Limiting use, disclosure, retention | Data used for published research only; no third-party transfer |
| Accuracy | Responses published as received; no imputation |
| Safeguards | Self-hosted BTS infrastructure; k-anonymised published dataset |
| Openness | This document, the methodology, and the analysis code are publicly available |
| Individual access | Respondents who provided contact can request their record via rob@bettertogethersolutions.com |
| Challenging compliance | Complaints to OPC: www.priv.gc.ca |

---

## 5. Data Retention

| Data Type | Retention Period | Disposal Method |
|-----------|-----------------|-----------------|
| Raw survey export (with PII) | 3 years from collection | Secure deletion from BTS server |
| Anonymised analysis dataset | Indefinite (published) | N/A — public record |
| Audit logs | 5 years | Secure deletion |
| Contact list (consented respondents) | Until contact or 1 year | Secure deletion |

---

## 6. Researcher Responsibilities

Any researcher using the published dataset must:
1. Not attempt to re-identify respondents
2. Not combine the dataset with other datasets for re-identification purposes
3. Cite this privacy assessment when discussing data protection measures
4. Report suspected re-identification risks to rob@bettertogethersolutions.com

---

## 7. References

- Machanavajjhala, A., Kifer, D., Gehrke, J., & Venkitasubramaniam, M. (2007). l-diversity: Privacy beyond k-anonymity. *ACM TKDD*, 1(1).
- Personal Information Protection and Electronic Documents Act, S.C. 2000, c. 5. https://laws-lois.justice.gc.ca/eng/acts/P-8.6/
- Statistics Canada. (2012). *Suppression and other protective measures for small cells.* Cat. no. 12-587-X.
- Sweeney, L. (2002). k-anonymity: A model for protecting privacy. *IJUFKS*, 10(5), 557–570.

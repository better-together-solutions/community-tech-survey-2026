# Qualitative Codebook

**Community Technology Survey — BTS 2026**

This document is the **operational codebook** for the AI-assisted Reflexive Thematic Analysis of open-text survey responses. It is published verbatim so that any researcher can verify, replicate, or challenge the coding decisions.

---

## Overview

Coding was performed using a large language model (LLM) via the Ollama API (see `docs/methodology.md §6.3` for model details and version). Two prompts were used per question: an **initial coding prompt** and a **theme synthesis prompt**. These prompts define the coding unit, the expected output format, and any instructions that constrain the analysis.

All prompts were fixed before analysis began and are hashed (SHA256) in the audit manifest. They were not modified between questions.

---

## Prompt 1: Initial Coding

This prompt implements **Phase 2** of Reflexive Thematic Analysis (Braun & Clarke, 2021): generating initial codes.

**Coding unit:** Each individual survey response (one row = one coding unit).

**Instructions given to the LLM:**

```
You are a qualitative research assistant performing initial thematic coding
following Reflexive Thematic Analysis (Braun & Clarke, 2021).

Below are survey responses to the question: "{question_label}"

TASK: Generate initial codes for each response. For each response:
1. Assign 1–3 descriptive codes (2–5 words each, lower_snake_case)
2. Note the sentiment: positive / negative / neutral / mixed
3. Flag if the response contains a notable direct quote (max 20 words)

Respond ONLY with a JSON array. Each element:
{
  "rid": "<respondent_id>",
  "codes": ["code_one", "code_two"],
  "sentiment": "positive|negative|neutral|mixed",
  "notable_quote": "<verbatim quote or null>"
}

Responses:
{responses}
```

**Output format:** JSON array with one object per response.

**Code format rules:**
- 2–5 words, lower_snake_case
- Descriptive (what the respondent said), not interpretive (what the researcher infers)
- Example: `corporate_platform_distrust`, `accessibility_barriers`, `governance_transparency_need`

**Sentiment categories:**
| Category | Definition |
|----------|-----------|
| `positive` | Response expresses support, satisfaction, hope, or enthusiasm |
| `negative` | Response expresses concern, frustration, opposition, or distrust |
| `neutral` | Factual or balanced response without clear valence |
| `mixed` | Response contains both positive and negative elements |

---

## Prompt 2: Theme Synthesis

This prompt implements **Phase 3** of Reflexive Thematic Analysis: searching for themes across codes.

**Unit of analysis:** The full set of initial codes and responses for one question.

**Instructions given to the LLM:**

```
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
{
  "theme": "<Theme Name>",
  "description": "...",
  "prevalence_pct": <number>,
  "supporting_quotes": [
    {"rid": "R001", "quote": "..."},
    {"rid": "R002", "quote": "..."}
  ],
  "member_codes": ["code_one", "code_two"]
}
```

**Output format:** JSON array with one object per theme.

**Theme naming guidance given to LLM:**
- Names should capture the essential meaning, not be abstract labels
- Range: 3–7 words
- Example: "Distrust of Corporate Data Practices", "Desire for Democratic Governance", "Accessibility as a Core Requirement"

---

## Intercoder Reliability (Second-Pass) Protocol

A 20% random sample of responses is re-coded in a second independent pass using **identical prompts**. The random sample is selected with seed = 42 (`numpy.random.default_rng(42)`). Krippendorff's alpha (nominal) is computed by comparing the primary code (first element of `codes` array) between Pass 1 and Pass 2.

Full IRR results: `output/<run_id>/qual/irr_results.json`.

---

## Analyst Notes (Human Review)

The following notes were added by the human analyst after reviewing LLM-generated themes:

_[To be completed by the analyst during the report stage. Note any themes that were split, merged, renamed, or rejected, and the rationale. These notes become part of the permanent audit record.]_

---

## Limitations of AI-Assisted Coding

1. **LLM hallucination risk.** LLMs may produce plausible-sounding but inaccurate quotes or codes. All supporting quotes in the published report should be verified against the raw data (`output/<run_id>/data/raw.csv`) by column and `rid`.

2. **Prompt sensitivity.** Small changes to prompt wording can alter themes. Prompts are fixed and published to enable challenge and replication.

3. **No lived-experience perspective.** LLMs do not share the lived experience of community members in Newfoundland & Labrador. Cultural and local context may be missed. Human analyst review is essential.

4. **English-language only.** The coding prompts and model were English-only. No French-language or Indigenous-language responses were received in this dataset, but this should be addressed in future administrations.

5. **Prevalence estimates are approximations.** The LLM's `prevalence_pct` is a qualitative estimate, not a counted frequency. Counted frequencies can be derived from the `initial_codes` data.

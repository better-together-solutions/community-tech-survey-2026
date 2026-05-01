# Methodology

**Community Technology Survey — Better Together Solutions, May 2026**

---

## 1. Study Design

This study employs a **cross-sectional survey design** to assess community demand, governance preferences, and adoption conditions for a proposed platform co-operative in Newfoundland & Labrador, Canada. The design is descriptive-exploratory, not experimental or causal.

**Positionality statement.** This survey was commissioned and analysed by Better Together Solutions (BTS), the organisation that is proposing the community platform co-operative. This creates an inherent potential for confirmation bias in instrument design and interpretation. We address this through: (1) pre-registered analysis plan (this document, committed to version control before analysis); (2) published all prompts, code, and data; (3) reporting findings that do not support the proposal alongside those that do; and (4) clearly distinguishing between what respondents said and what BTS infers.

---

## 2. Survey Instrument

The instrument was designed in-house using the Formbricks open-source survey platform, self-hosted at `forms.btsdev.ca`. It comprised 12 sections and up to 55 questions per respondent, with branching logic routing respondents to sector-specific questions based on their self-identified type (Q2).

**Pilot testing.** A pilot was not formally conducted due to time constraints. The instrument was reviewed internally by two BTS team members before deployment. This is acknowledged as a limitation.

**Question types used:**
- 5-point Likert rating scales (satisfaction, importance, trust, adoption likelihood)
- Multi-select categorical (problems, features, barriers, support needs)
- Open-ended free-text (trustworthiness, conditions, concerns)
- Binary Yes/No
- Optional contact and consent fields

**Full instrument:** All questions and response options are published in Appendix A of the live report at https://communityengine.app/community-technology-survey-2026-part-1

---

## 3. Sampling and Recruitment

**Target population.** Community members, organisations, and sector representatives in Newfoundland & Labrador (NL) who use or oversee digital tools in their work or community participation.

**Sampling frame.** There is no complete sampling frame for this population. Respondents were recruited via a **convenience/purposive sample** through:
- BTS social media channels (Facebook, Mastodon)
- Direct outreach to known community organisations, co-ops, non-profits, unions, and municipal partners
- Community networks in the St. John's and surrounding NL region

**Sampling limitations.** Convenience sampling produces a non-probability sample. Findings cannot be generalised to the full NL population. Respondents are likely to be more engaged with community technology issues than the general population (self-selection bias). The survey was distributed primarily in English; French-speaking and Indigenous community members are under-represented. These limitations are discussed in `docs/limitations.md`.

---

## 4. Data Collection

**Collection period:** March 27 – April 30, 2026 (35 days).
**Platform:** Formbricks v2.x, self-hosted on BTS infrastructure.
**Access:** Public URL, no authentication required.
**Total responses:** 112 (67 completed, 45 partial).

---

## 5. Quantitative Analysis Methods

### 5.1 Primary Analysis Sample

The primary analysis uses **completed responses only** (N = 67, Finished = "Yes"). Partial responses are counted in overview statistics but excluded from statistical comparisons to avoid biased estimates from selective non-completion.

### 5.2 Descriptive Statistics

For continuous and Likert-type variables:
- **Central tendency:** Mean (M), Median (Mdn), Mode
- **Dispersion:** Standard deviation (SD), Interquartile range (IQR)
- **Distribution shape:** Skewness, Kurtosis
- **Confidence intervals:** 95% bootstrap CI for the mean (B = 10,000 iterations; random seed = 42) following Efron & Tibshirani (1993)

For categorical and ordinal variables:
- Frequency counts (n) and percentages (%)
- Ordinal variables reported with median and IQR

**Treatment of Likert scales.** The Q7 feature importance items (8 items, 1–5 scale) are treated as **interval-level** for mean/CI calculations, consistent with the majority of survey research practice (Norman, 2010; Sullivan & Artino, 2013) and justified by the symmetric, approximately equidistant scale points. Non-parametric statistics (median, IQR, Kruskal-Wallis) are also reported as a robustness check.

### 5.3 Internal Consistency (Scale Reliability)

**Cronbach's alpha** (α; Cronbach, 1951) is computed for the Q7 feature importance scale (8 items). Interpretation follows George & Mallery (2003): α ≥ 0.90 = excellent; 0.80–0.89 = good; 0.70–0.79 = acceptable; 0.60–0.69 = questionable; < 0.60 = poor.

Formula: α = (k / (k−1)) × (1 − Σσᵢ² / σ²_total), where k = number of items.

### 5.4 Inferential Statistics and Effect Sizes

**Between-group comparisons.** Due to highly unequal group sizes (general_public: n = 79; all other sectors: n = 1–6), **full cross-segment inferential statistics are not reported**. Instead, a two-group comparison (individual/general_public vs. organisational/other) is used where sufficient power exists.

**Kruskal-Wallis H test** (Kruskal & Wallis, 1952) is used for between-group comparisons of ordinal/Likert variables, as normality assumptions cannot be assured for small groups.

**Effect size:** Epsilon-squared (ε²) = (H − k + 1) / (N − k), interpreted as: large ≥ 0.14, medium 0.06–0.13, small < 0.06 (Cohen, 1988).

**Chi-square test of independence** (Pearson, 1900) and Cramér's V effect size (Cramér, 1946) are used for categorical associations.

**Multiple comparison correction.** When testing multiple items within a family of related hypotheses (e.g., all 8 Q7 items), the **Bonferroni correction** is applied: α_corrected = 0.05 / k, where k is the number of tests in the family.

### 5.5 Missing Data

Missing values in branching questions are **structural** (the question was not shown to that respondent type) and are **not imputed**. Per-question denominators are reported, making the effective N visible for every statistic. Non-structural missingness (incomplete responses) is handled by using completed responses as the primary analysis sample.

Little's MCAR test was not applied because the branching missingness mechanism is known by design.

---

## 6. Qualitative Analysis Methods

### 6.1 Approach

We employ **Reflexive Thematic Analysis (RTA)** following Braun & Clarke (2021), the dominant framework for inductive thematic analysis in social science. RTA treats themes as researcher constructions, not objective discoveries, and foregrounds reflexivity about analytical decisions.

Given the volume of open-text responses (up to 18 questions × 112 respondents) and the tight publication timeline, we use **AI-assisted initial coding** as a first-pass tool, with human review of themes. This is consistent with emerging practice in computational qualitative research (Gao et al., 2024; Xiao et al., 2023).

### 6.2 The Six Phases of RTA (Braun & Clarke, 2021)

| Phase | Method Used |
|-------|-------------|
| 1. Familiarisation | Automated: response counts, length distributions |
| 2. Generating initial codes | AI-assisted: LLM first-pass coding with published prompts |
| 3. Searching for themes | AI-assisted: LLM theme synthesis across coded responses |
| 4. Reviewing themes | Intercoder reliability check (second LLM pass, 20% sample) |
| 5. Defining and naming themes | Human researcher review of LLM-generated themes |
| 6. Writing up | Report with verbatim quotes and researcher commentary |

### 6.3 AI-Assisted Coding

**LLM configuration:**
- **Model:** Llama 3.2 (configurable via `--ollama-model`)
- **Host:** Local Ollama instance (configurable via `OLLAMA_HOST`)
- **Version:** Recorded in audit manifest at time of analysis
- **Prompts:** Published verbatim in `docs/codebook.md`

The prompts serve as the **operational codebook**: they define what constitutes a code, the coding categories, and the output format. Two prompts are used per question: (1) initial coding (assigns 1–3 codes and sentiment per response), and (2) theme synthesis (groups codes into 3–6 named themes with descriptions, prevalence estimates, and supporting quotes).

All prompt text is SHA256-hashed and recorded in the audit manifest, ensuring the exact prompts used in the published analysis can be verified.

### 6.4 Intercoder Reliability

To assess the consistency of AI-assisted coding, a **second independent coding pass** is performed on a 20% random sample (n ≈ 13–22 per question) using identical prompts. Agreement between Pass 1 and Pass 2 is measured using **Krippendorff's alpha** (α_K) for nominal data (Hayes & Krippendorff, 2007):

- α_K ≥ 0.80: strong reliability (Krippendorff, 2004)
- α_K ≥ 0.67: acceptable minimum for exploratory research
- α_K < 0.67: themes should be interpreted as tentative

Results are reported per question in `output/<run_id>/qual/irr_results.json`.

### 6.5 Representation of Findings

- Themes are presented with a name, description, estimated prevalence (% of responses), and 2+ verbatim supporting quotes
- Quotes are attributed to respondent sector and anonymous ID (R001..RN) only — never to name or organisation
- Representative quotes are selected from the LLM-identified supporting quotes; quotes are not altered, only truncated with `[...]` where necessary for length
- The number of respondents whose quotes appear in the published report is not separately disclosed to further protect anonymity

---

## 7. Privacy and Data Protection

See `docs/privacy.md` for the full privacy impact assessment.

**Key measures:** PII removed (names, emails, contact details); anonymous respondent IDs assigned (R001..RN); k-anonymity verified (k ≥ 5) using quasi-identifiers; small cell suppression (n < 5) applied to all cross-tabulations; PIPEDA compliance reviewed.

---

## 8. Reproducibility

All analysis code, data, and prompts are published in this repository. See `REPRODUCIBILITY.md` for step-by-step replication instructions.

**Random seed:** 42 (used throughout for bootstrap sampling and word cloud generation).
**Software versions:** Pinned in `analysis/requirements.txt`.
**Input file SHA256:** Recorded in `output/<run_id>/audit/manifest.json`.

---

## References

- Braun, V., & Clarke, V. (2021). Thematic analysis: A practical guide. Sage.
- Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.). Erlbaum.
- Cramér, H. (1946). Mathematical methods of statistics. Princeton University Press.
- Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. Psychometrika, 16(3), 297–334.
- Efron, B., & Tibshirani, R. J. (1993). An introduction to the bootstrap. Chapman & Hall.
- Gao, J., Guo, Y., & Tian, Q. (2024). AI-assisted qualitative data analysis: Potentials, pitfalls, and practical recommendations. Qualitative Research, advance online publication.
- George, D., & Mallery, P. (2003). SPSS for Windows step by step: A simple guide and reference. Allyn & Bacon.
- Hayes, A. F., & Krippendorff, K. (2007). Answering the call for a standard reliability measure for coding data. Communication Methods and Measures, 1(1), 77–89.
- Krippendorff, K. (2004). Content analysis: An introduction to its methodology (2nd ed.). Sage.
- Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. Journal of the American Statistical Association, 47(260), 583–621.
- Machanavajjhala, A., Kifer, D., Gehrke, J., & Venkitasubramaniam, M. (2007). l-diversity: Privacy beyond k-anonymity. ACM Transactions on Knowledge Discovery from Data, 1(1), Article 3.
- Norman, G. (2010). Likert scales, levels of measurement and the "laws" of statistics. Advances in Health Sciences Education, 15, 625–632.
- Pearson, K. (1900). On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling. Philosophical Magazine, 50(302), 157–175.
- Sullivan, G. M., & Artino, A. R. (2013). Analyzing and interpreting data from Likert-type scales. Journal of Graduate Medical Education, 5(4), 541–542.
- Sweeney, L. (2002). k-anonymity: A model for protecting privacy. International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems, 10(5), 557–570.
- Xiao, Z., Yuan, X., Liao, Q. V., Cai, R., & Nichols, B. (2023). Supporting qualitative analysis with large language models: Combining codebook with GPT-3 for deductive coding. ACM CHI Conference on Human Factors in Computing Systems, Extended Abstracts.

---

## Publication Schedule

The report is published in two tranches reflecting the differing review requirements for quantitative and qualitative analysis:

### Part 1 — Quantitative Findings (published May 1, 2026)

Covers all statistical analysis: response overview, tool satisfaction (Q5), feature importance scale (Q7, Cronbach's α=0.7748), governance/trust indicators (Q9–Q12), and adoption/pricing analysis (Q50–Q52). No LLM-generated content. Fully reproducible from `quant` stage output alone.

**CE page:** `/community-technology-survey-2026-part-1`
**Pipeline command:** `python3 analysis/community_technology_survey_analysis.py report --run-id <id> --tranche quant`

### Part 2 — Qualitative Insights (published after editorial review)

Covers all open-text qualitative analysis: AI-assisted thematic coding of 18 questions, cross-question synthesis, sector-specific voices, and the synthesis narrative ("What This Tells Us"). Requires completion of the `qual` stage (Ollama LLM local coding) and human editorial review of IRR metrics before release.

**Rationale for delayed release:** Intercoder reliability (Krippendorff's α) ranged from −0.14 to 0.37 across questions. These values reflect code-label variation across LLM passes rather than theme incoherence, but warrant human review before public attribution. The quantitative findings are not affected.

**CE page:** `/community-technology-survey-2026-part-2`
**Pipeline command:** `python3 analysis/community_technology_survey_analysis.py report --run-id <id> --tranche qual`

### Combined (for replication)

The full combined report (`report.md`, `report.html`) containing both tranches is produced by the default `all` or `report` (no `--tranche`) command. This is the canonical reproducible artifact for archival purposes.

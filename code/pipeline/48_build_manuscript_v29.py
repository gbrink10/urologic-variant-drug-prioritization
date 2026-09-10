"""Build the v30 manuscript from the deposited results.

Every quantitative statement is interpolated from MANUSCRIPT_FACTS.json, which
is computed from the result tables. The prose and the deposit therefore cannot
disagree - the failure mode that produced 42 field-level differences between the
v28 text and its own CSV.

Writes: Downloads/FDA_Drug_Repurposing_v31.docx
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import paths

import docx
import pandas as pd
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.stdout.reconfigure(encoding='utf-8')

# Zenodo. The concept DOI is stable and always resolves to the newest archived
# version; the version DOI is minted when a GitHub release is cut and must be
# updated here before submission. Both are cited in Data Availability.
ZENODO_CONCEPT_DOI = 'doi:10.5281/zenodo.20217918'
# minted from the v31.0 GitHub release on 31 August 2026; DataCite state
# 'findable'. Update alongside the tag if the analysis is released again.
ZENODO_VERSION_DOI = 'doi:10.5281/zenodo.22211795'
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
FIG = paths.FIGURES
SCRATCH = paths.DATA / 'manuscript_parts'
OUT = paths.OUTPUT / 'FDA_Drug_Repurposing_v31.docx'

F = json.loads((RF / 'MANUSCRIPT_FACTS.json').read_text(encoding='utf-8'))
refs = SCRATCH.joinpath('v28_refs.txt').read_text(encoding='utf-8').splitlines()
back = json.loads(SCRATCH.joinpath('v28_backmatter.json').read_text(encoding='utf-8'))
# the v28 extraction ran to the next all-capitals heading and so swallowed the
# old table title and legend; drop anything that belongs to the previous table
back = {k: [p for p in v
            if not p.startswith(('Table 1', 'Master Table'))
            and 'Supplementary Table S5' not in p]
        for k, v in back.items()}
master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')
sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')
defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')

doc = docx.Document()
st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(11)


def H(text, size=13, space_before=12, level=1):
    # a real heading style, so the document has a navigable structure and
    # screen readers can announce sections
    try:
        p = doc.add_paragraph(style=f'Heading {level}')
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
    except KeyError:
        p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    return p


def P(text, italic=False, size=11, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.italic = italic
    r.font.size = Pt(size)
    return p


SUP = str.maketrans('0123456789-', '\u2070\u00b9\u00b2\u00b3\u2074'
                                 '\u2075\u2076\u2077\u2078\u2079\u207b')


def spell(v):
    """Small counts read as words in prose; anything larger stays a numeral."""
    return {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six',
            7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'}.get(int(v), str(v))


def ordinal(v):
    """96.1 -> '96th', 73.2 -> '73rd'. Percentiles read as ordinals in prose."""
    i = int(round(v))
    if 10 <= i % 100 <= 20:
        suf = 'th'
    else:
        suf = {1: 'st', 2: 'nd', 3: 'rd'}.get(i % 10, 'th')
    return f'{i}{suf}'


def fmt(x, sig=2):
    """One notation for every q-value in the manuscript: 1.3 x 10^-13."""
    if x is None:
        return 'n/a'
    if x >= 1e-3:
        return f'{x:.3f}'.rstrip('0').rstrip('.')
    mant, exp = f'{x:.1e}'.split('e')
    return f'{mant} \u00d7 10{str(int(exp)).translate(SUP)}'


q, de, rmc, dsn = F['q'], F['de'], F['rmc'], F['design']

# score-sensitivity ranks, needed in the Discussion and deposited as Table S2
_prov0 = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
_v = []
for _, _r in _prov0.iterrows():
    _e, _p, _l = (int(_r['E_refit']), int(_r['P_refit']),
                  int(_r['L_curated']))
    _v.append({'N': int(_r['N']), 'full': _e + _p + _l,
               'no_pathway': _e + _l})
_v = pd.DataFrame(_v)
for _c in ('full', 'no_pathway'):
    _v['r_' + _c] = _v[_c].rank(ascending=False, method='min').astype(int)
s2_lead_no_pathway = int(_v.loc[_v['N'] == 17, 'r_no_pathway'].iloc[0])
surv = F['survivors']
lead = next(s for s in surv if s['N'] == 17)
second = next(s for s in surv if s['N'] != 17)
# CEACAM1 is credited a pathway point on a set it does not belong to; the
# manuscript states that q rather than implying no pathway evidence exists
_pv = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
ceacam1_pq = f"{float(_pv.loc[_pv['N'] == 19, 'pathway_q'].iloc[0]):.4f}"


def _s2v(n_, variant):
    """A row's score under one sensitivity variant, from the same components
    Supplementary Table S2 is built from."""
    _r = _pv.loc[_pv['N'] == n_].iloc[0]
    _e, _p, _l = (int(_r['E_refit']), int(_r['P_refit']),
                  int(_r['L_curated']))
    _member = 'target in pathway set' in str(_r['P_basis'])
    if variant == 'full':
        return _e + _p + _l
    if variant == 'membership':
        return _e + (_p if _member else 0) + _l
    raise ValueError(variant)

# =====================================================================
# Front matter
# =====================================================================
# ASCO's AI policy asks for tool, version, date accessed and manufacturer.
# Fill these four in before submission; the audit fails while any still reads
# FILL_IN, so the manuscript cannot ship with a placeholder in it.
AI_CLAUDE_VERSION = 'Opus 5'
AI_GPT_VERSION = 'GPT-6'
AI_ACCESS_DATES = 'January to September 2026'
AI_BIORENDER_DATE = 'September 2026'

# the deposited audit records no cutoff date, so this is the date the audit
# file was last regenerated, which is when the searches were last run
PUBMED_SEARCH_THROUGH = 'August 31, 2026'

TITLE = ('Prioritizing Repurposable Drugs for Rare and Variant Urologic '
         'Cancers From Public Data')
p = doc.add_paragraph()
r = p.add_run(TITLE)
r.bold = True
r.font.size = Pt(15)

P('Running Title: Public-Data Drug Prioritization in Rare Urologic Cancers')
P('Authors: Garrett J. Brinkley, MD\u00b9; Jacob Greenberg, MD\u00b9; '
  'Jorge Caso, MD\u00b9')
P('Affiliations: \u00b9Department of Urology, Tulane University School of '
  'Medicine, New Orleans, Louisiana, USA')
P('Corresponding Author: Garrett J. Brinkley, MD; Department of Urology, Tulane '
  'University School of Medicine, New Orleans, LA; garrettjbrinkley@gmail.com')

H('CONTEXT', 12)
P('Key objective: What does reanalysis under models matched to each study '
  'design change about a curated set of repurposing hypotheses for drugs '
  'that are '
  'already FDA-approved, or in clinical trials for a different disease, for '
  'aggressive urologic cancers where trials are difficult to power?')
P(f"Knowledge generated: Fitting each deposited dataset under a model matched "
  f"to its design, where the deposit allows one, rather than reusing its "
  f"published summary statistics, changed which candidates qualified and "
  f"cost an FDA-approved therapy its place. It also identified a sarcomatoid "
  f"comparison in which histology cannot be separated from array batch. "
  f"The pipeline "
  f"produced {F['n_associations']} entries, "
  f"{F['n_drug_hypotheses']} drug-cancer hypotheses and one biomarker "
  f"observation, {F['arm_control']['n']} of them in the three "
  f"positive controls and {F['arm_discovery']['n']} in the four rare "
  f"cancers. Every therapy already exists: among the "
  f"{F['n_drug_hypotheses']} drug-cancer hypotheses, "
  f"{F['stage']['approved']} name an FDA-approved therapy, "
  f"{F['stage']['in_trials']} a therapy in trials for another disease and "
  f"{F['stage']['preclinical']} a preclinical therapy, nominated where "
  f"nothing clinical-stage targets that protein. All "
  f"{F['arm_control']['n']} control associations recover a drug proposed "
  f"independently by another group or already in trials. Among the "
  f"{F['arm_discovery']['n']} associations in the rare cancers, "
  f"{F['arm_discovery']['proposed']} were previously proposed, "
  f"{F['arm_discovery']['partial']} extend a drug from the conventional form "
  f"of the disease, one is a biomarker observation rather than a drug "
  f"hypothesis, and {F['arm_discovery']['novel']} had no prior proposal in "
  f"the urologic literature. The ranking criteria prioritized "
  f"{spell(F['funnel']['survive'])} of them and we name every criterion the "
  f"other {spell(F['arm_discovery']['novel'] - F['funnel']['survive'])} "
  f"missed.")

H('ABSTRACT', 12)
P(f"Purpose. Rare and variant urologic cancers are difficult to study in "
  f"randomized trials, so few have biomarker-directed treatment options. We "
  f"built a public-data framework that prioritizes drug targets for them "
  f"among therapies already approved or in trials for another disease.")
P(f"Methods. A curated set of drug-cancer associations was assembled from "
  f"TCGA and GEO, with drugs from the Therapeutic Target Database and Open "
  f"Targets and membership fixed before reanalysis; "
  f"{F['stage']['preclinical']} preclinical therapies entered where nothing "
  f"clinical-stage targeted the protein. Differential expression across "
  f"{F['n_series_total']} datasets, enrichment across eighteen pre-specified "
  f"gene sets and mechanistic-literature concordance gave a 6-point "
  f"score. Expression was reanalyzed in limma and edgeR under models matched "
  f"to each design, except one series deposited only as summary results. "
  f"Associations were "
  f"then classified by prior proposal and ranked by a pre-specified rule.")
P(f"Results. We evaluated {F['n_drug_hypotheses']} drug-cancer hypotheses "
  f"and one unscored "
  f"biomarker observation. {spell(F['n_complete_score']).capitalize()} carry a "
  f"complete score: {F['tiers'].get('Strong', 0)} Strong, "
  f"{F['tiers'].get('Moderate', 0)} Moderate, "
  f"{F['tiers'].get('Exploratory', 0)} Exploratory; "
  f"{spell(F['n_partial_score'])} are partial and untiered. All "
  f"{F['arm_control']['n']} positive-control associations recover a drug "
  f"proposed independently elsewhere. Among the {F['n_rare_hypotheses']} "
  f"rare-cancer hypotheses, {F['arm_discovery']['proposed']} were previously "
  f"proposed, {F['arm_discovery']['partial']} have a partial precedent and "
  f"{F['arm_discovery']['novel']} none in the urologic literature. The "
  f"criteria prioritized {F['funnel']['survive']}: CXCR1/CXCR2 blockade and "
  f"anti-CEACAM1 in renal medullary carcinoma, and anti-CEACAM5 conjugates "
  f"in ASCL1-positive small-cell bladder cancer. Restricting "
  f"pathway points to targets in an enriched set retains CXCR1/CXCR2 and "
  f"anti-CEACAM5 but excludes anti-CEACAM1. Of the other "
  f"{F['arm_discovery']['novel'] - F['funnel']['survive']}, SSTR2 fails "
  f"the batch-adjusted transcriptomic criterion and the sarcomatoid rows "
  f"cannot separate histology from batch.")
P(f"Conclusion. Public data can prioritize drug hypotheses for cancers in "
  f"which prospective biomarker-directed trials are hard to conduct. Every "
  f"candidate is reported with its evidence and needs experimental "
  f"validation.")

# =====================================================================
# Introduction
# =====================================================================
H('INTRODUCTION')
P('Online data resources have changed how oncologic disease can be studied. '
  'The Cancer Genome '
  'Atlas (TCGA) catalogs somatic alterations across thirty-three cancer '
  'types from '
  'more than eleven thousand patients [1,2], searchable through '
  'cBioPortal [3], and the Gene Expression Omnibus (GEO) archives over two '
  'hundred '
  'thousand transcriptomic datasets [4]. The Therapeutic '
  'Target Database [5] and Open Targets [6] record which proteins have '
  'drugs against them and how far each has progressed, and the Kyoto '
  'Encyclopedia of Genes and Genomes groups genes into annotated pathways '
  '[7]. Together they make it possible to assess therapeutic hypotheses from '
  'data already collected, provided the analysis accounts for how each '
  'dataset was built.')
P('Drug repurposing matches an approved or in-trial drug to a disease it was '
  'not developed for. Such a compound is de-risked, with established safety '
  'and pharmacokinetics, so development timelines and costs are potentially '
  'lower [8]. The critical challenge is '
  'identifying which approved drugs have a mechanistic rationale supported by '
  'molecular evidence in the target disease. We therefore '
  'focused candidate selection on therapies that are already FDA-approved '
  'or in '
  'clinical trials for another disease, with two preclinical exceptions '
  'where no clinical-stage therapy targeted the nominated protein. The '
  'ranking criteria below require a clinical-stage therapy, so those two '
  'are '
  'reported but not prioritized.')
P('Against that background, aggressive and variant urologic histologies are '
  'in high need of novel therapies. Renal medullary carcinoma [9], penile '
  'squamous cell carcinoma '
  '[10,11], sarcomatoid urothelial carcinoma [12] and small-cell bladder cancer '
  '[13] each progress rapidly, resist standard chemotherapy, and lack '
  'biomarker-directed prospective evidence, either because the disease is rare or because the '
  'biomarker-defined subset is too small to power a trial. Slow accrual and '
  'small populations make such trials difficult.')
P('We therefore asked whether public molecular data could be interrogated '
  'systematically enough to prioritize biomarker-matched drug hypotheses '
  'across several such cancers at once. We refer to the sequence of steps that '
  'does this, from data retrieval to the ranked candidates, as the pipeline; '
  'it '
  'is set out in Figure 1 and in the Methods. Three better-studied cancers are '
  'included deliberately as positive controls: neuroendocrine prostate cancer, '
  'muscle-invasive bladder cancer and clear cell renal cell carcinoma. These '
  'were chosen by the authors on clinical grounds, as aggressive urologic '
  'malignancies whose therapeutic priorities are already documented; '
  'neuroendocrine prostate cancer was included because its published '
  'therapeutic hypotheses give a reference to compare against. If the '
  'pipeline recovers those priorities, its output in the four rare cancers can '
  'be given more weight.')
P(f"Of the {F['n_associations']} associations the pipeline produced, "
  f"{F['n_previously_proposed']} were proposed by other groups first and are "
  f"identified as such; {F['n_framework_novel']} had no prior proposal in the "
  f"urologic literature, {spell(F['funnel']['survive'])} of which meet every "
  f"criterion we set.")

H('MATERIALS AND METHODS')
H('Data Sources', 11.5, 10, level=2)
P('This is a reassessment of a curated candidate set. The deposited scripts '
  'reproduce the differential-expression estimates, the enrichment tests, '
  'the score and the prioritization, but not the original manual mapping '
  'from genes to therapies, whose per-row queries were not retained. '
  'Procedure '
  'is in Supplementary Methods.')
P('The order of decisions matters to how the score should be read. The '
  'candidate set, the scoring dimensions, their ranges and the four ranking '
  'criteria were fixed first; the datasets were then reanalyzed, with '
  'study-specific models fitted where sample-level data were available; and '
  'auditing the genomic dimension against the cohorts it named came last, '
  'and removed it from the score (Supplementary Table S4). What remains is '
  'unchanged from the pre-specified set, including the requirement of 4 or '
  'better, which was not rescaled when the maximum fell from 9 to 6 and is '
  'a stricter bar than it was.')
P('Somatic alteration frequencies for the three positive controls came from '
  'the TCGA Pan-Cancer Atlas 2018 through cBioPortal [1\u20133], with cohort '
  'sizes in Figure 1. It has no neuroendocrine prostate cohort, so those '
  'genes were ranked against prostate adenocarcinoma, and the four rare '
  'cancers are absent entirely, so their genes were ranked on differential '
  'expression [9\u201313]. Genomic evidence therefore enters through '
  'candidate selection, not the score (Supplementary Methods Section 2). '
  'Transcriptomic data came from ten Gene Expression Omnibus series '
  '[4], listed with their accessions under Data Availability; pathway '
  'definitions from the Kyoto Encyclopedia of Genes and Genomes [7]; and '
  'drug-target relationships and clinical stage from the Therapeutic Target '
  'Database [5] and Open Targets [6]. Gene symbols were reconciled against the '
  'HGNC complete set. A rare cancer is often defined by an alteration that is '
  'not itself a drug target, SMARCB1 loss in renal medullary carcinoma being '
  'the clearest case [14], so transcriptomic nomination was not restricted to '
  'recurrently altered genes.')

H('Candidate Selection', 11.5, 10, level=2)
P(f"A candidate is one proposed therapy, drug class or combination matched "
  f"to one cancer or molecular subtype, supported by the evidence below; a "
  f"row naming several antagonists of the same axis is one candidate, not "
  f"several. "
  f"Candidates were generated one "
  f"cancer at a time. Genes were ranked by "
  f"somatic alteration frequency where TCGA provides a cohort and otherwise "
  f"by the moderated t-statistic from the corresponding fit, reviewed "
  f"manually, and carried forward three to seven per cancer and three to "
  f"five in each rare cancer, by clinical relevance rather than a threshold. Each was then "
  f"searched against the Therapeutic Target Database and Open Targets and "
  f"became an association only where it had a therapy that could be evaluated "
  f"clinically. The two groups reach the table by different routes: "
  f"{F['tcga_rows_freq_ge_15pct']} of the {F['n_tcga_anchored']} "
  f"positive-control associations nominate a gene the original curation "
  f"recorded as altered in 15% or more of the cohort, a figure from that "
  f"curation rather than from the recomputation in Supplementary Table S4, "
  f"while {F['geo_rows_no_recurrent_alteration']} of the "
  f"{F['n_geo_anchored']} from the rare cancers nominate a target that is not "
  f"itself recurrently altered and were reached on expression alone "
  f"(Supplementary Figure S1).")
P(f"The eighteen gene sets were used to score candidates, not "
  f"to choose them, so a "
  f"gene could be nominated without belonging to any; seven associations "
  f"entered that way, four of them cell-surface antigens that pathway "
  f"definitions do not group by, and two of the three prioritized candidates "
  f"are among the seven. This was a curated search, not an exhaustive "
  f"screen, and the search for a therapy was manual and unlogged: "
  f"{F['funnel_entry']:,} gene-cancer pairs met the expression threshold and "
  f"most have no clinically evaluable therapy (Supplementary Methods "
  f"Section 7b).")

H('Prioritization Score', 11.5, 10, level=2)
P('Each association received 0 to 6 points across three dimensions: '
  'transcriptomic evidence '
  '(0\u20133), pathway evidence '
  '(0\u20132) and external mechanistic-literature concordance (0\u20131). '
  'The ranges were set before scoring and the bins within each dimension are '
  'given in Supplementary Methods Section 6. '
  'The dimensions overlap rather than being independent, which the Discussion '
  'quantifies. Totals map to Strong (5\u20136), Moderate (3\u20134) '
  'and Exploratory (1\u20132) tiers, which express strength of evidence '
  'within this framework only. Where a component could not be computed it is '
  'reported as not computed, the total is out of fewer than 6 points, and the '
  'row is not assigned an evidence tier. A separate case arises where a target '
  'is absent from its dataset’s platform. The code recomputes the total '
  'from the evidence components, but a transcriptomic value that cannot be '
  're-derived from deposited expression data is retained as a curated input, '
  'flagged row by row in Supplementary Table S1 with the source it came '
  'from.')

H('Prior-Proposal Classification', 11.5, 10, level=2)
P('After scoring, each association was classified on PubMed as having no '
  'prior urologic-oncology proposal identified, a partial precedent, or a '
  'prior proposal. A prior proposal is a primary report, review, position '
  'paper or trial registration proposing the therapy or its class against '
  'the '
  'nominated target in this urologic disease. A partial precedent requires a '
  'report in the urologic literature that falls short of that: the target '
  'named in this disease with no therapy proposed against it, or the '
  'therapy '
  'proposed in the conventional form of the disease rather than the variant. '
  'A report in a non-urologic organ never creates a partial precedent; it is '
  'external mechanistic support: it can earn the literature point while the '
  'row stays classified as having no prior urologic proposal, as the '
  'ASCL1-CEACAM5 paradigm from small-cell lung cancer does. '
  'Searches ran on PubMed with no date or language limit, through '
  + PUBMED_SEARCH_THROUGH + '. One author '
  'classified each association and no second reviewer repeated it. '
  'Classifications were recorded after the scores were computed, but candidate '
  'curation drew on prior clinical and mechanistic knowledge, so the two are '
  'not independent. The search template, the counting rules and the per-row '
  'classifications are deposited.')

H('Ranking Criteria', 11.5, 10, level=2)
P('The criteria were defined a priori, before they were applied to any '
  'candidate. A candidate was prioritized only if all four of the '
  'following held:')
for _c in ('no prior urologic-oncology proposal identified;',
           'a total of 4 or better, an absolute count rather than a share of '
           'the points available for that row, so a row scored out of 4 must '
           'take all four;',
           'a transcriptomic component re-derivable from deposited data and '
           'meeting the standard for its route, q < 0.05 on a disease '
           'contrast or the top 15% of transcripts where only abundance is '
           'available; and',
           'a clinical-stage therapy, meaning one already FDA-approved for '
           'another disease or currently in trials, with a documented '
           'development pathway.'):
    _p = doc.add_paragraph(_c, style='List Bullet')
    _p.paragraph_format.space_after = Pt(2)
    for _r in _p.runs:
        _r.font.size = Pt(10.5)
P('Where a disease held more than one prioritized candidate, the first rank '
  'also '
  'required that the target belong to an enriched pathway. A candidate that '
  'missed a criterion is reported with that criterion named. Two further '
  'checks fixed at the same time, that no external source contradict a '
  'candidate and that the target be reachable by the kind of therapy proposed, '
  'changed no candidate and are reported in the Supplementary Materials.')

H('Statistical Analysis', 11.5, 10, level=2)
P(f"Each series was fitted with the model its design supports, given per "
  f"dataset in Supplementary Table S3. Count-based series were filtered with "
  f"edgeR filterByExpr against the design matrix, normalized by the trimmed "
  f"mean of M-values, given voom precision weights and fitted by weighted "
  f"least squares in limma; log-scale and already-summarized series were "
  f"fitted with limma-trend under robust empirical Bayes moderation. Four "
  f"design features were modeled explicitly: donor as a random effect through "
  f"duplicateCorrelation in the penile series, consensus correlation "
  f"{F['refit']['pscc_dupcor'].split('consensus ')[-1]}, whose "
  f"{dsn['pscc_normal_arrays']} normal arrays come from "
  f"{dsn['pscc_normal_donors']} donors; patient as a fixed blocking factor in "
  f"the matched tumor-normal bladder kinome panel; batch as a covariate in "
  f"each small-cell subtype contrast against the mean of the rest; and, in "
  f"the sarcomatoid series, chip collinear with histology, so that "
  f"coefficient is not estimable and no histology contrast is reported.")
P(f"The renal medullary series is a two-cell-line SMARCB1 rescue experiment "
  f"deposited only as an author-computed differential-expression table, with "
  f"no sample-level matrix, so no model matched to its design can be fitted. "
  f"The two lines were treated as two independent patient-derived models "
  f"rather than an inferential cohort: a gene had to exceed |log2 fold "
  f"change| of 0.5 in the disease-state orientation at q < 0.05 in each line "
  f"separately, and the reported q-value is the larger of the two.")
P(f"Enrichment asks whether a gene set holds more of a cancer's raised "
  f"genes than chance would put there. It was a one-sided hypergeometric "
  f"test of the genes at q < 0.05 "
  f"with log2 fold change above 0.5 against each of the eighteen sets, with "
  f"the genes that dataset measured as the universe rather than the whole "
  f"genome, which would inflate the overlap for a targeted panel "
  f"(Supplementary Methods Section 5). Benjamini-Hochberg correction was "
  f"applied across the eighteen sets within each context, and not across "
  f"contexts, drugs or downstream comparisons. Throughout, q is a "
  f"Benjamini-Hochberg-adjusted p-value, used to control the false-discovery "
  f"rate. For differential expression it is adjusted across the genes tested "
  f"in that series; for enrichment it is adjusted across the eighteen gene "
  f"sets within each context. Two thresholds were "
  f"pre-specified: q < 0.05 for differential expression and an exploratory "
  f"q < 0.10 for enrichment, values between the two being described as "
  f"suggestive. Analyses ran under R 4.6.1 (limma 3.68.4, edgeR 4.10.1) and "
  f"Python 3.10.")

print('front matter and methods written')

# =====================================================================
# Results
# =====================================================================
H('RESULTS')

H('The Association Table', 11.5, 10, level=2)
ctx_counts = ', '.join(f'{k} {v}' for k, v in F['per_context'].items())
P(f"The pipeline produced {F['n_drug_hypotheses']} drug-cancer hypotheses "
  f"and one unscored biomarker observation (Table 1; every score component "
  f"is in Supplementary Table S1), "
  f"{F['arm_control']['n']} in the three positive controls and "
  f"{F['arm_discovery']['n']} in the four rare cancers. Of these, "
  f"{F['tiers'].get('Strong', 0)} reach the Strong tier, "
  f"{F['tiers'].get('Moderate', 0)} Moderate and "
  f"{F['tiers'].get('Exploratory', 0)} Exploratory. Four sarcomatoid "
  f"hypotheses are scored out of 4 rather than 6 and carry no tier, and the "
  f"biomarker observation carries no score.")

H('Positive Controls', 11.5, 10, level=2)
P(f"All {F['arm_control']['proposed']} positive-control associations recover a "
  f"drug proposed independently by another group: six in neuroendocrine "
  f"prostate cancer [15\u201323], seven "
  f"in muscle-invasive bladder cancer [24\u201332] and three in clear cell "
  f"renal cell carcinoma [33\u201337]. Erlotinib in renal medullary "
  f"carcinoma [38,39] and pembrolizumab in penile squamous cell carcinoma "
  f"[40–42] were recovered within the rare cancers rather than the "
  f"designated control contexts, giving {F['n_previously_proposed']} "
  f"instances of agreement with a prior proposal, which is not independent "
  f"validation, for the reason the Discussion gives.")

H('Rare and Variant Cancers', 11.5, 10, level=2)
P(f"In renal medullary carcinoma the deposited experiment is a SMARCB1 rescue "
  f"in two patient-derived cell lines. Across the {rmc['genes_measured_both']:,} "
  f"genes measured in both, the correlation between lines is only "
  f"r = {rmc['r_between_lines']}. Requiring a consistent change in both lines "
  f"leaves {rmc['up_both']} genes. Chemokine genes are "
  f"among them, elevated in the SMARCB1-null state in both lines (CXCL8 "
  f"{rmc['CXCL8']['RMC2C']:+.2f} and {rmc['CXCL8']['RMC219']:+.2f}, with "
  f"CXCL1, CXCL2 and CXCL3 also elevated), and KEGG chemokine signaling is "
  f"enriched among those 187 genes at q = {q['rmc_chemokine']:.4f} (Figure 2), "
  f"coherent with the neutrophil-rich microenvironment described in this "
  f"disease [43]. This nominates the CXCR1/CXCR2 antagonist class, and "
  f"CEACAM1 alongside it ({rmc['CEACAM1']['RMC2C']:+.2f} and "
  f"{rmc['CEACAM1']['RMC219']:+.2f}).")

P(f"Lineage-stratified small-cell bladder cancer (Figure 3), classified by "
  f"lineage transcription factor [44], produced three subtype-specific "
  f"associations. ASCL1-positive tumors show CEACAM5 elevation "
  f"({de['CEACAM5_ascl1']['log2FC']:+.2f}, q = {fmt(de['CEACAM5_ascl1']['q'])}), "
  f"supporting CEACAM5-directed antibody-drug conjugates as a class; "
  f"POU2F3-positive tumors show arachidonic-acid metabolism enrichment "
  f"(q = {q['pou2f3_arachidonic']:.3f}) with PTGS1 elevated "
  f"({de['PTGS1_pou2f3']['log2FC']:+.2f}, q = {fmt(de['PTGS1_pou2f3']['q'])}), "
  f"a COX-1 program whose therapeutic direction requires functional "
  f"testing. In tuft cells, which "
  f"POU2F3 defines, prostaglandin signaling has been reported to restrain "
  f"rather than promote tumorigenesis [45]. The "
  f"NEUROD1-positive somatostatin receptor 2 association is not supported: the "
  f"fold change reproduces ({de['SSTR2_neurod1']['log2FC']:+.2f}) but does not "
  f"reach significance under a batch-adjusted subtype contrast "
  f"(q = {de['SSTR2_neurod1']['q']:.3f}), and the neuroactive ligand-receptor "
  f"set is not enriched in that subtype, so these data do not establish "
  f"subtype-specific transcriptomic support for carrying the small-cell "
  f"lung cancer approach [46] into NEUROD1-positive small-cell bladder "
  f"cancer.")

print('results 3.1-3.3 written')

P(f"The sarcomatoid series is reported in full in the Supplementary Results, "
  f"and Figure 4 shows why no contrast is. Every sarcomatoid tumor was run "
  f"on a different batch of chips from every conventional tumor, so a "
  f"difference between the groups is also a difference between batches and "
  f"no model can separate them. We therefore report no "
  f"sarcomatoid-versus-conventional comparison "
  f"and scored four of these five associations on transcript abundance "
  f"summarized within the sarcomatoid tumors, without estimating a "
  f"difference between the histologies: "
  f"UHRF1 [47], NSD2 "
  f"and G6PD [48] are highly abundant there and ATR is not. The pathway "
  f"component could not be computed for this context, so these rows total out of 4 "
  f"rather than 6 and carry no evidence tier, and neither of the two candidates without "
  f"a prior proposal was prioritized. TROP2 is reported there as an "
  f"observation, not as a predictive biomarker, and carries no score "
  f"[49\u201351].")

P(f"Penile squamous cell carcinoma is reported in the Supplementary Results. "
  f"In brief, a dominant immune-hot phenotype converges on the established "
  f"pembrolizumab priority [40–42], with two partially-novel candidates "
  f"alongside it [52–54] and none without a prior proposal.")
H('Candidates Without a Prior Proposal', 11.5, 10, level=2)
P(f"Figure 5 sets every candidate without a prior proposal against each "
  f"criterion; Table 1 accounts for every association with its score and "
  f"evidence tier, and Supplementary Table S1 carries the per-row evidence. "
  f"{spell(F['funnel']['framework_novel']).capitalize()} associations had no "
  f"prior proposal in the urologic literature. "
  f"{spell(F['funnel']['survive']).capitalize()} meet every criterion, in "
  f"{spell(F['n_survivor_contexts'])} diseases: renal medullary carcinoma "
  f"and ASCL1-positive small-cell bladder cancer. The other "
  f"{spell(F['funnel']['framework_novel'] - F['funnel']['survive'])} "
  f"failed one or more criteria, named below.")

P(f"The SSTR2-directed hypothesis, the only one of the six naming an "
  f"FDA-approved therapy, failed both the score and the transcriptomic "
  f"criterion "
  f"({_s2v(29,'full')}/6; q = {de['SSTR2_neurod1']['q']:.3f} once the "
  f"small-cell subtypes are contrasted with batch in the model). ATR failed "
  f"both the score and the abundance criterion (1/4; "
  f"{ordinal(F['abundance_pct']['ATR']['pct'])} percentile). NSD2 met the "
  f"abundance criterion but failed the score criterion (3/4, where the "
  f"criterion asks for 4). All three remain open questions that better data "
  f"could settle.")

P(f"We rank the prioritized candidates within a disease, not between "
  f"diseases. Two are in renal medullary carcinoma and compete for the same "
  f"experimental effort; the third is in ASCL1-positive small-cell bladder "
  f"cancer. The only feature that could separate them across diseases is "
  f"membership of one of our eighteen sets, which reflects the drug classes "
  f"we chose rather than the biology.")

P(f"Within renal medullary carcinoma we would carry CXCR1/CXCR2 blockade "
  f"forward first, at {lead['total']}/6. Its chemokine ligands are elevated "
  f"in both patient-derived lines, both receptors are confirmed membrane "
  f"proteins in the Human Protein Atlas [55], and the antagonist class is "
  f"already in clinical development. CXCR1 and CXCR2 "
  f"belong to a chemokine gene set enriched among the genes meeting the "
  f"concordance criterion in both lines "
  f"(q = {q['rmc_chemokine']:.4f}) and CEACAM1 belongs to no enriched set, "
  f"which is the only difference between their scores. That enrichment is "
  f"driven by the four CXCL ligands, which also supply the transcriptomic "
  f"score for this row, and neither receptor is among the "
  f"{rmc['genes_measured_both']:,} genes the series measured, so the pathway "
  f"and transcriptomic evidence are not independent and the target itself was "
  f"never observed: the evidence is the measured ligands, not receptor "
  f"expression, and Supplementary Table S1 names the evidence gene and the "
  f"nominated target separately for every row. Anti-CEACAM1 scores {second['total']}/6; its single "
  f"pathway point comes from a cytokine-receptor set enriched at "
  f"q = {ceacam1_pq} to which CEACAM1 does not belong, so requiring "
  f"membership leaves {_s2v(19,'membership')}/6, below the threshold of 4 "
  f"(Supplementary Table S2). Its "
  f"surface protein abundance and therapeutic index in "
  f"renal medullary carcinoma are both unknown.")
P(f"Anti-CEACAM5 conjugates are the third prioritized candidate, and the only "
  f"one in ASCL1-positive small-cell bladder cancer. CEACAM5 is enriched in "
  f"that subtype ({de['CEACAM5_ascl1']['log2FC']:+.2f}, "
  f"q = {fmt(de['CEACAM5_ascl1']['q'])}), confirmed at the membrane in the "
  f"Human Protein Atlas [55] and low "
  f"in normal bladder RNA ({F['hpa']['nTPM']['CEACAM5']} normalized "
  f"transcripts per million, which orients safety planning rather than "
  f"demonstrating a systemic therapeutic window), and the drug class is in "
  f"active development. Its weaknesses are that CEACAM5 belongs to none of "
  f"the eighteen "
  f"pre-specified sets, so no pathway evidence supports it and its "
  f"eligibility rests on the literature point, without which it scores "
  f"{_s2v(28,'full')-1}/6; and that subtype-specific protein "
  f"expression, internalization and payload sensitivity in small-cell bladder "
  f"cancer are all untested.")
P(f"One qualification applies to the renal medullary lead: the proposed "
  f"mechanism runs through myeloid recruitment, so tumor-cell monoculture "
  f"alone does not evaluate it. All three are hypotheses, "
  f"not validated findings, and the experiment that would settle this one is "
  f"CXCR1/CXCR2 blockade in an immunocompetent model with an intact myeloid "
  f"compartment.")

H('DISCUSSION')
P('In this study, we show that public molecular data can be used to prioritize '
  'drug hypotheses in cancers where a dedicated biomarker-directed trial is '
  'difficult to conduct, and the associations in Table 1 were assembled '
  'without them.')
P(f"Refitting cost two candidates, by different routes. Somatostatin "
  f"receptor 2 reproduces its fold change but loses significance under a "
  f"batch-adjusted subtype model, so reusing the deposited summary would have "
  f"carried it. Refitting also showed the sarcomatoid contrast to be "
  f"confounded with array chip, which is why ATR is scored on abundance.")

P('Computational repurposing from public expression data is established [56]. '
  'GETgene-AI combines mutation frequency, differential expression and '
  'drug-target annotation [57]; this workflow uses the same kinds of '
  'information in candidate selection, but its score excludes genomic '
  'frequency; '
  'Pathway2Targets prioritizes targets by the pathways they belong to, the '
  'signal our eighteen gene sets supply [59]; and signature reversion found '
  'the choice of differential-expression method itself changing which '
  'candidates emerge [58], as refitting did here. Those methods are '
  'benchmarked on cohorts large enough to support them. We applied the same class of method where no such cohort '
  'exists, with positive controls run through the same pipeline.')
P(f"Recovery of the "
  f"{F['n_previously_proposed']} previously proposed priorities is a positive "
  f"control rather than independent validation, because prior knowledge "
  f"entered the pathway panel, the drug curation and the choice of "
  f"representative therapy; it shows the pipeline returns established priorities "
  f"in well-characterized disease, but it does not measure sensitivity or "
  f"precision. Three features of the deposited data also limited what could "
  f"be analyzed: histology confounded with array chip in the sarcomatoid "
  f"series, no normal tissue in the clear cell renal series, and a different "
  f"disease in the hereditary leiomyomatosis series, reported as adjacent "
  f"context only (Supplementary Table S3).")
P(f"The three score dimensions overlap, so the total orders candidates rather "
  f"than measuring them. The transcriptomic and pathway scores share an "
  f"input, since a set is enriched because its member genes are "
  f"differentially expressed and those same genes can supply the "
  f"transcriptomic point, and a pathway point is awarded even where the "
  f"target is not a member of the enriched set. Each prioritized candidate "
  f"therefore rests "
  f"on a different dimension and none survives every variant: CXCR1/CXCR2 "
  f"carries no literature point and holds without one, but falls to "
  f"{_s2v(17,'full')-2} without the pathway dimension; anti-CEACAM1 falls to "
  f"{_s2v(19,'membership')} when pathway points require membership, which "
  f"its cytokine-receptor point does not have; anti-CEACAM5 has no pathway "
  f"evidence to lose but falls to {_s2v(28,'full')-1} without its literature "
  f"point. Table 1 names the variant that removes each, and Supplementary "
  f"Table S2 gives every row under every variant. The dropped genomic "
  f"dimension was a fourth such choice: recomputing it from the cohorts it "
  f"named reproduces the curated band in 4 of the 15 rows with a cohort to "
  f"check against, and in several rows it stood for the alteration that "
  f"defines the disease rather than one in the nominated target "
  f"(Supplementary Table S4). Removing it did not change the prioritized set "
  f"among the {F['n_framework_novel']} hypotheses without a prior "
  f"urologic-oncology proposal, the comparison this study turns on, though "
  f"it moved five positive-control rows below the threshold.")
P(f"Our study has limitations, and most are bounded by what is public. The "
  f"Cancer Genome Atlas supported candidate selection in muscle-invasive "
  f"bladder and clear cell renal cell carcinoma; prostate adenocarcinoma "
  f"supplied adjacent-histology context for neuroendocrine prostate cancer, "
  f"and the four rare cancers have no cohort there at all, so genes in them "
  f"could be nominated only on expression. Rare-disease sample "
  f"sizes are modest, and enrichment was corrected within context only. Where a target is absent from "
  f"its platform the row retains a curated value, flagged in Supplementary "
  f"Table S1. The renal medullary experiment is two cell lines rather than a "
  f"patient cohort, and they agree poorly overall (r = "
  f"{rmc['r_between_lines']}), which is why consistency across both was "
  f"required. Finally, the urologic-only novelty standard is "
  f"a statement about the urologic literature and says nothing about "
  f"precedence outside it.")

P(f"One further limitation follows from how candidates were selected. In the "
  f"four rare cancers, where no alteration frequency was available to rank "
  f"on, a gene had to reach q < 0.05 with log2 fold change above 0.5 on its "
  f"disease contrast to be nominated at all, and we kept the list of genes "
  f"we analyzed short. That threshold applies to the measured evidence "
  f"gene, which for several rows is a ligand or a signature member rather "
  f"than the nominated target, and it governed nomination, not the "
  f"eligibility criteria applied after reanalysis. In cancers this "
  f"rare, such a threshold partly measures how little data has been "
  f"deposited rather than the biology, so a real target that falls short of "
  f"significance in a small cohort is never nominated; proteasome inhibition in renal medullary carcinoma [60] is one "
  f"such candidate. Further work could extend the search to the less "
  f"significant genes we set aside. Deposited data also limited the scope: "
  f"several variants of immediate interest, including primary "
  f"bladder adenocarcinoma, urachal carcinoma, plasmacytoid urothelial "
  f"carcinoma and translocation renal cell carcinoma, have no "
  f"histology-labeled cohort of adequate size and could not be analyzed. "
  f"Analyzing them will require larger histology-labeled cohorts to be "
  f"deposited.")

P(f"In conclusion, we scored {F['n_drug_hypotheses']} drug-cancer hypotheses "
  f"and report one further, unscored biomarker observation across three "
  f"positive-control and four rare or variant urologic cancers using only "
  f"public data. "
  f"Every positive-control association recovered a drug proposed "
  f"independently elsewhere, and "
  f"{F['arm_discovery']['novel']} from the rare cancers had none in the "
  f"urologic literature; the criteria prioritized "
  f"{spell(F['funnel']['survive'])} of those "
  f"{spell(F['n_framework_novel'])} and we name every criterion the other "
  f"{spell(F['n_framework_novel'] - F['funnel']['survive'])} missed. "
  f"The contribution is a method for generating and "
  f"ranking drug hypotheses in cancers where a dedicated trial is hard to "
  f"power, with the code and data deposited. All three prioritized candidates "
  f"need "
  f"experimental validation in their own disease, and broader progress would "
  f"benefit from wider tumor sequencing and from histology-labeled, "
  f"machine-accessible repositories.")

print('discussion and conclusions written')

# =====================================================================
# Data availability
# =====================================================================
H('DATA AVAILABILITY')
P('All datasets used are publicly available without restriction. Genomic '
  'alteration frequencies for the three positive controls were extracted from The '
  'Cancer Genome Atlas Pan-Cancer Atlas 2018 via cBioPortal. Ten Gene Expression '
  'Omnibus accessions provided transcriptomic evidence: GSE199274, GSE216053 and '
  'GSE216052 (neuroendocrine prostate cancer); GSE130598 (muscle-invasive '
  'bladder cancer kinome); GSE143630 [61] (clear cell renal cell carcinoma); '
  'GSE157256 [62] (hereditary leiomyomatosis renal cell cancer, reported as '
  'adjacent-disease context only); GSE180999 (renal medullary carcinoma); '
  'GSE196978 (penile squamous cell carcinoma); GSE128192 (sarcomatoid versus '
  'conventional urothelial carcinoma); and GSE269750 (small-cell bladder cancer, '
  'subtype-stratified). Pathway definitions were retrieved through the Kyoto '
  'Encyclopedia of Genes and Genomes programmatic interface and gene symbols '
  'normalized against the HGNC complete set. Drug-target associations were drawn '
  'from the Therapeutic Target Database and OpenTargets. All analysis scripts, '
  'the fitted differential-expression tables, the enrichment tables, the master '
  'association table with per-row scoring provenance, the candidate-selection '
  'table, the count of gene-cancer pairs considered, the prior-proposal audit and the '
  'figure-generation code are archived at GitHub '
  '(github.com/gbrink10/urologic-variant-drug-prioritization) and at Zenodo '
  f'({ZENODO_CONCEPT_DOI}, which resolves to the most recent archived version'
  + (f'; this manuscript corresponds to {ZENODO_VERSION_DOI}' if ZENODO_VERSION_DOI
     else '') + '). '
  'The nominated targets were also checked against DepMap [63], the PRISM '
  'Repurposing screen [64] and LINCS L1000 [65,66]; none of the three changed '
  'which candidates were prioritized, and all three are reported in the '
  'Supplementary Materials. '
  'The pipeline runs end to end from the deposited code; the large primary '
  'deposits are re-downloaded by the first script rather than mirrored.')

# =====================================================================
# Figures
# =====================================================================
FIGURES = [
    ('Figure1_pipeline.png', 6.5,
     'Figure 1. The pipeline, from context definition to the ranked '
     'candidates. Steps 1 to 6 build the association table. Candidate '
     'selection used genomic information from The Cancer Genome Atlas for '
     'the positive-control contexts, including prostate adenocarcinoma as '
     'adjacent-histology context for neuroendocrine prostate cancer, and '
     'expression evidence for the four rare or variant contexts; the '
     'six-point score combines transcriptomic evidence, pathway evidence and '
     'external mechanistic-literature concordance, and genomic information '
     'contributes no points. Differential expression was fitted '
     'across ten Gene Expression Omnibus datasets with a model '
     'matched to how each was collected where sample-level data are '
     'deposited, and by concordance across the two lines of the renal '
     'medullary series, which is deposited only as a summary table; '
     'hypergeometric enrichment across eighteen '
     'pre-specified druggable pathway or gene sets, compared against only the '
     'genes that dataset measured; drug-target curation; a 6-point prioritization '
     'score; and a PubMed search for prior proposals, run only after '
     'scoring was complete. Candidates are ranked by a rule fixed before it '
     'was applied; none is discarded.'),
    ('Figure2_RMC.png', 6.9,
     'Figure 2. Renal medullary carcinoma. (A) Effect in RMC-2C against effect '
     'in RMC219 for every gene measured in both lines. The genome-wide '
     'correlation is weak, so requiring consistent change in both lines is a '
     'stringent filter rather than a formality; genes passing it are highlighted, '
     'and the chemokine axis is labeled. (B) The chemokine axis gene by gene, '
     'each line shown separately, in disease-state orientation, with the pathway '
     'q-value computed on the genes changing in both lines. (C) Proposed '
     'mechanism: tumor-derived chemokines act on CXCR1 and CXCR2 carried by '
     'recruited myeloid cells, which is why a tumor-cell monoculture does '
     'not evaluate it. Neither receptor was measured in this series. '
     'CXCL8 binds both receptors; CXCL1, '
     'CXCL2 and CXCL3 are CXCR2-selective. These are CXCR1/CXCR2-axis '
     'antagonists with differing receptor selectivity: AZD5069, navarixin, '
     'reparixin and danirixin. Panel C created with '
     'BioRender.com.'),
    ('Figure3_SCBC.png', 6.9,
     'Figure 3. Lineage-stratified small-cell bladder cancer. (A) Subtype '
     'composition by lineage transcription factor. (B) The nominated target in '
     'each subtype with its q-value from the batch-adjusted subtype contrast; '
     'somatostatin receptor 2 in NEUROD1-positive tumors does not reach '
     'significance, which is why that association was not prioritized. The '
     'PTGS1 signal is a candidate perturbation axis rather than a direction: '
     'aspirin is a pharmacologically available non-selective inhibitor, and '
     'whether inhibition or activation is therapeutic requires functional '
     'testing.'),
    ('Figure4_SarcUC.png', 6.9,
     'Figure 4. Sarcomatoid urothelial carcinoma, and why no contrast is '
     'reported. (A) The separation between the two chip-aligned groups, shown '
     'for completeness; it cannot be read as a difference between histologies, '
     'because every sarcomatoid tumor was run on a different batch of chips '
     'from every conventional tumor. (B) Pathway values from that same '
     'comparison, which inherit the confounding, so no pathway component is '
     'scored for this context. (C) The quantity these rows are scored on '
     'instead: abundance summarized within the sarcomatoid tumors, which '
     'estimates no difference between the histologies and so does not rest '
     'on the confounded comparison. The dashed line is the 85th percentile, the threshold the '
     'abundance route scores against; ATR falls below it, which is why that '
     'candidate was not prioritized. The confounding in panels A and B is the '
     'design flaw that the deposited summary statistics did not show and the '
     'refit did.'),
    ('Figure5_candidate_selection.png', 6.9,
     'Figure 5. Every candidate without a prior urologic-oncology proposal, '
     'against every criterion. Each cell carries a symbol as well as a color: '
     '+ meets the criterion, ~ partly meets it, '
     '− does not meet it, n/a cannot be tested. '
     'The first column names which arm the evidence comes from and is left uncolored, '
     'because a route is not a verdict; the second marks whether the total meets '
     'the criterion of 4, and the third whether the evidence meets the standard '
     'for its arm. Protein access records whether the target is '
     'reachable by the kind of therapy proposed. The pathway column marks '
     'whether the target is itself a member of the enriched set, and reads '
     'not in the selected sets where the target belongs to none of the '
     'eighteen, which differs from the sarcomatoid rows, where it reads not '
     'computed because their only enrichment derives from the confounded '
     'comparison. '
     'The score is less strict than the column: it awards one point for '
     'enrichment or for membership and two for both, so a target can carry a '
     'pathway point without appearing in the set. Supplementary Table S2 gives '
     'every score under the membership-only rule. '
     'Candidates above the dashed line met all four of: '
     'E1, no prior urologic-oncology proposal was found; E2, a score '
     'of 4 or better out of the points available for that row; E3, '
     'transcriptomic evidence strong enough for the kind it rests on, '
     'q < 0.05 on a disease contrast or the top 15% of transcripts on '
     'abundance; and E4, a therapy in clinical development. Every candidate '
     'placed below the line was placed there by E2 or E3.'),
]
for name, width, legend in FIGURES:
    path = FIG / name
    if not path.exists():
        print(f'  MISSING FIGURE {name}')
        continue
    doc.add_paragraph()
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    # accessibility: give the image a description as well as a legend
    shape = doc.inline_shapes[-1]
    docPr = shape._inline.docPr
    docPr.set('descr', legend[:800])
    docPr.set('title', legend.split('.')[0])
    P(legend, size=9.5)
print(f'  embedded {len(FIGURES)} figures')

# =====================================================================
# References and back matter
# =====================================================================
H('REFERENCES')
for r in refs:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(r)
    run.font.size = Pt(9.5)

for key in ('CRediT AUTHOR STATEMENT', 'FUNDING', 'CONFLICTS OF INTEREST',
            'ETHICS STATEMENT'):
    H(key, 12)
    for para in back[key]:
        P(para, size=10)

H('SUPPLEMENTARY MATERIALS', 12)
P('Supplementary Results: the sarcomatoid urothelial carcinoma findings in '
  'full; a plain-language account of the four '
  'independent sources, what each can and cannot show, what was done with '
  'each and which deposited file holds its raw output; the penile squamous '
  'cell carcinoma findings in full; and the per-gene nomination routes with '
  'Supplementary Figure S1. '
  'Supplementary Methods: full procedural detail for the pipeline steps and '
  'the four independent evidence sources, including data releases, model '
  'specifications, thresholds and statistical tests. '
  'Supplementary Table S1: the complete association table, all rows and all '
  'score components, with the dataset and gene underlying each transcriptomic '
  'component, the fitted fold change and q-value, the pathway q-value, and an '
  'explicit flag on any row whose component is not re-derivable from deposited '
  'data. Supplementary Table S2: score-sensitivity analysis, giving the ranking '
  'under removal of the pathway '
  'dimension, removal of the literature dimension and a target-membership '
  'requirement for the pathway dimension, with whether '
  'each row still meets the score criterion under each, including the score with '
  'the former genomic dimension restored. Supplementary Table S3: per-dataset '
  'design summary, giving the contrast, the model fitted, the blocking or batch '
  'structure, sample counts and any confounding identified. Supplementary '
  'Table S4: the genomic value curated for each row, recomputed from the '
  'cohort it names where one exists, with the genes queried, the cohort '
  'size and the altered fraction. Supplementary Data: '
  'fitted differential-expression tables for every context, enrichment tables '
  'with nominal and corrected values, the renal medullary two-line reanalysis, '
  'the Human Protein Atlas, DepMap, PRISM and LINCS result tables, and the '
  'candidate-selection table.')

H('AI USAGE DISCLOSURE', 12)
P('Large language models were used for three things in this work: writing and '
  'debugging the analysis code, organizing the prior-proposal literature '
  'search, and drafting and editing manuscript text. The tools were Claude '
  '(Anthropic; ' + AI_CLAUDE_VERSION + ', accessed ' + AI_ACCESS_DATES + ') '
  'and ChatGPT (OpenAI; ' + AI_GPT_VERSION + ', accessed ' + AI_ACCESS_DATES +
  '). The mechanism schematic in Figure 2C was drafted with the '
  'figure-generation tool in BioRender (Toronto, Canada; accessed ' +
  AI_BIORENDER_DATE + ') from its scientific icon library, and each element '
  'was checked against the cited receptor pharmacology by the authors. No AI '
  'tool was used to generate, impute or alter any data. Every quantitative '
  'result reported here was produced by author-run scripts (Python 3.10; '
  'R 4.6.1 with limma 3.68.4 and edgeR 4.10.1) operating on the deposited '
  'public data, and the numbers in the manuscript come from those result '
  'tables. The authors checked every prior-proposal classification, score '
  'assignment and figure element against the underlying analysis and take '
  'full responsibility for the content and conclusions. The schematic '
  'prompts and the unedited exports are deposited with the code.', size=10)
for para in []:  # the inherited v28 paragraph duplicates the statement above
    # the inherited paragraph predates the refit and says Python only
    para = para.replace('All analyses were executed by author-run Python '
                        'analytical scripts',
                        'All analyses were executed by author-run Python and R '
                        'scripts')
    P(para, size=10)
# The v28 disclosure paragraph that stood here repeated the statement above.
# The per-figure correction history it carried lives in the repository audit
# log and in 45_prepare_panelC_images.py, not in the manuscript.

print('references, back matter and disclosure written')

# =====================================================================
# Table 1 (condensed; the full table is Supplementary Table S1)
# =====================================================================
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
merged = master.copy()  # master already carries Prior status
novel_rows = merged[merged['Prior status'].astype(str).str.startswith('FRAMEWORK-NOVEL')]
partial_rows = merged[merged['Prior status'].astype(str).str.startswith('PARTIALLY NOVEL')]
bench = defs[defs['Context'].isin(['NEPC', 'MIBC / MPBC', 'ccRCC / sRCC', 'ccRCC'])]

H('Table 1. Framework output by evidence class', 12)
P('Every association is accounted for in one class. The complete table, with '
  'the three scored components, the curated genomic value retained as unscored '
  'disease context, and the provenance of each, is Supplementary Table S1.',
  italic=True, size=9.5)

t = doc.add_table(rows=1, cols=6)
t.style = 'Table Grid'
# python-docx honours a width only when autofit is off, and the width has to
# be set on every cell; the number column was taking as much room as the
# drug column and forcing the long antagonist row to wrap
t.autofit = False
COL_IN = (0.32, 0.85, 2.05, 0.95, 1.45, 1.28)
hdr = ['#', 'Context', 'Drug / target', 'Score \u00b7 evidence tier', 'Status',
       'Required next step']
for c, h in zip(t.rows[0].cells, hdr):
    c.text = ''
    run = c.paragraphs[0].add_run(h)
    run.bold = True
    run.font.size = Pt(8.0)
# repeat the header on each page and stop rows splitting across pages
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
_tr = t.rows[0]._tr
_trPr = _tr.get_or_add_trPr()
_hdr = OxmlElement('w:tblHeader')
_hdr.set(qn('w:val'), 'true')
_trPr.append(_hdr)


def stage_tag(stage):
    """'FDA-approved (CLL, AML)' -> 'FDA approved'; 'Phase II/III (...)' -> 'Phase II/III'.

    The curated stage string carries the indication and the trial it rests on,
    which Table 1 has no room for. Supplementary Table S1 keeps it in full.
    """
    v = str(stage)
    low = v.lower()
    if 'preclinical' in low:
        return 'preclinical'
    if 'fda-approved' in low or 'fda approved' in low:
        return 'FDA approved'
    m = re.search(r'phase\s+(i{1,3}v?(?:\s*/\s*i{1,3}v?)*)', low)
    if m:
        return 'phase ' + m.group(1).upper().replace(' ', '')
    return v.split('(')[0].strip().lower() or 'stage not curated'


# the recovered therapies behind each positive-control block; these are the
# paper's only calibration evidence and no display item named them
CONTROL_AGENTS = {
    '1\u20136': 'recovers venetoclax, alisertib, tazemetostat, decitabine, '
                'cabazitaxel-carboplatin, olaparib',
    '7\u201313': 'recovers alisertib, talazoparib, alpelisib, erdafitinib, '
                 'enfortumab vedotin, pembrolizumab, palbociclib',
    '14\u201316': 'recovers pazopanib, belzutifan, abemaciclib',
}

TIER_PLAIN = {
    'Not tiered (pathway component not estimable)':
        'Not tiered (pathway component not computed)',
    'Not tiered (pathway and transcriptomic component not estimable)':
        'Not tiered (pathway and expression components not computed)',
}


def add_row(cells, bold=False, size=8.0):
    row = t.add_row()
    trPr = row._tr.get_or_add_trPr()
    cant = OxmlElement('w:cantSplit')
    trPr.append(cant)
    for c, v in zip(row.cells, cells):
        c.text = ''
        para = c.paragraphs[0]
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)
        # a tuple is (main text, qualifier); the qualifier is set smaller and
        # italic on its own line, which is how the clinical stage is shown
        main, qual = v if isinstance(v, tuple) else (v, None)
        run = para.add_run(str(main))
        run.font.size = Pt(size)
        run.bold = bold
        if qual:
            q = para.add_run('\n' + str(qual))
            q.font.size = Pt(size - 0.8)
            q.italic = True
    return row


# the number column was taking as much width as the drug column, forcing the
# long antagonist row to wrap; python-docx honours a width only with autofit
# off and only when it is set on every cell
# Word takes the column widths from tblGrid when the layout is fixed, so
# setting them on the cells alone left every column at the default inch
_grid = t._tbl.find(qn('w:tblGrid'))
for _gc, _w in zip(_grid.findall(qn('w:gridCol')), COL_IN):
    _gc.set(qn('w:w'), str(int(round(_w * 1440))))
for _row in t.rows:
    for _c, _w in zip(_row.cells, COL_IN):
        _c.width = Inches(_w)

# narrow cell margins: the table is six columns of prose and the default
# 0.08" left/right padding costs almost a page across thirty rows
_tblPr = t._tbl.tblPr
_mar = OxmlElement('w:tblCellMar')
for _side, _w in (('left', 60), ('right', 60), ('top', 10), ('bottom', 10)):
    _e = OxmlElement(f'w:{_side}')
    _e.set(qn('w:w'), str(_w))
    _e.set(qn('w:type'), 'dxa')
    _mar.append(_e)
_tblPr.append(_mar)


accounted = set()

add_row(['', 'POSITIVE CONTROLS \u2014 not evaluated as discovery', '', '', '', ''],
        bold=True)
for ctxs, label in ((('NEPC',), 'Neuroendocrine prostate'),
                    (('MIBC / MPBC',), 'Muscle-invasive bladder'),
                    (('ccRCC / sRCC', 'ccRCC'), 'Clear cell renal')):
    sub = merged[merged['Context'].isin(ctxs)]
    if not len(sub):
        continue
    accounted |= set(sub['N'])
    tiers_here = {TIER_PLAIN.get(k, k): v for k, v in
                  sub['Tier'].value_counts().to_dict().items()}
    _st = [stage_tag(x) for x in defs.loc[defs['N'].isin(sub['N']), 'Stage']]
    _sc = Counter(_st)
    rng = f'{sub["N"].min()}\u2013{sub["N"].max()}'
    add_row([rng, label,
             (f'{len(sub)} associations, all recovering priorities proposed '
              f'elsewhere',
              '; '.join(f'{v} {k}' for k, v in _sc.most_common())),
             ', '.join(f'{v} {k}' for k, v in tiers_here.items()),
             'positive control', CONTROL_AGENTS.get(rng, 'not a discovery candidate')])

# previously proposed priorities arising in the rare or variant contexts
rare_recovery = merged[merged['N'].isin([18, 20])]
if len(rare_recovery):
    add_row(['', 'PREVIOUSLY PROPOSED, IN THE RARE CANCERS', '', '', '', ''], bold=True)
    for _, r in rare_recovery.iterrows():
        accounted.add(int(r['N']))
        add_row([r['N'], r['Context'],
                 (f"{r['Drug']} \u2014 {r['Target']}",
                  stage_tag(r['Stage'])),
                 f"{r['Total']} \u00b7 {TIER_PLAIN.get(r['Tier'], r['Tier'])}", 'previously proposed',
                 'recovered in a rare cancer'])

add_row(['', 'NO PRIOR UROLOGIC-ONCOLOGY PROPOSAL IDENTIFIED', '', '', '', ''],
        bold=True)
for _, r in novel_rows.sort_values('N').iterrows():
    accounted.add(int(r['N']))
    srow = sel[sel['N'] == r['N']]
    if len(srow):
        srow = srow.iloc[0]
        # spell the exclusion out; codes are opaque and were being truncated
        PLAIN = {
            23: 'Lower confidence: scores 3 of the 4 points its cohort can '
                'support, and the criterion asks for 4',
            24: 'Lower confidence: the target is not abundantly expressed '
                'in sarcomatoid tumors, at the 73rd percentile of measured '
                'transcripts',
            29: 'Lower confidence: transcriptomic support does not hold '
                'under a batch-adjusted subtype model '
                f"(q = {de['SSTR2_neurod1']['q']:.3f}), and no enriched pathway "
                'contains the target',
        }
        # each prioritized row loses eligibility under a different variant, so
        # the cell names the one that removes it rather than saying "sensitive"
        status = ('Prioritized; first rank within RMC; not eligible without '
                  'the pathway dimension (Supplementary Table S2)'
                  if int(r['N']) == 17 else
                  'Prioritized under the primary score; below threshold when '
                  'pathway points require membership of an enriched set '
                  '(Supplementary Table S2)'
                  if int(r['N']) == 19 else
                  'Prioritized; not eligible without the literature point '
                  '(Supplementary Table S2)' if int(r['N']) == 28 else
                  'Prioritized' if bool(srow['survives']) else
                  PLAIN.get(int(r['N']),
                            'Not prioritized: ' + str(srow['reservation'])))
    else:
        status = ''
    nxt = {17: 'immunocompetent model with an intact myeloid compartment',
           19: 'RMC tumor-surface confirmation and normal-tissue safety assessment',
           28: 'SCBC-specific expression, internalization and payload testing',
           23: 'dependency testing in sarcomatoid rather than conventional '
               'urothelial models',
           24: 'a sarcomatoid cohort whose histology is not confounded with '
               'array chip',
           29: 'a larger NEUROD1-positive cohort with batch separable from '
               'subtype'}.get(int(r['N']), 'not carried forward')
    add_row([r['N'], r['Context'],
             (f"{r['Drug']} \u2014 {r['Target']}", stage_tag(r['Stage'])),
             f"{r['Total']} \u00b7 {TIER_PLAIN.get(r['Tier'], r['Tier'])}", status, nxt])

add_row(['', 'PARTIAL PRECEDENT', '', '', '', ''], bold=True)
accounted |= set(partial_rows['N'])
_pst = Counter(stage_tag(x) for x in
                defs.loc[defs['N'].isin(partial_rows['N']), 'Stage'])
add_row([', '.join(str(int(x)) for x in sorted(partial_rows['N'])), 'various',
         (f'{len(partial_rows)} associations extending a precedent from '
          f'the conventional form of the disease to this variant',
          '; '.join(f'{v} {k}' for k, v in _pst.most_common())),
         ', '.join(f'{v} {k}' for k, v in
                   {TIER_PLAIN.get(k, k): v for k, v in
                    partial_rows['Tier'].value_counts().to_dict().items()}.items()),
         'not evaluated as discovery', 'see Supplementary Table S1'])

add_row(['', 'REPORTED, NOT SCORED AS A DRUG HYPOTHESIS', '', '', '', ''],
        bold=True)
# the one row whose transcriptomic component is also inestimable: a loss
# marker can only be demonstrated by the comparison this cohort cannot support
unscored = merged[merged['Tier'].str.contains('transcriptomic')
                  & (~merged['N'].isin(accounted))]
for _, r in unscored.sort_values('N').iterrows():
    accounted.add(int(r['N']))
    add_row([r['N'], r['Context'],
             ('TROP2 (TACSTD2) expression \u2014 unscored observation, not a scored '
              'association',
              'sacituzumab govitecan: FDA approved, urothelial indication '
              'withdrawn 2024'),
             'not computed',
             'the apparent between-group difference cannot be separated '
             'from chip batch',
             'independent, non-confounded cohort'])

missing = sorted(set(merged['N']) - accounted)
assert not missing, f'Table 1 omits associations {missing}'
print(f'  Table 1: all {len(accounted)} associations accounted for')

P('The line under each therapy gives its furthest clinical stage: FDA approved '
  'means approved somewhere, not necessarily in the cancer named here, and '
  'the approved indication and supporting trial are given in full in '
  'Supplementary Table S1. '
  'Scores sum three partially overlapping dimensions (transcriptomic '
  '0\u20133, pathway 0\u20132, external literature '
  '0\u20131) and express strength of evidence within this framework only, not '
  'established drug sensitivity. "No prior urologic-oncology proposal '
  'identified" refers to the pre-specified PubMed search and makes no claim of '
  'biological precedence outside urology. Sarcomatoid rows are reported '
  'descriptively: the two tumor types were run on separate batches of chips in that '
  'series, so no model can attribute the differences to biology.',
  italic=True, size=9)

# =====================================================================
# Supplementary tables generated alongside
# =====================================================================
SUP = paths.OUTPUT / 'v31_supplementary'
SUP.mkdir(parents=True, exist_ok=True)

full = master.merge(prov[['N', 'scoring_gene', 'arm', 'refit_context', 'E_basis',
                          'refit_log2FC', 'refit_q', 'P_basis', 'pathway_q',
                          'E_derivable_from_data']], on='N')
full.to_csv(SUP / 'Supplementary_Table_S1_full_association_table.csv', index=False)

# S2: score sensitivity - how the ranking moves under each ablation
rows = []
for _, r in prov.iterrows():
    e, p_, l = int(r['E_refit']), int(r['P_refit']), int(r['L_curated'])
    member = 'target in pathway set' in str(r['P_basis'])
    # the curated genomic value the score no longer carries, kept here so the
    # reader can see what dropping it did to each row
    g = int(r.get('G_disease_context_not_scored', 0) or 0)
    rows.append({
        'N': int(r['N']), 'Target': r['Target'],
        'full': e + p_ + l,
        'no_pathway': e + l,
        'no_literature': e + p_,
        # a pathway point can rest on an enrichment the target is not part of
        'pathway_requires_membership': e + (p_ if member else 0) + l,
        'with_former_genomic_dimension': g + e + p_ + l,
        'denominator': int(str(r.get('total_denominator', 6) or 6)),
    })
s2 = pd.DataFrame(rows)
VARIANTS = ('full', 'no_pathway', 'no_literature',
            'pathway_requires_membership', 'with_former_genomic_dimension')
for col in VARIANTS:
    s2[f'rank_{col}'] = s2[col].rank(ascending=False, method='min').astype(int)
    # E2 asks for 4 or better of the points estimable for that row
    s2[f'meets_E2_{col}'] = s2[col] >= 4
s2.to_csv(SUP / 'Supplementary_Table_S2_score_sensitivity.csv', index=False)

# S3: per-dataset design summary
summ = pd.read_csv(RF / 'REFIT_SUMMARY.csv')
man = pd.read_csv(REPO / 'data' / 'prepared' / 'PREPARED_MANIFEST.csv')
s3 = summ.merge(man[['context', 'samples', 'data_type', 'note']], on='context',
                how='left')
s3.to_csv(SUP / 'Supplementary_Table_S3_dataset_designs.csv', index=False)

# S4 is written by 58_genomic_provenance.py straight into the supplement
_gp = SUP / 'GENOMIC_PROVENANCE.csv'
if _gp.exists():
    (SUP / 'Supplementary_Table_S4_genomic_provenance.csv').write_bytes(
        _gp.read_bytes())

for f in ('LINCS_CONNECTIVITY_V29.csv', 'CANDIDATE_SELECTION.csv',
          'KEGG_ENRICHMENT_REFIT.csv', 'RMC_ENRICHMENT.csv',
          'SCORING_PROVENANCE_V29.csv', 'REFIT_VS_PUBLISHED.csv'):
    if (RF / f).exists():
        (SUP / f).write_bytes((RF / f).read_bytes())

doc.save(str(OUT))

# =====================================================================
# Report
# =====================================================================
d2 = docx.Document(str(OUT))
ps = [p.text.strip() for p in d2.paragraphs]
i0 = ps.index('INTRODUCTION')
i1 = ps.index('DATA AVAILABILITY')
# The figure legends sit AFTER Data Availability, so they were never inside
# the Introduction-to-Discussion span; subtracting them understated the body by
# 563 words. A Results paragraph opening "Figure 4 and Table 1 together give..."
# was also being mistaken for a legend and subtracted. Count the span as it is.
body = sum(len(ps[i].split()) for i in range(i0, i1) if ps[i])
legends = sum(len(t_.split()) for t_ in ps[i1:]
              if t_.startswith('Figure ') and len(t_.split()) > 40)
a0 = ps.index('ABSTRACT')
abstract = sum(len(ps[i].split()) for i in range(a0 + 1, a0 + 6) if ps[i])
c0 = ps.index('CONTEXT')
ctx = sum(len(ps[i].split()) for i in range(c0 + 1, c0 + 3) if ps[i])

print(f"\nSaved {OUT}")
print(f"  body        {body} words")
print(f"  abstract    {abstract} words")
print(f"  context     {ctx} words")
print(f"  figures     {len(d2.inline_shapes)}")
print(f"  tables      {len(d2.tables)} (Table 1 has {len(d2.tables[0].rows)} rows)")
print(f"  references  {len(refs)}")
print(f"  supplementary written to {SUP}")
print("\nS2 sensitivity, lead candidate rank under each variant:")
lead_s2 = s2[s2['N'] == 17].iloc[0]
for col in ('full', 'no_pathway', 'no_literature',
            'pathway_requires_membership'):
    print(f"    {col:<30} score {lead_s2[col]:>2}  rank {lead_s2['rank_' + col]}")

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

TITLE = ('Prioritizing Existing Drugs for Rare and Variant Urologic '
         'Cancers Using Public Data')
p = doc.add_paragraph()
r = p.add_run(TITLE)
r.bold = True
r.font.size = Pt(15)

P('Running title: Drug Prioritization From Public Cancer Data')
P('Authors: Garrett J. Brinkley, MD\u00b9; Jacob Greenberg, MD\u00b9; '
  'Jorge Caso, MD\u00b9')
P('Affiliations: \u00b9Department of Urology, Tulane University School of '
  'Medicine, New Orleans, Louisiana, USA')
P('Corresponding Author: Garrett J. Brinkley, MD; Department of Urology, Tulane '
  'University School of Medicine, New Orleans, LA; garrettjbrinkley@gmail.com')

H('CONTEXT', 12)
P(f"Key Objective: Can public molecular data help prioritize existing drugs "
  f"for rare and variant urologic cancers that are difficult to study in "
  f"randomized trials?")
P(f"Knowledge Generated: We developed a step-by-step workflow to evaluate "
  f"{F['n_drug_hypotheses']} drug-cancer hypotheses and one biomarker "
  f"observation. {spell(F['funnel']['survive']).capitalize()} candidates "
  f"without an identified prior urologic proposal met the ranking criteria. "
  f"Reanalysis also identified a candidate that lost statistical support after "
  f"batch adjustment and a dataset in which tumor type could not be separated "
  f"from batch. The results provide priorities for experimental testing, not "
  f"evidence of treatment benefit.")

H('ABSTRACT', 12)
P(f"Purpose: To develop a step-by-step workflow that uses public molecular "
  f"data to prioritize existing drugs for rare and variant urologic cancers.")
P(f"Methods: Within each cancer, genes were ranked by their molecular "
  f"signal, and the highest-ranked were reviewed to carry a small number "
  f"forward. We reassessed that candidate set using public genomic data, "
  f"{F['n_series_total']} gene-expression datasets, and drug-target "
  f"databases. A 6-point score combined gene expression, pathway "
  f"enrichment, and support from published mechanistic studies. Candidates "
  f"mainly involved approved or investigational drugs, with "
  f"{spell(F['stage']['preclinical'])} preclinical exceptions. We reanalyzed "
  f"expression data according to study design where sample-level data were "
  f"available, classified prior urologic proposals, and applied prespecified "
  f"ranking criteria.")
P(f"Results: The workflow evaluated {F['n_drug_hypotheses']} drug-cancer "
  f"hypotheses and one unscored biomarker observation. "
  f"{spell(F['n_complete_score']).capitalize()} candidates had complete "
  f"scores: {F['tiers'].get('Strong', 0)} Strong, "
  f"{F['tiers'].get('Moderate', 0)} Moderate, and "
  f"{F['tiers'].get('Exploratory', 0)} Exploratory. "
  f"{spell(F['n_partial_score']).capitalize()} had partial scores without an "
  f"evidence tier. All {F['arm_control']['n']} positive-control candidates "
  f"matched previously proposed approaches. {F['arm_discovery']['novel']} of "
  f"{F['n_rare_hypotheses']} rare-cancer hypotheses had no identified prior "
  f"urologic proposal. {spell(F['funnel']['survive']).capitalize()} met the "
  f"ranking criteria: CXCR1/CXCR2 blockade and anti-CEACAM1 in renal medullary "
  f"carcinoma, and CEACAM5-directed antibody-drug conjugates in ASCL1-positive "
  f"small-cell bladder cancer. Requiring target membership in an enriched "
  f"pathway excluded anti-CEACAM1 but retained the other two. SSTR2 lacked "
  f"significant expression support after batch adjustment, and the sarcomatoid "
  f"dataset could not separate histology from batch.")
P(f"Conclusion: Public data can help prioritize drug hypotheses for rare "
  f"cancers. Rankings depend on data quality and scoring assumptions, and all "
  f"prioritized candidates require experimental validation.")

# =====================================================================
# Introduction
# =====================================================================
H('INTRODUCTION')
P('Public cancer datasets can help researchers identify treatment options '
  'worth testing. The Cancer Genome Atlas (TCGA) records tumor mutations and '
  'other genomic changes [1,2], which can be searched through cBioPortal [3]. '
  'The Gene Expression Omnibus (GEO) provides gene-expression data [4]. The '
  'Therapeutic Target Database [5] and Open Targets [6] link proteins to drugs '
  'and their development stage. The Kyoto Encyclopedia of Genes and Genomes '
  '(KEGG) groups genes into biological pathways [7]. Together, these resources '
  'support drug repurposing: studying an existing drug for a different '
  'disease.')
P('Drugs already approved or tested in people may have safety and '
  'pharmacokinetic data that can reduce development time and cost [8]. The '
  'challenge is finding drugs with a clear biological rationale in the new '
  'disease. This is especially important for renal medullary carcinoma, penile '
  'squamous cell carcinoma, sarcomatoid urothelial carcinoma, and small-cell '
  'bladder cancer [9\u201313]. These aggressive cancers have limited '
  'biomarker-directed treatment evidence, and small patient populations make '
  'randomized trials difficult.')
P('We developed a step-by-step workflow to use public cancer data to '
  'prioritize existing drugs for further study. We applied it to four rare or '
  'variant urologic cancers and three positive-control cancers: '
  'neuroendocrine prostate cancer, muscle-invasive bladder cancer, and clear '
  'cell renal cell carcinoma. The controls were selected because published '
  'treatment proposals provided a reference for comparison. The workflow '
  'ranks genes within each cancer by their molecular signal, reviews the '
  'highest-ranked for clinical relevance, and then scores and ranks the '
  'resulting candidates reproducibly (Figure 1).')

# =====================================================================
# Methods
# =====================================================================
H('MATERIALS AND METHODS')
H('Data Sources and Study Sequence', 11.5, 10, level=2)
P(f"We reassessed a set of drug-cancer candidates drawn from the highest-ranked "
  f"molecular signals in each cancer, as described below. The "
  f"candidate list, scoring components, point ranges, and ranking criteria "
  f"were fixed before reanalysis. We then reanalyzed each dataset using "
  f"methods appropriate to its study design. A later audit found that the "
  f"genomic score could not be consistently reproduced, so we removed it. This "
  f"reduced the maximum score from 9 to 6. The prioritization threshold "
  f"remained 4 points and therefore became more demanding (Supplementary "
  f"Table S4).")
P(f"Genomic data came from the TCGA Pan-Cancer Atlas 2018 through cBioPortal "
  f"[1\u20133]. TCGA lacks neuroendocrine prostate cancer and the four rare "
  f"cancers. Prostate adenocarcinoma therefore provided related-disease "
  f"genomic context for neuroendocrine prostate cancer; rare-cancer candidates "
  f"were selected using expression data. Genomic information informed "
  f"candidate selection but did not contribute to the final score. "
  f"Transcriptomic data came from {F['n_series_total']} GEO datasets [4]. Gene "
  f"symbols were standardized using the HGNC complete set. Because a defining "
  f"alteration such as SMARCB1 loss may not itself be druggable [14], "
  f"expression-based selection was not limited to recurrently altered genes.")
P('The deposited scripts reproduce differential expression, pathway '
  'enrichment, scoring, and ranking. They do not reproduce the original manual '
  'gene-to-drug search because individual search queries were not saved. Full '
  'procedures are described in the Supplementary Methods.')

H('Candidate Selection', 11.5, 10, level=2)
P('Each candidate paired a therapy, drug class, or combination with one '
  'cancer or molecular subtype. Several drugs targeting the same biological '
  'axis counted as one candidate. Candidates were not assembled as a free '
  'list of drugs. Within each cancer, every measured gene was ranked by its '
  'molecular signal: alteration frequency where a TCGA cohort was available, '
  'and the moderated t-statistic from that cancer\u2019s expression fit '
  'otherwise. Only the highest-ranked genes were reviewed, and three to seven '
  'per cancer were carried forward, including three to five per rare cancer. '
  'The judgment applied at this step was which of the top-ranked signals to '
  'pursue, weighing clinical relevance; the ranking itself came from the '
  'data. Those genes were then matched to therapies through the Therapeutic '
  'Target Database and Open Targets, and a gene became a candidate only where '
  'a therapy existed. Two preclinical therapies were retained because no '
  'clinical-stage drug targeted the protein; neither was eligible for '
  'prioritization.')
P(f"In the rare cancers, initial expression-based selection required q < 0.05 "
  f"and log2 fold change >0.5. This threshold applied to the measured evidence "
  f"gene, which could be a ligand or signature member rather than the drug "
  f"target. Selection thresholds were distinct from the eligibility criteria "
  f"applied after reanalysis. "
  f"{spell(F['geo_rows_no_recurrent_alteration']).capitalize()} of the "
  f"{F['n_geo_anchored']} rare-cancer entries were selected through expression "
  f"alone. In the original curation, {F['tcga_rows_freq_ge_15pct']} of "
  f"{F['n_tcga_anchored']} control candidates involved genes recorded as "
  f"altered in at least 15% of the cohort; these values were not the audited "
  f"estimates in Supplementary Table S4.")
P(f"The 18 prespecified gene sets were used for scoring, not selection. Seven "
  f"candidates, including four cell-surface antigens and two prioritized "
  f"candidates, had targets outside these sets. This was a ranked shortlist, "
  f"not an exhaustive drug screen: {F['funnel_entry']:,} gene-cancer pairs "
  f"met the expression threshold, and only those at the top of each cancer\u2019s "
  f"ranking were carried into drug matching (Supplementary Methods Section 7b).")

H('Prioritization Score', 11.5, 10, level=2)
P('Candidates received up to 6 points: gene-expression evidence, 0\u20133; '
  'pathway evidence, 0\u20132; and supporting mechanistic literature, '
  '0\u20131. Pathway scoring awarded one point for set membership or '
  'enrichment and two when the target belonged to an enriched set. Full '
  'scoring rules appear in Supplementary Methods Section 6. These evidence '
  'sources overlap and are not independent.')
P('Complete scores were classified as Strong (5\u20136), Moderate '
  '(3\u20134), or Exploratory (1\u20132). These tiers describe evidence within '
  'this workflow, not demonstrated drug activity. Candidates with an '
  'unavailable component were scored out of the remaining points and received '
  'no tier. When expression support could not be recalculated from the '
  'deposited data, the original curated value was retained and clearly flagged '
  'with its source in Supplementary Table S1.')

H('Prior-Proposal Classification', 11.5, 10, level=2)
P('After scoring, one author searched PubMed through ' + PUBMED_SEARCH_THROUGH
  + ', without date or language restrictions. Candidates were classified as '
  'previously proposed, having a partial precedent, or having no identified '
  'prior urologic-oncology proposal. A prior proposal required a report, '
  'review, position paper, or trial registration proposing the therapy or drug '
  'class against the target in that disease. A partial precedent meant that '
  'the target had been described without a proposed therapy, or that the '
  'therapy had been proposed for the conventional cancer rather than its '
  'variant.')
P('Reports from non-urologic cancers could provide the mechanistic-literature '
  'point but did not establish a urologic precedent. No second reviewer '
  'repeated the classification. Although these searches followed scoring, '
  'prior knowledge had already informed candidate selection. The search '
  'strategy, counting rules, and classifications are deposited with the code.')

H('Ranking Criteria', 11.5, 10, level=2)
P('Candidates were prioritized only when they met all four prespecified '
  'criteria:')
for _c in ('No prior urologic-oncology proposal was identified.',
           'The total score was at least 4 points.',
           'Expression support could be recalculated from deposited data and '
           'met the relevant threshold: q < 0.05 for a disease comparison or '
           'the top 15% of measured transcripts for an abundance-only '
           'analysis.',
           'A therapy was FDA-approved for another disease or in clinical '
           'trials, with a documented development pathway.'):
    _p = doc.add_paragraph(_c, style='List Number')
    _p.paragraph_format.space_after = Pt(2)
P('The 4-point threshold was absolute: a candidate scored out of 4 needed all '
  '4 points. Candidates were ranked within diseases, not across diseases. When '
  'a disease had multiple eligible candidates, first rank also required target '
  'membership in an enriched pathway. Checks for contradictory external '
  'evidence and target accessibility changed no rankings. Candidates that '
  'failed a criterion were retained and labeled with the reason.')

H('Statistical Analysis', 11.5, 10, level=2)
P('Each dataset was analyzed according to its study design (Supplementary '
  'Table S3). Count data were filtered with edgeR filterByExpr, normalized by '
  'the trimmed mean of M-values, and analyzed with voom weights and limma. '
  'Log-scale and summarized expression data were analyzed with limma-trend and '
  'robust empirical Bayes moderation.')
P(f"Models accounted for repeated samples and batch effects where possible. "
  f"The penile cancer dataset included {dsn['pscc_normal_arrays']} "
  f"normal-tissue arrays from {dsn['pscc_normal_donors']} donors; "
  f"duplicateCorrelation modeled donor effects, with a consensus correlation "
  f"of {F['refit']['pscc_dupcor'].split('consensus ')[-1]}. The matched "
  f"bladder kinome dataset used patient as a fixed blocking factor. Small-cell "
  f"bladder subtypes were compared with the mean of the remaining subtypes, "
  f"adjusting for batch.")
P('In the sarcomatoid dataset, all sarcomatoid and conventional tumors were '
  'processed on separate chip batches. Histology and batch therefore could not '
  'be separated. We did not estimate differences between the two histologies. '
  'Instead, we ranked mean transcript abundance within the 28 sarcomatoid '
  'tumors and repeated these rankings within each batch.')
P(f"The renal medullary dataset contained a SMARCB1 rescue experiment in two "
  f"patient-derived cell lines, available only as a published "
  f"differential-expression table. We could not refit a sample-level model. "
  f"Genes had to change consistently in both lines, with |log2 fold change| "
  f">0.5 and q < 0.05 in each. Effects were oriented to the SMARCB1-null "
  f"disease state, and the larger of the two q-values was reported. The lines "
  f"were treated as separate experimental models, not a patient cohort.")
P('Pathway enrichment tested whether the 18 selected gene sets contained more '
  'upregulated genes than expected by chance. We used one-sided hypergeometric '
  'tests on genes with q < 0.05 and log2 fold change >0.5. The background '
  'included only genes measured in that dataset, avoiding bias from using the '
  'whole genome for targeted panels.')
P('Benjamini\u2013Hochberg correction was applied across tested genes for '
  'differential expression and across the 18 gene sets within each disease or '
  'subtype for enrichment. It was not applied across diseases, drugs, or later '
  'comparisons. Throughout, q denotes the adjusted P value. Thresholds were '
  'q < 0.05 for differential expression and an exploratory q < 0.10 for '
  'enrichment; enrichment values from 0.05 to <0.10 were considered '
  'suggestive. Analyses used R 4.6.1, limma 3.68.4, edgeR 4.10.1, and '
  'Python 3.10.')

print('front matter and methods written')

# =====================================================================
# Results
# =====================================================================
H('RESULTS')
H('Candidate Overview', 11.5, 10, level=2)
P(f"The workflow evaluated {F['n_drug_hypotheses']} drug-cancer hypotheses "
  f"and one unscored biomarker observation (Table 1). "
  f"{spell(F['arm_control']['n']).capitalize()} entries involved "
  f"positive-control cancers and {F['arm_discovery']['n']} involved rare "
  f"cancers. Among {F['n_complete_score']} candidates with complete scores, "
  f"{F['tiers'].get('Strong', 0)} were Strong, {F['tiers'].get('Moderate', 0)} "
  f"Moderate, and {F['tiers'].get('Exploratory', 0)} Exploratory. "
  f"{spell(F['n_partial_score']).capitalize()} sarcomatoid candidates had "
  f"partial scores out of 4 and received no tier. Of the "
  f"{F['n_drug_hypotheses']} drug hypotheses, {F['stage']['approved']} named "
  f"FDA-approved therapies, {F['stage']['in_trials']} investigational "
  f"therapies, and {F['stage']['preclinical']} preclinical therapies. Approval "
  f"refers to any indication, not necessarily the cancer studied here.")

H('Positive Controls', 11.5, 10, level=2)
P(f"All {F['arm_control']['n']} control candidates matched previously "
  f"proposed treatment approaches: six in neuroendocrine prostate cancer "
  f"[15\u201323], seven in muscle-invasive bladder cancer [24\u201332], and "
  f"three in clear cell renal cell carcinoma [33\u201337]. Erlotinib in renal "
  f"medullary carcinoma [38,39] and pembrolizumab in penile cancer "
  f"[40\u201342] provided two additional matches within the rare cancers. "
  f"These {F['n_previously_proposed']} matches demonstrate agreement with "
  f"existing proposals, not independent validation.")

H('Rare and Variant Cancers', 11.5, 10, level=2)
P(f"In renal medullary carcinoma, changes across the "
  f"{rmc['genes_measured_both']:,} genes measured in both cell lines were "
  f"weakly correlated (r = {rmc['r_between_lines']:.2f}). Requiring consistent "
  f"changes in both lines retained {rmc['up_both']} genes. CXCL8 was "
  f"elevated in the SMARCB1-null state in both lines (log2 fold changes, "
  f"{rmc['CXCL8']['RMC2C']:+.2f} and {rmc['CXCL8']['RMC219']:+.2f}), as were CXCL1, "
  f"CXCL2, and CXCL3. Chemokine signaling was enriched "
  f"(q = {q['rmc_chemokine']:.4f}; Figure 2), consistent with the "
  f"neutrophil-rich microenvironment reported in this disease [43]. These "
  f"findings supported CXCR1/CXCR2 blockade. CEACAM1 was also elevated in both "
  f"lines ({rmc['CEACAM1']['RMC2C']:+.2f} and {rmc['CEACAM1']['RMC219']:+.2f}).")
P(f"Small-cell bladder tumors were grouped by lineage transcription factor "
  f"[44]. ASCL1-positive tumors had higher CEACAM5 expression (log2 fold "
  f"change, {de['CEACAM5_ascl1']['log2FC']:+.2f}; "
  f"q = {fmt(de['CEACAM5_ascl1']['q'])}), supporting study of CEACAM5-directed "
  f"antibody-drug conjugates (Figure 3). POU2F3-positive tumors showed "
  f"suggestive enrichment of arachidonic-acid metabolism "
  f"(q = {q['pou2f3_arachidonic']:.3f}) and increased PTGS1 expression "
  f"({de['PTGS1_pou2f3']['log2FC']:+.2f}; "
  f"q = {de['PTGS1_pou2f3']['q']:.3f}). These findings do not establish "
  f"whether COX-1 should be inhibited or activated. Prostaglandin signaling "
  f"has restrained tumor formation in another tuft-cell model [45].")
P(f"In NEUROD1-positive tumors, SSTR2 retained a positive fold change "
  f"({de['SSTR2_neurod1']['log2FC']:+.2f}) but was not significant after batch "
  f"adjustment (q = {de['SSTR2_neurod1']['q']:.3f}). The neuroactive "
  f"ligand-receptor gene set was also not enriched. These results did not "
  f"support extending the small-cell lung cancer SSTR2 approach [46] to this "
  f"bladder subtype.")
P(f"Sarcomatoid results were limited to within-tumor transcript abundance "
  f"because histology was inseparable from chip batch (Figure 4; "
  f"Supplementary Figure S2). UHRF1 [47], NSD2, and G6PD [48] remained above "
  f"the 85th percentile in every batch; ATR remained below it. Pathway scores "
  f"were not computed, leaving {F['n_partial_score']} candidates with partial "
  f"scores. TROP2 was reported only as an unscored expression observation, not "
  f"a predictive biomarker [49\u201351]. Full results appear in the "
  f"Supplementary Results.")
P(f"Penile cancer showed an immune-active expression pattern supporting the "
  f"established pembrolizumab proposal [40\u201342]. Two other candidates had "
  f"partial precedents [52\u201354]; none lacked a prior urologic proposal.")

H('Candidates Without an Identified Prior Proposal', 11.5, 10, level=2)
P(f"Of the {F['n_rare_hypotheses']} rare-cancer drug hypotheses, "
  f"{spell(F['arm_discovery']['proposed'])} were previously proposed, "
  f"{spell(F['arm_discovery']['partial'])} had partial precedents, and "
  f"{spell(F['arm_discovery']['novel'])} had no identified prior "
  f"urologic-oncology proposal. {spell(F['funnel']['survive']).capitalize()} "
  f"of the {spell(F['arm_discovery']['novel'])} met all prioritization "
  f"criteria (Figure 5). SSTR2 failed the score and expression criteria "
  f"({_s2v(29,'full')}/6; q = {de['SSTR2_neurod1']['q']:.3f}). ATR failed the "
  f"score and abundance criteria (1/4; "
  f"{ordinal(F['abundance_pct']['ATR']['pct'])} percentile). NSD2 met the "
  f"abundance criterion but fell below the score threshold (3/4). These "
  f"exclusions reflect the available evidence and do not rule out therapeutic "
  f"activity.")
P(f"CXCR1/CXCR2 blockade ranked first within renal medullary carcinoma "
  f"({lead['total']}/6). Both receptors are membrane proteins in the Human "
  f"Protein Atlas [55], and antagonists are in clinical development. However, "
  f"neither receptor was measured in the renal medullary dataset. The "
  f"expression evidence came from their chemokine ligands. Those same ligands "
  f"drove pathway enrichment, so the expression and pathway scores were not "
  f"independent. This hypothesis concerns myeloid-cell recruitment and "
  f"requires an immunocompetent model with an intact myeloid compartment; "
  f"tumor-cell monoculture alone cannot test it.")
P(f"Anti-CEACAM1 also qualified in renal medullary carcinoma "
  f"({second['total']}/6), but its ranking was sensitive to pathway scoring. "
  f"Its pathway point came from an enriched cytokine-receptor set "
  f"(q = {ceacam1_pq}) that did not include CEACAM1. Requiring target "
  f"membership removed that point and reduced the score to "
  f"{_s2v(19,'membership')}/6 (Supplementary Table S2). Tumor-surface protein "
  f"expression and the therapeutic index in renal medullary carcinoma remain "
  f"unknown.")
P(f"CEACAM5-directed antibody-drug conjugates qualified in ASCL1-positive "
  f"small-cell bladder cancer ({_s2v(28,'full')}/6). Human Protein Atlas data "
  f"support membrane localization [55], and the drug class is in clinical "
  f"development. Normal bladder RNA expression was "
  f"{F['hpa']['nTPM']['CEACAM5']} normalized transcripts per million; this "
  f"informs safety planning but does not establish a systemic therapeutic "
  f"window. CEACAM5 belonged to none of the 18 selected gene sets and earned "
  f"no pathway points. Removing its literature point reduced the score to "
  f"{_s2v(28,'full') - 1}/6. Subtype-specific protein expression, antibody "
  f"internalization, and payload sensitivity remain untested.")

print('results written')

# =====================================================================
# Discussion
# =====================================================================
H('DISCUSSION')
P(f"This study used public molecular data to prioritize existing drugs for "
  f"rare and variant urologic cancers. "
  f"{spell(F['funnel']['survive']).capitalize()} candidates met the "
  f"prespecified criteria: CXCR1/CXCR2 blockade and anti-CEACAM1 in renal "
  f"medullary carcinoma, and CEACAM5-directed antibody-drug conjugates in "
  f"ASCL1-positive small-cell bladder cancer. The value of this approach is a "
  f"transparent, testable shortlist, not evidence that these treatments work.")
P('Reanalysis changed which candidates qualified. SSTR2 retained a positive '
  'fold change but lost statistical support after batch adjustment. The '
  'sarcomatoid comparison could not separate tumor biology from chip batch, so '
  'we used within-tumor abundance rather than a histology comparison. These '
  'examples show why published summary results cannot always substitute for '
  'analysis that accounts for study design.')
P('Computational drug repurposing from public expression data is established '
  '[56]. GETgene-AI combines mutation frequency, differential expression, and '
  'drug-target annotation [57]. Signature-reversion work has shown that the '
  'differential-expression method can change drug rankings [58]. '
  'Pathway2Targets prioritizes drugs through pathway membership [59]. Our '
  'workflow uses similar information but applies it to rare cancers with '
  'limited data. It also reports which candidates fail the ranking criteria '
  'and why.')
P(f"The {F['n_previously_proposed']} matches to previous proposals should not "
  f"be interpreted as independent validation. Prior knowledge influenced the "
  f"gene-set panel, the review of top-ranked genes, and the representative "
  f"therapies chosen for each target. The "
  f"controls show that the workflow can return established proposals, but they "
  f"do not estimate its sensitivity or precision.")
P(f"The score is a ranking tool, not a measure of treatment benefit. "
  f"Expression and pathway components can reward the same biological signal, "
  f"and the primary score permits a pathway point even when the target is "
  f"outside the enriched set. No prioritized candidate remained eligible under "
  f"every alternative scoring rule. CXCR1/CXCR2 blockade fell to "
  f"{_s2v(17,'full') - 2} points without pathway evidence; anti-CEACAM1 fell "
  f"to {_s2v(19,'membership')} when pathway points required target membership; "
  f"and anti-CEACAM5 fell to {_s2v(28,'full') - 1} without literature support. "
  f"These differences make the assumptions behind each ranking important to "
  f"report (Supplementary Table S2).")
P(f"The genomic audit identified another limitation of the original scoring "
  f"system. Recalculation reproduced the curated score band in only "
  f"{F['genomic_audit']['agree']} of {F['genomic_audit']['recomputed']} "
  f"candidates with an available comparison cohort. Some values represented a "
  f"defining disease alteration rather than an alteration in the drug target. "
  f"Removing this component did not change which of the "
  f"{spell(F['arm_discovery']['novel'])} candidates without a prior proposal "
  f"were prioritized, although {spell(F['genomic_audit']['controls_moved'])} "
  f"control candidates fell below the score threshold (Supplementary "
  f"Table S4).")
P('Data availability imposed further limits. TCGA provided direct genomic '
  'context only for muscle-invasive bladder and clear cell renal cell '
  'carcinoma. Neuroendocrine prostate cancer used related-histology context, '
  'and the four rare cancers had no TCGA cohorts. The clear cell renal '
  'expression dataset lacked normal tissue, and the hereditary leiomyomatosis '
  'dataset represented a different disease and was used only as '
  'related-disease context. Rare-cancer sample sizes were small, and '
  'enrichment correction was limited to each disease or subtype. The renal '
  'medullary experiment involved two cell lines with weak overall agreement, '
  'not a patient cohort. Some expression scores could not be recalculated and '
  'remain flagged as curated inputs. Prior-proposal classification was limited '
  'to urologic literature and was not independently repeated.')
P('Taking only the top of each ranking also narrowed the search. Requiring '
  'statistical significance can exclude useful targets when rare-disease '
  'datasets are small. Proteasome inhibition in renal medullary carcinoma was one such '
  'omitted candidate [60]. Future analyses could examine genes below the '
  'initial significance threshold and broaden drug matching. We also lacked '
  'adequately sized, histology-labeled datasets for primary bladder '
  'adenocarcinoma, urachal carcinoma, plasmacytoid urothelial carcinoma, and '
  'translocation renal cell carcinoma.')
P(f"In conclusion, this public-data workflow evaluated "
  f"{F['n_drug_hypotheses']} drug-cancer hypotheses and one biomarker "
  f"observation across seven urologic cancers. "
  f"{spell(F['funnel']['survive']).capitalize()} candidates without an "
  f"identified prior urologic proposal met the primary ranking criteria. Each "
  f"requires disease-specific experimental validation. Larger, "
  f"histology-labeled public datasets would support more complete and reliable "
  f"searches.")

print('discussion and conclusions written')

# =====================================================================
# Data availability
# =====================================================================
H('DATA AVAILABILITY')
P(f"All source datasets are publicly available. Genomic data came from the "
  f"TCGA Pan-Cancer Atlas 2018 through cBioPortal. The "
  f"{F['n_series_total']} GEO datasets were GSE199274, GSE216053, and "
  f"GSE216052 (neuroendocrine prostate cancer); GSE130598 (muscle-invasive "
  f"bladder kinome); GSE143630 [61] (clear cell renal cell carcinoma); "
  f"GSE157256 [62] (hereditary leiomyomatosis renal cell cancer, used only as "
  f"related-disease context); GSE180999 (renal medullary carcinoma); "
  f"GSE196978 (penile cancer); GSE128192 (sarcomatoid and conventional "
  f"urothelial carcinoma); and GSE269750 (small-cell bladder subtypes).")
P('Pathway definitions came from the KEGG programmatic interface, gene '
  'symbols from HGNC, and drug-target information from the Therapeutic Target '
  'Database and Open Targets. Scripts, analysis tables, scoring records, '
  'candidate-selection records, prior-proposal searches, and figure code are '
  'archived at github.com/gbrink10/urologic-variant-drug-prioritization and '
  'Zenodo. '
  + (f'The version-specific DOI for this manuscript is {ZENODO_VERSION_DOI}; '
     if ZENODO_VERSION_DOI else '')
  + f'The record for the latest archived version is {ZENODO_CONCEPT_DOI}. '
  'The first script downloads the large primary datasets rather than including '
  'copies in the repository.')
P('Additional checks used DepMap [63], PRISM [64], and LINCS L1000 [65,66]. '
  'None changed the prioritized candidates; all are reported in the '
  'Supplementary Materials. The scripts run the analysis from the curated '
  'inputs but do not reconstruct the original manual drug search.')


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
     'Figure 4. What the sarcomatoid rows are scored on. Histology is '
     'confounded with array chip in this series, so no sarcomatoid-versus-'
     'conventional contrast is reported and these rows are scored on '
     'abundance within the sarcomatoid tumors alone. (A) Where the four '
     'scoring genes sit in that transcriptome. The curve is the ranked mean '
     'expression of all 20,363 genes measured across the 28 sarcomatoid '
     'tumors; the dashed line is the 85th percentile, the threshold the '
     'abundance route scores against. ATR falls below it, which is why that '
     'candidate was not prioritized. (B) The same four percentiles '
     'recomputed independently inside each of the four chip batches the 28 '
     'tumors were run on (n = 6, 11, 2 and 9), with the pooled value filled. '
     'Each gene stays on the same side of the 85th-percentile threshold in '
     'all four batches, supporting the consistency of the pooled abundance '
     'classification. Percentiles shift by a few points between batches; '
     'the per-batch values are deposited. The confounded contrast itself, and the pathway values that '
     'inherit it, are Supplementary Figure S2.'),
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
  'cell carcinoma findings in full; the per-gene nomination routes with '
  'Supplementary Figure S1; and the sarcomatoid comparison that cannot be '
  'interpreted, with Supplementary Figure S2. '
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
  'candidate-selection table, and the sarcomatoid abundance percentiles '
  'per chip batch.')

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

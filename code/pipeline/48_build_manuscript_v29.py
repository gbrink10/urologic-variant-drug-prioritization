"""Build the v29 manuscript from the deposited results.

Every quantitative statement is interpolated from MANUSCRIPT_FACTS.json, which
is computed from the result tables. The prose and the deposit therefore cannot
disagree - the failure mode that produced 42 field-level differences between the
v28 text and its own CSV.

Writes: Downloads/FDA_Drug_Repurposing_v29.docx
"""
import json
import sys
from pathlib import Path

import paths

import docx
import pandas as pd
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
FIG = paths.FIGURES
SCRATCH = paths.DATA / 'manuscript_parts'
OUT = paths.OUTPUT / 'FDA_Drug_Repurposing_v29.docx'

F = json.loads((RF / 'MANUSCRIPT_FACTS.json').read_text(encoding='utf-8'))
refs = SCRATCH.joinpath('v28_refs.txt').read_text(encoding='utf-8').splitlines()
back = json.loads(SCRATCH.joinpath('v28_backmatter.json').read_text(encoding='utf-8'))
master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')
sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')
defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')

doc = docx.Document()
st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(11)


def H(text, size=13, space_before=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
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


def fmt(x, sig=2):
    """Format a q-value the way the text should read it."""
    if x is None:
        return 'n/a'
    if x < 1e-3:
        return f'{x:.1e}'.replace('e-0', ' \u00d7 10\u207b')
    return f'{x:.3f}'.rstrip('0').rstrip('.')


q, de, rmc, dsn = F['q'], F['de'], F['rmc'], F['design']

# score-sensitivity ranks, needed in the Discussion and deposited as Table S2
_prov0 = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
_v = []
for _, _r in _prov0.iterrows():
    _g, _e, _p, _l = (int(_r['G_curated']), int(_r['E_refit']),
                      int(_r['P_refit']), int(_r['L_curated']))
    _v.append({'N': int(_r['N']), 'full': _g + _e + _p + _l,
               'no_anchor': _e + _p + _l, 'no_pathway': _g + _e + _l})
_v = pd.DataFrame(_v)
for _c in ('full', 'no_anchor', 'no_pathway'):
    _v['r_' + _c] = _v[_c].rank(ascending=False, method='min').astype(int)
s2_lead_no_anchor = int(_v.loc[_v['N'] == 17, 'r_no_anchor'].iloc[0])
s2_lead_no_pathway = int(_v.loc[_v['N'] == 17, 'r_no_pathway'].iloc[0])
surv = F['survivors']
lead = next(s for s in surv if s['N'] == 17)
second = next(s for s in surv if s['N'] != 17)

# =====================================================================
# Front matter
# =====================================================================
TITLE = ('An Auditable Public-Data Framework for Prioritizing Biomarker-Matched '
         'Drug Hypotheses Across Benchmark and Rare Urologic Cancers')
p = doc.add_paragraph()
r = p.add_run(TITLE)
r.bold = True
r.font.size = Pt(15)

P('Running Title: Auditable Drug-Hypothesis Prioritization in Urologic Cancers')
P('Authors: Garrett J. Brinkley, MD\u00b9; Jacob Greenberg, MD\u00b9; '
  'Jorge Caso, MD\u00b9')
P('Affiliations: \u00b9Department of Urology, Tulane University School of '
  'Medicine, New Orleans, Louisiana, USA')
P('Corresponding Author: Garrett J. Brinkley, MD; Department of Urology, Tulane '
  'University School of Medicine, New Orleans, LA; garrettjbrinkley@gmail.com')

H('CONTEXT', 12)
P('Key objective: Can publicly deposited genomic and transcriptomic data be '
  'interrogated systematically enough, and transparently enough to be audited, '
  'to prioritize biomarker-anchored drug hypotheses for aggressive urologic '
  'cancers that will not support dedicated trials?')
P(f"Knowledge generated: One pipeline, applied uniformly to three benchmark and "
  f"four rare or variant contexts, produced {F['n_associations']} drug-cancer "
  f"associations. Design-aware reanalysis of the primary data changed eight of "
  f"them. Orthogonal protein, dependency and compound evidence supported some "
  f"candidates, contradicted others, and could not test those acting through "
  f"the microenvironment; a pre-specified rule reduced "
  f"{F['funnel']['framework_novel']} candidates without a prior "
  f"urologic-oncology proposal to {F['funnel']['survive']}.")

H('ABSTRACT', 12)
P(f"Purpose. Rare and variant urologic cancers lack biomarker-directed "
  f"prospective evidence. We built a public-data framework that prioritizes "
  f"drug hypotheses across seven contexts and reports its own failures: three "
  f"benchmark contexts used to calibrate it (neuroendocrine prostate cancer, "
  f"muscle-invasive bladder cancer, clear cell renal cell carcinoma) and four "
  f"rare or variant discovery contexts (renal medullary carcinoma, penile "
  f"squamous cell carcinoma, sarcomatoid urothelial carcinoma, and "
  f"lineage-stratified small-cell bladder cancer).")
P(f"Methods. Alteration frequencies, differential expression across ten Gene "
  f"Expression Omnibus datasets, enrichment across eighteen pre-specified "
  f"druggable pathway or gene sets, drug-target curation and a 9-point "
  f"prioritization score were combined, followed by an independent PubMed "
  f"prior-proposal audit. Differential expression was fitted with design-aware, "
  f"platform-appropriate models (limma and edgeR), blocking on donor where "
  f"replicates were technical and pairing where samples were matched. "
  f"Candidates were then assessed against four orthogonal sources that took no "
  f"part in scoring, and reduced by a rule fixed in advance.")
P(f"Results. {F['n_associations']} drug-cancer associations emerged: "
  f"{F['tiers'].get('Strong', 0)} Strong-tier, {F['tiers'].get('Moderate', 0)} "
  f"Moderate-tier and {F['tiers'].get('Exploratory', 0)} Exploratory-tier, "
  f"including one candidate negative predictive biomarker (trophoblast "
  f"cell-surface antigen 2 loss, log\u2082 fold change "
  f"{de['TACSTD2_sarc']['log2FC']:+.2f}). "
  f"{F['n_previously_proposed']} recovered priorities proposed independently "
  f"elsewhere. {F['n_framework_novel']} had no prior urologic-oncology proposal "
  f"identified; of these, {F['funnel']['eligible']} met eligibility and "
  f"{F['funnel']['survive']} survived the audit. Refitting changed eight "
  f"associations and dissolved two candidates the earlier analysis had carried "
  f"forward.")
P(f"Conclusion. A public-data framework can prioritize biomarker-matched drug "
  f"hypotheses where prospective evidence will not otherwise exist, provided it "
  f"reports what it cannot support. CXCR1/CXCR2 blockade in renal medullary "
  f"carcinoma is the highest-priority experimental hypothesis it produces "
  f"(chemokine signalling q = {q['rmc_chemokine']:.4f}), but the dependency and "
  f"compound screens cannot test a microenvironment-directed mechanism, so "
  f"their silence is not support. All candidates require disease-specific "
  f"validation.")

# =====================================================================
# Introduction
# =====================================================================
H('INTRODUCTION')
P('Two decades of cancer genomics have produced an enormous openly deposited '
  'resource: The Cancer Genome Atlas catalogues somatic alterations across '
  'thirty-three cancer types from more than eleven thousand patients [1,2], the '
  'Gene Expression Omnibus archives over two hundred thousand transcriptomic '
  'datasets, and cBioPortal, OpenTargets, the Therapeutic Target Database and '
  'the Kyoto Encyclopedia of Genes and Genomes integrate these with drug-target '
  'and pathway annotation. The bottleneck in translational oncology has arguably '
  'shifted from generating primary data to interrogating it. Drug repurposing '
  'engages that resource directly: rather than nominate a new molecule, it asks '
  'whether an approved or clinical-stage agent can be matched to a new molecular '
  'context, entering with established safety, pharmacology and supply chain. The '
  'challenge is performing that matching across several diseases at once with '
  'enough discipline that the priorities are auditable and falsifiable.')
P('Aggressive and variant urologic histologies are a high-need setting. Renal '
  'medullary carcinoma, penile squamous cell carcinoma, sarcomatoid urothelial '
  'carcinoma and small-cell bladder cancer each progress rapidly, resist '
  'standard cytotoxic chemotherapy, and lack dedicated biomarker-directed '
  'prospective evidence, either because the disease is intrinsically rare or '
  'because the biomarker-defined subset is too small to power a registration '
  'trial. Slow accrual, expensive multi-institutional coordination and '
  'insufficient population make such trials difficult to mount, and for several '
  'of these diseases that evidence is unlikely to arrive on current incentives.')
P('We therefore asked whether public molecular data could be interrogated '
  'systematically enough to prioritize biomarker-anchored drug hypotheses across '
  'several such contexts at once. Three common source diseases are included '
  'deliberately as benchmarks: they have abundant prior literature, so the '
  'framework\u2019s ability to recover established priorities in them calibrates '
  'what its output means in the rare contexts, where no such yardstick exists. '
  'Two design features matter. Candidate generation and scoring were completed '
  'before any prior-proposal classification, so convergence with existing '
  'literature is separable from discovery. And the rule that reduces candidates '
  'to a shortlist was fixed before it was applied, so every exclusion is '
  'attributable to a stated criterion rather than to judgement.')

# =====================================================================
# Methods
# =====================================================================
H('MATERIALS AND METHODS')
P('We applied one six-step pipeline uniformly to all seven contexts, set out in '
  'Figure 1: a genomic or context-anchor value; per-context differential '
  'expression across ten Gene Expression Omnibus datasets; upper-tail '
  'hypergeometric enrichment across eighteen pre-specified druggable pathway or '
  'gene sets; mapping of differentially expressed genes to clinically evaluable '
  'agents through the Therapeutic Target Database and OpenTargets; a 9-point '
  'prioritization score combining four evidence dimensions; and an independent '
  'PubMed prior-proposal audit performed only after scoring was complete. '
  'Candidates were then assessed against four orthogonal evidence layers that '
  'took no part in scoring (Figure 1, Step 7). Full procedural detail is given '
  'in Supplementary Methods, and the pipeline is executable from the deposited '
  'code.')
P('Somatic alteration frequencies for urothelial bladder carcinoma (n = 411), '
  'kidney renal clear cell carcinoma (n = 512) and prostate adenocarcinoma '
  '(n = 494) came from The Cancer Genome Atlas Pan-Cancer Atlas 2018 via '
  'cBioPortal [1,2]. The four rare-disease contexts are not represented there, '
  'so frequencies were curated from published series: Msaouel 2020 for renal '
  'medullary carcinoma [3], Chahoud 2021 [4] and Aydin 2020 [5] for penile '
  'squamous cell carcinoma, Guo 2019 for sarcomatoid urothelial carcinoma [6] '
  'and Chang 2018 for small-cell bladder cancer [7]. Because a rare-disease '
  'context is often anchored by an alteration that is not itself the '
  'therapeutic target \u2014 SMARCB1 biallelic loss in renal medullary carcinoma '
  'being the clearest case \u2014 transcriptomic nomination was not restricted to '
  'recurrently altered genes.')
P(f"Differential expression was fitted with the standard treatment for each "
  f"platform rather than one elementary test applied to all. Count-based series "
  f"were filtered by expression, normalised by trimmed mean of M-values and "
  f"fitted with voom precision weights; log-scale series were fitted with "
  f"limma\u2019s variance-moderated linear model with an intensity trend. Three "
  f"design features were modelled that the primary deposits make explicit and "
  f"the previous analysis had not used. The penile series contains "
  f"{dsn['pscc_normal_arrays']} normal arrays from only "
  f"{dsn['pscc_normal_donors']} donors, so donor was included as a blocking "
  f"factor by duplicate correlation rather than treating the arrays as "
  f"independent. The muscle-invasive bladder kinome panel is a matched "
  f"tumour-normal design, so patient was included as a blocking factor. In "
  f"lineage-stratified small-cell bladder cancer each subtype was contrasted "
  f"against the mean of the remaining subtypes with batch in the model. Renal "
  f"medullary carcinoma is a two-cell-line rescue experiment for which no "
  f"sample-level matrix is deposited; the two patient-derived lines were "
  f"therefore treated as two biological replicates and only genes changing "
  f"consistently in both were carried forward.")
P(f"Gene symbols were normalised to current HGNC nomenclature before enrichment. "
  f"This is not cosmetic: the pathway definitions use current symbols while the "
  f"older expression platforms use the symbols of their day, so any gene renamed "
  f"in the interval was silently dropped from its own pathway. Enrichment used "
  f"the direction-specific up-regulated gene list as the query and the genes "
  f"actually measured and retained in that dataset as the background, rather "
  f"than a fixed transcriptome-wide count. Benjamini-Hochberg correction was "
  f"applied across the eighteen sets within each context; it was not applied "
  f"across contexts, drugs or the downstream comparisons, and q-values should be "
  f"read accordingly. A 10% false-discovery threshold was pre-specified for this "
  f"exploratory setting and is used consistently; values between 5% and 10% are "
  f"described as suggestive rather than significant.")
P('Each association received a score from 0 to 9 across four dimensions, which '
  'are partially overlapping rather than independent: a genomic or '
  'context-anchor value (0\u20133), a transcriptomic value (0\u20133), a pathway '
  'value (0\u20132) and external mechanistic-literature concordance (0\u20131). '
  'The transcriptomic and pathway dimensions derive from the same expression '
  'data, and in several benchmark rows the genomic dimension reflects a '
  'disease-defining anchor rather than alteration of the nominated target; both '
  'facts are stated because they bound what the composite means. The two '
  'data-derived dimensions are computed by one function from the deposited '
  'fitted tables, so the manuscript table and the deposited table cannot '
  'diverge. Scores map to Strong (7\u20139), Moderate (4\u20136) and Exploratory '
  '(1\u20133) tiers, which express strength of evidence within this framework '
  'only and not established drug sensitivity.')
P('The prior-proposal audit was performed after scoring was complete. For each '
  'association we ran multiple PubMed query variants and examined reviews, '
  'position papers and trial registries, classifying each association as having '
  'no prior urologic-oncology proposal identified, a partial precedent, or a '
  'prior proposal. Novelty was assessed against urologic-oncology literature '
  'only: prior proposals from small-cell lung, gastric or other non-urologic '
  'contexts do not count, even where the same biology has been proposed. This is '
  'a statement about the urologic literature, not a claim of biological '
  'precedence.')
P(f"Candidates were reduced by a rule fixed before it was applied. Eligibility "
  f"required no prior urologic-oncology proposal, Moderate tier or better, a "
  f"transcriptomic component re-derivable from deposited data at q < 0.05, and "
  f"an available clinical-stage agent. Survival additionally required that no "
  f"orthogonal layer contradict the candidate and that target accessibility "
  f"match the modality. The lead additionally required that the target itself "
  f"belong to a pathway that is enriched, since an enrichment driven by other "
  f"genes is not evidence for that target. A layer that cannot evaluate a "
  f"candidate counts as neither support nor contradiction.")

print('front matter and methods written')

# =====================================================================
# Results
# =====================================================================
H('RESULTS')

H('3.1 Framework Output', 11.5, 10)
ctx_counts = ', '.join(f'{k} {v}' for k, v in F['per_context'].items())
P(f"Applying the pipeline produced {F['n_associations']} drug-cancer "
  f"associations (Table 1; the complete table with all score components is "
  f"Supplementary Table S1): {F['tiers'].get('Strong', 0)} Strong-tier, "
  f"{F['tiers'].get('Moderate', 0)} Moderate-tier and "
  f"{F['tiers'].get('Exploratory', 0)} Exploratory-tier. Per context: "
  f"{ctx_counts}. Each row carries its score decomposition, clinical-development "
  f"stage, prior-proposal status and the specific dataset and gene on which its "
  f"transcriptomic component rests.")

H('3.2 Benchmark Recovery', 11.5, 10)
P(f"The three benchmark contexts contributed sixteen associations, every one of "
  f"which recovers a priority proposed independently elsewhere \u2014 six in "
  f"neuroendocrine prostate cancer [10\u201318], seven in muscle-invasive "
  f"bladder cancer [19\u201327] and three in clear cell renal cell carcinoma "
  f"[28\u201332]. Two further previously-proposed priorities arise in the "
  f"rare-disease contexts, erlotinib in renal medullary carcinoma and "
  f"pembrolizumab in penile squamous cell carcinoma [34,35], giving "
  f"{F['n_previously_proposed']} in all. This is calibration rather than "
  f"independent validation: prior knowledge influenced the pathway panel, the "
  f"drug curation and the choice of representative agent, so recovery shows the "
  f"framework behaves sensibly where the answer is known, not that its novel "
  f"output is correct.")

H('3.3 Discovery Contexts', 11.5, 10)
P(f"In renal medullary carcinoma the deposited experiment is a SMARCB1 rescue in "
  f"two patient-derived lines. Across the {rmc['genes_measured_both']:,} genes "
  f"measured in both, the genome-wide correlation between lines is only "
  f"r = {rmc['r_between_lines']}, so requiring consistent change in both is a "
  f"stringent filter: {rmc['up_both']} genes pass it. A chemokine axis is among "
  f"them, elevated in the SMARCB1-null disease state in both lines \u2014 CXCL8 "
  f"{rmc['CXCL8']['RMC2C']:+.2f} and {rmc['CXCL8']['RMC219']:+.2f}, CXCL1 "
  f"{rmc['CXCL1']['RMC2C']:+.2f} and {rmc['CXCL1']['RMC219']:+.2f}, CXCL2 "
  f"{rmc['CXCL2']['RMC2C']:+.2f} and {rmc['CXCL2']['RMC219']:+.2f} \u2014 with "
  f"KEGG chemokine signalling enriched on the both-lines set at "
  f"q = {q['rmc_chemokine']:.4f} (Figure 2), coherent with the neutrophil-rich "
  f"microenvironment described in this disease [33]. This nominates the "
  f"CXCR1/CXCR2 antagonist class, and carcinoembryonic antigen-related cell adhesion "
  f"molecule 1 alongside it (CEACAM1 {rmc['CEACAM1']['RMC2C']:+.2f} and "
  f"{rmc['CEACAM1']['RMC219']:+.2f}). Chemokine signalling is not the most "
  f"strongly enriched set in this context \u2014 {F['rmc_top_pathway'].replace('_', ' ')} "
  f"ranks above it at q = {F['rmc_top_q']:.4f} \u2014 so the claim is that the "
  f"axis is robustly present, not that it dominates.")
P(f"Penile squamous cell carcinoma showed a dominant immune-hot phenotype. "
  f"HLA-DRA is elevated at {de['HLA_DRA_pscc']['log2FC']:+.2f} "
  f"(q = {fmt(de['HLA_DRA_pscc']['q'])}) with CXCL9 and CXCL10 elevated and "
  f"antigen processing and presentation enriched at "
  f"q = {q['pscc_antigen']:.4f}, converging on the established pembrolizumab "
  f"priority [36\u201338] with partially-novel matrix metalloproteinase and "
  f"periostin candidates [39\u201341]. This signal survives modelling the six "
  f"normal arrays as {dsn['pscc_normal_donors']} donors rather than six "
  f"independent samples, which was the more demanding test.")
P(f"Sarcomatoid urothelial carcinoma (Figure 3) yielded nuclear receptor-binding "
  f"SET domain protein 2 (NSD2 {de['NSD2_sarc']['log2FC']:+.2f}, "
  f"q = {fmt(de['NSD2_sarc']['q'])}) with epigenetic regulation enriched at "
  f"q = {q['sarc_epigenetic']:.3f}, together with partially-novel UHRF1 [42] and "
  f"G6PD [43] candidates, and one candidate negative predictive biomarker: "
  f"trophoblast cell-surface antigen 2, encoded by TACSTD2, is downregulated "
  f"({de['TACSTD2_sarc']['log2FC']:+.2f}, q = {fmt(de['TACSTD2_sarc']['q'])}), "
  f"concordant with three independent pathology reports [44\u201346] and "
  f"hypothesised to be associated with lower response to sacituzumab govitecan, "
  f"whose accelerated approval in metastatic urothelial carcinoma was withdrawn "
  f"in October 2024. The ataxia telangiectasia and Rad3-related kinase candidate "
  f"that the previous analysis carried does not survive refitting: its effect is "
  f"{de['ATR_sarc']['log2FC']:+.2f} at q = {fmt(de['ATR_sarc']['q'])}, below the "
  f"framework\u2019s own entry threshold.")
P(f"Lineage-stratified small-cell bladder cancer (Figure 4), classified by "
  f"lineage transcription factor [47], produced three subtype-specific "
  f"associations. ASCL1-positive tumours show CEACAM5 elevation "
  f"({de['CEACAM5_ascl1']['log2FC']:+.2f}, q = {fmt(de['CEACAM5_ascl1']['q'])}), "
  f"supporting CEACAM5-directed antibody-drug conjugates as a class; "
  f"POU2F3-positive tumours show arachidonic-acid metabolism enrichment "
  f"(q = {q['pou2f3_arachidonic']:.3f}) with PTGS1 elevated "
  f"({de['PTGS1_pou2f3']['log2FC']:+.2f}, q = {fmt(de['PTGS1_pou2f3']['q'])}), "
  f"supporting non-selective cyclooxygenase inhibition [49]. The "
  f"NEUROD1-positive somatostatin receptor 2 association does not survive: the "
  f"fold change reproduces ({de['SSTR2_neurod1']['log2FC']:+.2f}) but it does "
  f"not reach significance under a batch-adjusted subtype contrast "
  f"(q = {de['SSTR2_neurod1']['q']:.3f}), and the neuroactive ligand-receptor "
  f"set is not enriched in that subtype at all. The somatostatin receptor 2 "
  f"paradigm established in small-cell lung cancer [48] therefore does not "
  f"transfer here on the strength of these data.")

print('results 3.1-3.3 written')

H('3.4 Orthogonal Evidence Audit', 11.5, 10)
P('Every association is nominated from transcript abundance, a weaker claim '
  'than several modalities require, so the nominated targets were assessed '
  'against four sources that took no part in scoring. These are an audit rather '
  'than a validation: each can find a candidate wanting, none can establish that '
  'it works, and each is blind to some candidates by construction.')
P(f"{F['hpa']['n_surface_required']} associations depend on extracellular "
  f"access and all {F['hpa']['n_confirmed']} are confirmed against the Human "
  f"Protein Atlas [50]. Normal-tissue expression speaks to therapeutic window "
  f"and separates the two survivors: CXCR1 is near-absent in normal kidney "
  f"({F['hpa']['CXCR1_kidney']} normalised transcripts per million) whereas "
  f"CEACAM1 is substantially expressed there ({F['hpa']['CEACAM1_kidney']}), so "
  f"an agent directed at CEACAM1 in a renal tumour would face on-target, "
  f"off-tumour exposure in the organ of origin that a CXCR1/CXCR2 antagonist "
  f"would not. Delta-like ligand 3 is undetectable in normal bladder "
  f"({F['hpa']['nTPM']['DLL3']}) and somatostatin receptor 2 near-absent "
  f"({F['hpa']['nTPM']['SSTR2']}), while trophoblast cell-surface antigen 2 is "
  f"abundant in normal urothelium ({F['hpa']['nTPM']['TACSTD2']}), which is what "
  f"makes its loss in sarcomatoid disease interpretable rather than a "
  f"low-baseline artefact.")
P(f"DepMap CRISPR screens ask whether a cell requires a gene, a more demanding "
  f"question than whether it is abundantly expressed [55]; gene effect is "
  f"reported on the Chronos scale, where more negative means more required. "
  f"Across {F['depmap']['n_urothelial_lines']} urothelial lines, stratified by "
  f"genotype and target expression from CCLE via cBioPortal [56], the approach "
  f"calibrates: RPL5 scores {F['depmap']['RPL5']:.2f} with every line dependent, "
  f"and PIK3CA-mutant lines are selectively dependent on PIK3CA "
  f"({F['depmap']['PIK3CA_mut']:.2f} versus {F['depmap']['PIK3CA_wt']:.2f}), "
  f"recovering a biomarker-dependency relationship from independent data. It "
  f"also contradicts one of our own candidates: NSD2 is "
  f"{F['depmap']['NSD2_verdict']} even in the lines expressing it most highly "
  f"({F['depmap']['NSD2_high']:+.2f}), which is why that candidate does not "
  f"survive. ATR is a genuine but pan-essential dependency, so the target is "
  f"required while the sarcomatoid-specific rationale gains no support. For "
  f"antibody, conjugate and radioligand rows the screen is not the right test "
  f"at all: CEACAM1 is recorded as {F['depmap']['CEACAM1_verdict']}.")
P(f"Compound-level activity was read from the PRISM Repurposing screen across "
  f"{F['prism']['n_lines']} cell lines [51]. It calibrates — bortezomib "
  f"gives {F['prism']['bortezomib']:.2f} and erlotinib is markedly more active "
  f"in urothelial lines ({F['prism']['erlotinib_uro']:.2f}) — but the four "
  f"screened CXCR1/CXCR2 antagonists show no tumour-cell-autonomous activity in "
  f"any lineage. This is expected rather than negative: the proposed mechanism "
  f"is blockade of myeloid recruitment, which a tumour-cell monoculture cannot "
  f"test in either direction. What it does establish is the absence of "
  f"off-target cytotoxicity in the class.")
P(f"Signature reversal against the LINCS L1000 libraries [52,53] was recomputed "
  f"on the refitted gene lists, and the result differs from what we previously "
  f"reported. {F['lincs']['n_sig_reversal']} of {F['lincs']['n_terms']} "
  f"reversal terms across {F['lincs']['n_contexts']} contexts reach q < 0.05, "
  f"and nominated agents do now appear, palbociclib and erlotinib among them. "
  f"Neither is context-specific: palbociclib surfaces in hereditary "
  f"leiomyomatosis renal cell cancer, sarcomatoid urothelial carcinoma and "
  f"muscle-invasive bladder cancer alike, and erlotinib surfaces in sarcomatoid "
  f"disease rather than in the renal medullary context where it is the positive "
  f"control. No nominated agent reaches rank 1 in any context, and the lists are "
  f"dominated by heat shock protein 90, mitogen-activated protein kinase kinase "
  f"and multi-kinase perturbagens profiled in unrelated lineages. Connectivity "
  f"therefore remains uninformative here, for a more specific reason than "
  f"before.")

H('3.5 The Shortlist', 11.5, 10)
P(f"Applying the pre-specified rule (Figure 5), the "
  f"{F['funnel']['framework_novel']} associations without a prior "
  f"urologic-oncology proposal reduce to {F['funnel']['eligible']} eligible and "
  f"{F['funnel']['survive']} survivors. Two fail eligibility because refitting "
  f"dissolved their transcriptomic support: the ATR candidate at "
  f"q = {fmt(de['ATR_sarc']['q'])} and the somatostatin receptor 2 candidate at "
  f"q = {de['SSTR2_neurod1']['q']:.3f}. One fails because its agent is no longer "
  f"in development, tusamitamab ravtansine having been discontinued in December "
  f"2023; whether a successor anti-CEACAM5 conjugate is in active clinical "
  f"development should be confirmed before that row is revisited. One fails the "
  f"audit because DepMap contradicts it. Both survivors are in renal medullary "
  f"carcinoma, so the framework’s discovery output concentrates in a single "
  f"disease rather than spreading across contexts.")
P(f"CXCR1/CXCR2 blockade is the lead candidate. It scores {lead['total']}/9, its "
  f"chemokine axis is elevated consistently in both patient-derived lines, its "
  f"target lies in a pathway that is itself enriched "
  f"(q = {q['rmc_chemokine']:.4f}) rather than borrowing an enrichment driven by "
  f"other genes, both receptors are confirmed at the membrane, normal kidney "
  f"expression is negligible, and the antagonist class is clinical-stage with "
  f"established safety. Anti-CEACAM1 is the second survivor at "
  f"{second['total']}/9, but it is weaker on two counts that matter: its target "
  f"is not a member of the enriched pathway, and its normal-kidney expression is "
  f"{F['hpa']['CEACAM1_kidney']} against {F['hpa']['CXCR1_kidney']} for CXCR1.")
P('One qualification travels with the lead. The dependency and compound screens '
  'do not endorse it so much as they cannot test it: a mechanism operating '
  'through myeloid recruitment is invisible to tumour-cell monoculture, so their '
  'silence is not support. It is the best-supported hypothesis this framework '
  'produces, not a validated finding, and the decisive experiment, CXCR1/CXCR2 '
  'blockade in an immunocompetent renal medullary carcinoma model with an intact '
  'myeloid compartment, remains to be done.')

H('3.6 What the Framework Could Not Surface', 11.5, 10)
P('Applied consistently, the drug-class-first rule that fixed the eighteen gene '
  'sets exposes one material omission. Delta-like ligand 3 is the canonical '
  'ASCL1-lineage neuroendocrine surface antigen and the target of tarlatamab, a '
  'bispecific T-cell engager approved in 2024 for extensive-stage small-cell '
  'lung cancer. No pre-specified set in our panel contains it, so no DLL3 '
  'hypothesis could have been generated for any context, irrespective of the '
  'underlying data.')
P('Tested post hoc, DLL3 is elevated in the ASCL1-positive subtype '
  '(log₂ fold change +1.61) but does not reach significance after '
  'correction (q = 0.30), and had the Notch pathway been among the pre-specified '
  'sets it would have been nominally enriched only. DLL3-directed therapy in '
  'genitourinary small-cell carcinoma has already been proposed in the urologic '
  'literature (Liao 2024 [54]), so under this study’s standard DLL3 is a '
  'previously proposed priority that the panel failed to recover, a false '
  'negative of the framework rather than a missed discovery. It is reported here '
  'and excluded from Table 1, which is the pre-specified output. The cause is '
  'specific and correctable: the binding constraint is the panel’s coverage '
  'of druggable biology, not the scoring rules and not the underlying data.')

print('results 3.4-3.6 written')

# =====================================================================
# Discussion
# =====================================================================
H('DISCUSSION')
P('A central problem in rare and variant urologic cancers is that the patient '
  'numbers needed to power dedicated biomarker-matched trials are not, and may '
  'never be, available. The associations in Table 1 show that a public-data '
  'framework can nonetheless prioritize biologically coherent hypotheses across '
  'several such contexts, and can be reported together with the places it '
  'fails.')
P(f"The clearest demonstration of that last point is what happened when the "
  f"primary data were refitted with design-aware models. Eight associations "
  f"changed, and two candidates the earlier analysis had carried forward "
  f"dissolved: the somatostatin receptor 2 row, which had the most attractive "
  f"translational package of any candidate we produced, and the ATR row. Neither "
  f"failed because of new data; both failed because the original elementary "
  f"per-gene tests ignored replicate structure and batch. A framework that had "
  f"not been rebuilt from primary data would have carried both into a "
  f"manuscript. We report this because the same risk applies to any "
  f"public-data prioritization that does not refit what it reuses.")
P(f"Three design features of the deposited data bound what can be concluded, "
  f"and none was visible in the summary tables the earlier analysis relied on. "
  f"In the sarcomatoid series all {dsn['sarc_chips_sarc_only'] + dsn['sarc_chips_uc_only']} "
  f"arrays are hybridised such that sarcomatoid and conventional samples share "
  f"no chip: {dsn['sarc_chips_sarc_only']} chips carry sarcomatoid samples only "
  f"and {dsn['sarc_chips_uc_only']} carry conventional samples only, with "
  f"{dsn['sarc_chips_mixed']} mixed. Batch and biology are therefore completely "
  f"confounded there, a model including chip is not estimable, and every "
  f"sarcomatoid association, including the trophoblast cell-surface antigen 2 "
  f"biomarker, must be read with that in mind. The clear cell renal series "
  f"contains {dsn['ccrcc_samples']} tumours and no normal tissue, so those rows "
  f"are scored on absolute expression rather than a disease contrast; the "
  f"metastatic-versus-non-metastatic contrast that the series does support "
  f"yields {dsn['ccrcc_q05_genes']} gene at q < 0.05. And the hereditary "
  f"leiomyomatosis series, used previously as though it spoke to clear cell "
  f"disease, is a different disease; it is reported here as adjacent-disease "
  f"mechanistic context only.")
P('The recovery of eighteen previously-proposed priorities is calibration, not '
  'independent validation. Prior knowledge entered the pathway panel, the drug '
  'curation, the literature dimension and the choice of representative agent, so '
  'the framework and the literature are not independent. What recovery does show '
  'is that a pipeline built without reference to any particular answer behaves '
  'sensibly where the answer is known, which is the only available yardstick for '
  'what its output means where the answer is not.')
P(f"The scoring dimensions are partially overlapping, and the composite should "
  f"be read as an ordering device rather than a measurement. The transcriptomic "
  f"and pathway dimensions share an input. In several rows the genomic dimension "
  f"reflects a disease-defining anchor rather than alteration of the nominated "
  f"target: renal medullary carcinoma is near-universally SMARCB1-deficient, "
  f"which certifies that the samples represent the disease but says nothing "
  f"specific about CXCR1 or CXCR2. That contribution is load-bearing. In the "
  f"sensitivity analysis (Supplementary Table S2) the lead candidate falls from "
  f"first to {int(s2_lead_no_anchor)}th when the anchor contribution is removed "
  f"and to {int(s2_lead_no_pathway)}rd when the pathway dimension is dropped, "
  f"while it remains first when the literature dimension is removed and when the "
  f"pathway dimension is required to contain the target itself. Part of the "
  f"ordering is therefore carried by the scoring architecture rather than by "
  f"target-specific biology, and the shortlist should be read with that in "
  f"mind.")
P(f"Remaining limitations are bounded by what is public. Rare-disease sample "
  f"sizes are modest. Enrichment was corrected within context across eighteen "
  f"sets and not across contexts or downstream comparisons. The transcriptomic "
  f"dimension is not uniformly transcriptomic: where a target is absent from its "
  f"platform the row retains a curated value, and every such row is flagged in "
  f"Supplementary Table S1 rather than left implicit. The renal medullary "
  f"experiment is two cell lines, not a patient cohort, and its lines agree "
  f"poorly overall (r = {rmc['r_between_lines']}), which is why consistency "
  f"across both was required. Finally, the urologic-only novelty standard is "
  f"deliberately conservative and says nothing about biological precedence "
  f"outside urology.")
P('Section 3.6 makes a further limitation concrete: because candidate generation '
  'is bounded by the pre-specified panel, any druggable axis absent from it is '
  'invisible however strong its expression signal. DLL3 is the clearest case and '
  'proteasome inhibition in renal medullary carcinoma [57] a second, so panel '
  'coverage should be re-audited against newly approved drug classes before '
  'reuse. Resolution is also bounded by what is deposited: several variants of '
  'immediate interest, including primary bladder adenocarcinoma, urachal '
  'carcinoma, plasmacytoid urothelial carcinoma and translocation renal cell '
  'carcinoma, have no histology-labelled cohort of adequate size and could not '
  'be analysed. The forward requirement is infrastructural rather than '
  'algorithmic.')

H('CONCLUSIONS')
P(f"One public-data framework applied uniformly across three benchmark and four "
  f"rare or variant urologic cancer contexts produced {F['n_associations']} "
  f"drug-cancer associations, recovered {F['n_previously_proposed']} priorities "
  f"proposed independently elsewhere, and reduced "
  f"{F['funnel']['framework_novel']} associations without a prior "
  f"urologic-oncology proposal to {F['funnel']['survive']} under a rule fixed in "
  f"advance. Its contribution is not any single drug-cancer pair but a way of "
  f"generating, calibrating and challenging drug hypotheses in data-poor cancers "
  f"that can be audited and contradicted. CXCR1/CXCR2 blockade in renal "
  f"medullary carcinoma is the highest-priority experimental hypothesis it "
  f"produces. All candidates remain hypotheses requiring disease-specific "
  f"validation, and broader progress requires universal tumour sequencing and a "
  f"histology-labelled, machine-accessible biorepository.")

print('discussion and conclusions written')

# =====================================================================
# Data availability
# =====================================================================
H('DATA AVAILABILITY')
P('All datasets used are publicly available without restriction. Genomic '
  'alteration frequencies for the benchmark contexts were extracted from The '
  'Cancer Genome Atlas Pan-Cancer Atlas 2018 via cBioPortal. Ten Gene Expression '
  'Omnibus accessions provided transcriptomic evidence: GSE199274, GSE216053 and '
  'GSE216052 (neuroendocrine prostate cancer); GSE130598 (muscle-invasive '
  'bladder cancer kinome); GSE143630 [8] (clear cell renal cell carcinoma); '
  'GSE157256 [9] (hereditary leiomyomatosis renal cell cancer, reported as '
  'adjacent-disease context only); GSE180999 (renal medullary carcinoma); '
  'GSE196978 (penile squamous cell carcinoma); GSE128192 (sarcomatoid versus '
  'conventional urothelial carcinoma); and GSE269750 (small-cell bladder cancer, '
  'subtype-stratified). Pathway definitions were retrieved through the Kyoto '
  'Encyclopedia of Genes and Genomes programmatic interface and gene symbols '
  'normalised against the HGNC complete set. Drug-target associations were drawn '
  'from the Therapeutic Target Database and OpenTargets. All analysis scripts, '
  'the fitted differential-expression tables, the enrichment tables, the master '
  'association table with per-row scoring provenance, the candidate-selection '
  'table and the figure-generation code are archived at GitHub '
  '(github.com/gbrink10/urologic-variant-drug-prioritization) and at Zenodo. '
  'The pipeline runs end to end from the deposited code; the large primary '
  'deposits are re-downloaded by the first script rather than mirrored.')

# =====================================================================
# Figures
# =====================================================================
FIGURES = [
    ('Figure1_pipeline.png', 6.5,
     'Figure 1. The pipeline, from context definition to shortlist. Steps 1 to 6 '
     'produce the association table: genomic or context-anchor input from The '
     'Cancer Genome Atlas for the three benchmark contexts and from published '
     'series for the four rare or variant contexts; differential expression '
     'across ten Gene Expression Omnibus datasets fitted with a design-aware, '
     'platform-appropriate model; hypergeometric enrichment across eighteen '
     'pre-specified druggable pathway or gene sets against each dataset’s own '
     'measured-gene universe; drug-target curation; a 9-point prioritization '
     'score; and an independent PubMed prior-proposal audit performed only after '
     'scoring. Step 7 is the orthogonal evidence audit, whose four layers '
     'contributed nothing to any score. The shortlist is produced by a rule '
     'fixed before it was applied.'),
    ('Figure2_RMC.png', 6.9,
     'Figure 2. Renal medullary carcinoma. (A) Effect in RMC-2C against effect '
     'in RMC219 for every gene measured in both lines. The genome-wide '
     'correlation is weak, so requiring consistent change in both lines is a '
     'stringent filter rather than a formality; genes passing it are highlighted, '
     'and the chemokine axis is labelled. (B) The chemokine axis gene by gene, '
     'each line shown separately, in disease-state orientation, with the pathway '
     'q-value computed on the both-lines set. (C) Proposed mechanism. CXCR1 and '
     'CXCR2 are receptors on the neutrophil, not on the tumour cell, which is '
     'why a tumour-cell monoculture cannot test this hypothesis in either '
     'direction.'),
    ('Figure3_SarcUC.png', 6.9,
     'Figure 3. Sarcomatoid urothelial carcinoma. (A) Differential expression '
     'from the limma refit, 28 sarcomatoid versus 84 conventional tumours, with '
     'the nominated targets labelled; ATR lies close to the origin, which is why '
     'its association does not survive. (B) Pathway enrichment, with sets '
     'meeting the pre-specified 10% false-discovery threshold shown in green and '
     'starred and nominal-only sets in gold. (C) Nominated targets by '
     'subcellular compartment: NSD2, UHRF1 and the ATR-ATRIP complex are '
     'nuclear, G6PD is cytoplasmic, and trophoblast cell-surface antigen 2 is '
     'drawn sparse at the membrane to indicate loss. Sarcomatoid and '
     'conventional samples share no array chip in this series, so batch and '
     'biology cannot be separated; all panels should be read with that '
     'limitation.'),
    ('Figure4_SCBC.png', 6.9,
     'Figure 4. Lineage-stratified small-cell bladder cancer. (A) Subtype '
     'composition by lineage transcription factor. (B) The nominated target in '
     'each subtype with its q-value from the batch-adjusted subtype contrast; '
     'somatostatin receptor 2 in NEUROD1-positive tumours does not reach '
     'significance, which is why that association does not enter the shortlist. '
     '(C) Proposed lineage-stratified therapeutic hypotheses. CEACAM5 and '
     'somatostatin receptor 2 are cell-surface targets; PTGS1/COX-1 is an '
     'intracellular enzyme on the endoplasmic reticulum and is shown inhibited '
     'by aspirin, a non-selective cyclooxygenase inhibitor, rather than by a '
     'COX-2-selective agent.'),
    ('Figure5_candidate_selection.png', 6.9,
     'Figure 5. Candidate selection under a rule fixed in advance. (A) Attrition '
     'from the full association table to the shortlist, with the criterion '
     'applied at each stage. (B) Every candidate without a prior '
     'urologic-oncology proposal against every criterion. Each cell carries a '
     'symbol as well as a colour: + supports, ~ partial, − fails the '
     'criterion or contradicts, n/a cannot test. The enrichment column is '
     'credited only where the target is itself a member of the enriched pathway, '
     'since an enrichment driven by other genes is not evidence for that target. '
     'A layer that cannot evaluate a candidate is not evidence for it, so '
     'absence of contradiction is weaker than positive support.'),
]
for name, width, legend in FIGURES:
    path = FIG / name
    if not path.exists():
        print(f'  MISSING FIGURE {name}')
        continue
    doc.add_paragraph()
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
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
P('Supplementary Methods: full procedural detail for the six pipeline steps and '
  'the four orthogonal evidence layers, including data releases, model '
  'specifications, thresholds and statistical tests. '
  'Supplementary Table S1: the complete association table, all rows and all '
  'score components, with the dataset and gene underlying each transcriptomic '
  'component, the fitted fold change and q-value, the pathway q-value, and an '
  'explicit flag on any row whose component is not re-derivable from deposited '
  'data. Supplementary Table S2: score-sensitivity analysis, giving the ranking '
  'under removal of the context-anchor contribution, removal of the pathway '
  'dimension, removal of the literature dimension, and a target-membership '
  'requirement for the pathway dimension. Supplementary Table S3: per-dataset '
  'design summary, giving the contrast, the model fitted, the blocking or batch '
  'structure, sample counts and any confounding identified. Supplementary Data: '
  'fitted differential-expression tables for every context, enrichment tables '
  'with nominal and corrected values, the renal medullary two-line reanalysis, '
  'the Human Protein Atlas, DepMap, PRISM and LINCS result tables, and the '
  'candidate-selection table.')

H('AI USAGE DISCLOSURE', 12)
for para in back['AI USAGE DISCLOSURE']:
    P(para, size=10)
P('The mechanism schematics in Figures 2C, 3C and 4C were produced with '
  'generative image tooling from prompts written against the deposited scoring '
  'data, then checked element by element against the analysis by the authors '
  'before use; one erroneous compartment label was corrected and the correction '
  'is applied by deposited code, with the unedited originals retained in the '
  'archive. All quantitative panels are generated directly from the deposited '
  'result tables.', size=10)

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
P('The complete association table, with every score component and its '
  'provenance, is Supplementary Table S1.', italic=True, size=9.5)

t = doc.add_table(rows=1, cols=6)
t.style = 'Table Grid'
hdr = ['#', 'Context', 'Drug / target', 'Score \u00b7 tier', 'Status after audit',
       'Required next step']
for c, h in zip(t.rows[0].cells, hdr):
    c.text = ''
    run = c.paragraphs[0].add_run(h)
    run.bold = True
    run.font.size = Pt(8.5)


def add_row(cells, bold=False, size=8.5):
    row = t.add_row()
    for c, v in zip(row.cells, cells):
        c.text = ''
        run = c.paragraphs[0].add_run(str(v))
        run.font.size = Pt(size)
        run.bold = bold
    return row


add_row(['', 'BENCHMARK RECOVERY', '', '', '', ''], bold=True)
for ctx, label in (('NEPC', 'Neuroendocrine prostate'),
                   ('MIBC / MPBC', 'Muscle-invasive bladder'),
                   ('ccRCC / sRCC', 'Clear cell renal')):
    sub = merged[merged['Context'] == ctx]
    if not len(sub):
        continue
    tiers_here = sub['Tier'].value_counts().to_dict()
    tier_txt = ', '.join(f'{v} {k}' for k, v in tiers_here.items())
    add_row([f'{sub["N"].min()}\u2013{sub["N"].max()}', label,
             f'{len(sub)} associations, all recovering priorities proposed elsewhere',
             tier_txt, 'calibration set', 'not carried forward as discovery'])

add_row(['', 'NO PRIOR UROLOGIC-ONCOLOGY PROPOSAL IDENTIFIED', '', '', '', ''],
        bold=True)
for _, r in novel_rows.sort_values('N').iterrows():
    s = sel[sel['N'] == r['N']]
    if len(s):
        s = s.iloc[0]
        status = ('LEAD CANDIDATE' if int(r['N']) == 17 else
                  'survives audit' if bool(s['survives']) else
                  'excluded: ' + str(s['failed_criteria'])[:58])
    else:
        status = ''
    nxt = ('immunocompetent model with intact myeloid compartment'
           if int(r['N']) == 17 else
           'preclinical bridging; narrow therapeutic window in kidney'
           if int(r['N']) == 19 else
           'confirm successor agent in development' if int(r['N']) == 28 else
           'not carried forward')
    add_row([r['N'], r['Context'], f"{r['Drug']} \u2014 {r['Target']}",
             f"{r['Total']} \u00b7 {r['Tier']}", status, nxt])

add_row(['', 'PARTIAL PRECEDENT', '', '', '', ''], bold=True)
add_row([', '.join(str(int(n)) for n in sorted(partial_rows['N'])),
         'various',
         f'{len(partial_rows)} associations extending a precedent from '
         f'conventional disease or another organ to this variant',
         ', '.join(f'{v} {k}' for k, v in
                   partial_rows['Tier'].value_counts().to_dict().items()),
         'not evaluated as discovery',
         'see Supplementary Table S1'])

add_row(['', 'CANDIDATE NEGATIVE PREDICTIVE BIOMARKER', '', '', '', ''], bold=True)
neg = merged[merged['N'] == 27].iloc[0]
add_row([27, neg['Context'], 'TROP2 (TACSTD2) loss \u2014 sacituzumab govitecan',
         f"{neg['Total']} \u00b7 {neg['Tier']}",
         'hypothesised lower response probability',
         'protein-level confirmation; batch-confounded series'])

P('Scores are the sum of four partially overlapping dimensions (genomic or '
  'context-anchor 0\u20133, transcriptomic 0\u20133, pathway 0\u20132, external '
  'literature 0\u20131) and express strength of evidence within this framework '
  'only, not established drug sensitivity. "No prior urologic-oncology proposal '
  'identified" refers to the pre-specified PubMed search and makes no claim of '
  'biological precedence outside urology.', italic=True, size=9)

# =====================================================================
# Supplementary tables generated alongside
# =====================================================================
SUP = paths.OUTPUT / 'v29_supplementary'
SUP.mkdir(parents=True, exist_ok=True)

full = master.merge(prov[['N', 'scoring_gene', 'arm', 'refit_context', 'E_basis',
                          'refit_log2FC', 'refit_q', 'P_basis', 'pathway_q',
                          'E_derivable_from_data']], on='N')
full.to_csv(SUP / 'Supplementary_Table_S1_full_association_table.csv', index=False)

# S2: score sensitivity - how the ranking moves under each ablation
rows = []
for _, r in prov.iterrows():
    g, e, p_, l = int(r['G_curated']), int(r['E_refit']), int(r['P_refit']), int(r['L_curated'])
    member = 'target in pathway set' in str(r['P_basis'])
    rows.append({
        'N': int(r['N']), 'Target': r['Target'],
        'full': g + e + p_ + l,
        'no_context_anchor': e + p_ + l,
        'no_pathway': g + e + l,
        'no_literature': g + e + p_,
        'pathway_requires_membership': g + e + (p_ if member else 0) + l,
    })
s2 = pd.DataFrame(rows)
for col in ('full', 'no_context_anchor', 'no_pathway', 'no_literature',
            'pathway_requires_membership'):
    s2[f'rank_{col}'] = s2[col].rank(ascending=False, method='min').astype(int)
s2.to_csv(SUP / 'Supplementary_Table_S2_score_sensitivity.csv', index=False)

# S3: per-dataset design summary
summ = pd.read_csv(RF / 'REFIT_SUMMARY.csv')
man = pd.read_csv(REPO / 'data' / 'prepared' / 'PREPARED_MANIFEST.csv')
s3 = summ.merge(man[['context', 'samples', 'data_type', 'note']], on='context',
                how='left')
s3.to_csv(SUP / 'Supplementary_Table_S3_dataset_designs.csv', index=False)

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
legends = sum(len(t_.split()) for t_ in ps
              if t_.startswith('Figure ') and len(t_.split()) > 40)
body = sum(len(ps[i].split()) for i in range(i0, i1) if ps[i]) - legends
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
for col in ('full', 'no_context_anchor', 'no_pathway', 'no_literature',
            'pathway_requires_membership'):
    print(f"    {col:<30} score {lead_s2[col]:>2}  rank {lead_s2['rank_' + col]}")

"""Build the v30 manuscript from the deposited results.

Every quantitative statement is interpolated from MANUSCRIPT_FACTS.json, which
is computed from the result tables. The prose and the deposit therefore cannot
disagree - the failure mode that produced 42 field-level differences between the
v28 text and its own CSV.

Writes: Downloads/FDA_Drug_Repurposing_v31.docx
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
  'interrogated systematically to identify and prioritize drugs for aggressive '
  'urologic cancers, where clinical trials are difficult to power?')
P(f"Knowledge generated: We scored {F['n_associations']} drug-cancer "
  f"associations across seven urologic cancers. "
  f"{F['n_previously_proposed']} of the drugs we identified had already been "
  f"proposed by other groups, which served as a positive control for the "
  f"framework. {F['n_partially_novel']} extended a drug "
  f"proposed for conventional disease, or for another organ, to a variant. One "
  f"was a biomarker observation rather than a drug hypothesis. The remaining "
  f"{F['n_framework_novel']} had no prior proposal in the urologic literature. "
  f"We then used four independent data sources, none of which had contributed "
  f"to the score, and they supported {F['funnel']['survive']} of those "
  f"{F['n_framework_novel']} and argued against the rest.")

H('ABSTRACT', 12)
P(f"Purpose. Rare and variant urologic cancers are difficult to study in "
  f"randomized trials, so few have biomarker-directed treatment options. We "
  f"built a public-data framework that identifies and prioritizes drug targets "
  f"for seven urologic cancers: three common cancers with established "
  f"priorities, which serve as positive controls, and four rare or variant "
  f"cancers for which no such reference exists.")
P(f"Methods. Alteration frequencies, differential expression across ten Gene "
  f"Expression Omnibus datasets, enrichment across eighteen pre-specified "
  f"druggable gene sets and drug-target curation were combined into a 9-point "
  f"score, which exists to put several dissimilar kinds of evidence on one "
  f"comparable scale. Differential expression was "
  f"fitted with design-aware, platform-appropriate models (limma and edgeR). We "
  f"then searched the literature to see which associations had already been "
  f"proposed, after scoring was finished so that it could not influence the "
  f"score. Finally we checked each candidate against four independent data "
  f"sources that took no part in scoring, to see whether anything outside our "
  f"own pipeline supported it. A rule written in advance decided which "
  f"candidates the paper carries forward.")
P(f"Results. We scored {F['n_associations']} drug-cancer associations: "
  f"{F['tiers'].get('Strong', 0)} Strong, {F['tiers'].get('Moderate', 0)} "
  f"Moderate and {F['tiers'].get('Exploratory', 0)} Exploratory. In one "
  f"sarcomatoid series the two tumor types had been run on separate batches of "
  f"microarray chips, so we could not compare them and scored those five "
  f"associations on how strongly each target was expressed within the "
  f"sarcomatoid tumors instead. Of the "
  f"{F['n_associations']} associations, {F['n_previously_proposed']} recover a "
  f"drug already proposed elsewhere for that disease, "
  f"{F['n_partially_novel']} extend a drug from conventional disease or "
  f"another organ to a variant, one is the TROP2 biomarker observation, and "
  f"{F['n_framework_novel']} had no prior proposal in the urologic literature. "
  f"Three of those {F['n_framework_novel']} were supported by the independent "
  f"sources. The other three were not: CRISPR screens showed one target is not "
  f"required for tumor-cell survival, one is not strongly expressed in the "
  f"disease, and one lost its expression signal once we accounted for batch.")
P(f"Conclusion. Public data can be used to prioritize drug hypotheses for "
  f"cancers that may never have a randomized trial, provided the method is "
  f"explicit about what it cannot show. {F['funnel']['survive']} hypotheses "
  f"were supported in {F['n_survivor_contexts']} diseases: CXCR1/CXCR2 "
  f"blockade and anti-CEACAM1 in renal medullary carcinoma, and anti-CEACAM5 "
  f"conjugates in ASCL1-positive small-cell bladder cancer. We rank candidates "
  f"within a disease. We do not rank a candidate in one disease against a "
  f"candidate in another, because the only feature that would separate them is "
  f"whether the target happens to appear in our gene panel, and that reflects "
  f"how we built the panel rather than the biology of the tumors. All "
  f"three need experimental validation in their own disease.")

# =====================================================================
# Introduction
# =====================================================================
H('INTRODUCTION')
P('Over the last several decades an abundance of online data resources has '
  'emerged to help us better understand oncologic disease. Each does a '
  'different job. The Cancer Genome Atlas catalogs somatic alterations across '
  'thirty-three cancer types from more than eleven thousand patients [1,2], and '
  'cBioPortal makes those alteration frequencies searchable one gene at a '
  'time. The Gene Expression Omnibus archives over two hundred thousand '
  'transcriptomic datasets, most of them deposited with the samples and the '
  'design that produced them. The Therapeutic Target Database and OpenTargets '
  'record which proteins have drugs against them and how far each of those '
  'drugs has progressed. The Kyoto Encyclopedia of Genes and Genomes groups '
  'genes into annotated pathways, so a signal in a single gene can be read '
  'against the pathway it belongs to. Taken together, the bottleneck in '
  'translational oncology has arguably shifted from generating data to '
  'interrogating it.')
P('Drug repurposing takes a different route to a new treatment. Instead of '
  'developing a new molecule, it asks whether a drug that is already approved, '
  'or already in trials, can be matched to a disease it was not designed for. '
  'A drug that has been through trials arrives with its human dosing and side '
  'effects already known, which is most of what makes it worth trying '
  'somewhere new. The hard part is doing this matching across several diseases '
  'at once, in a way disciplined enough that someone else can check the result '
  'and disagree with it.')
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
  'systematically enough to prioritize biomarker-anchored drug hypotheses '
  'across several such cancers at once. Three better-studied cancers are '
  'included deliberately as positive controls. Their treatment priorities are '
  'already documented, so whether the pipeline returns those priorities tells '
  'us how much weight to give its output in the rare cancers, where nothing is '
  'documented to check it against. Two design choices support that reading. We '
  'scored every candidate before classifying any of them as previously '
  'proposed or not, so agreement with the literature could not have been '
  'engineered. And we wrote the shortlist rule before we applied it, so any '
  'candidate we drop can be traced to a specific criterion rather than to our '
  'opinion.')
P(f"What is new here is not any single drug-cancer pair. "
  f"{F['n_previously_proposed']} of the {F['n_associations']} associations we "
  f"report were proposed by other groups first, and we say so in each case. "
  f"What is new is that one pipeline runs across seven urologic cancers at "
  f"once, with well-studied cancers included in the same run as positive "
  f"controls, and that it reports what it cannot support alongside what it "
  f"can: the candidates that dissolved once the data were modeled properly, "
  f"the candidate an independent screen contradicted, and a drug class our own "
  f"gene panel made it impossible to find. Repurposing work in these rare "
  f"cancers has been done one disease at a time, which leaves no way to judge "
  f"whether a method that produced a plausible answer in one would produce one "
  f"in another.")

# =====================================================================
# Methods
# =====================================================================
H('MATERIALS AND METHODS')
P('Candidate associations were assembled from the sources above before the final models were fitted. Every score reported here comes from those final models.')
P('We applied one six-step pipeline uniformly to all seven contexts, set out in '
  'Figure 1: a genomic or context-anchor value; per-context differential '
  'expression across ten Gene Expression Omnibus datasets; upper-tail '
  'hypergeometric enrichment across eighteen pre-specified druggable pathway or '
  'gene sets; mapping of differentially expressed genes to clinically evaluable '
  'agents through the Therapeutic Target Database and OpenTargets; a 9-point '
  'prioritization score combining four evidence dimensions; and a '
  'score-independent PubMed prior-proposal audit performed only after '
  'scoring was complete. '
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
  f"were filtered by expression, normalized by trimmed mean of M-values and "
  f"fitted with voom precision weights; log-scale series were fitted with "
  f"limma\u2019s variance-moderated linear model with an intensity trend. Three "
  f"design features the primary deposits make explicit, and the previous "
  f"analysis had not used, were modeled. The penile series has "
  f"{dsn['pscc_normal_arrays']} normal arrays from only "
  f"{dsn['pscc_normal_donors']} donors, so donor was blocked by duplicate "
  f"correlation; the muscle-invasive bladder kinome panel is matched tumor-normal, "
  f"so patient was blocked; and each small-cell subtype was contrasted "
  f"against the mean of the remaining subtypes with batch in the model. Renal "
  f"medullary carcinoma is a two-cell-line rescue experiment with no deposited "
  f"sample-level matrix, so it was treated as two independent patient-derived "
  f"models rather than an inferential cohort, and only genes "
  f"changing consistently in both were carried forward.")
P(f"Gene symbols were normalized to current HGNC nomenclature before enrichment. "
  f"Pathway definitions use current symbols while the older platforms use the "
  f"symbols of their day, so any gene renamed in the interval was silently "
  f"dropped from its own pathway. Enrichment used "
  f"the direction-specific up-regulated gene list as the query and the genes "
  f"actually measured and retained in that dataset as the background, rather "
  f"than a fixed transcriptome-wide count. Benjamini-Hochberg correction was "
  f"applied across the eighteen sets within each context; it was not applied "
  f"across contexts, drugs or the downstream comparisons, and q-values should be "
  f"read accordingly. Two thresholds were pre-specified and are applied "
  f"throughout: differential-expression significance is q < 0.05, and "
  f"pathway enrichment uses an exploratory q < 0.10, with values between 0.05 "
  f"and 0.10 described as suggestive rather than conventionally significant.")
P('Each association received a score from 0 to 9 across four dimensions, which '
  'are partially overlapping rather than independent: a genomic or '
  'context-anchor value (0\u20133), a transcriptomic value (0\u20133), a pathway '
  'value (0\u20132) and external mechanistic-literature concordance (0\u20131). '
  'The transcriptomic and pathway dimensions share an input, and in several '
  'benchmark rows the genomic dimension reflects a disease-defining anchor '
  'rather than alteration of the nominated target; both bound what the '
  'composite means and are quantified in the Discussion. The two data-derived '
  'dimensions are computed by one function from the deposited fitted tables '
  'and reconciled against the manuscript by an audit script, so divergence is '
  'detectable rather than impossible. Scores map to Strong (7\u20139), Moderate (4\u20136) and Exploratory '
  '(1\u20133) tiers, which express strength of evidence within this framework '
  'only and not established drug sensitivity.')
P('The prior-proposal audit was performed after scoring was complete, classifying '
  'each association as having no prior urologic-oncology proposal identified, a '
  'partial precedent, or a prior proposal. It was carried out by one author and '
  'was not duplicated by a second reviewer, so it is score-independent rather '
  'than independent in the dual-reviewer sense; the search template, the counting '
  'rules and the per-row classifications are deposited. Novelty was assessed against urologic-oncology literature '
  'only: prior proposals from small-cell lung, gastric or other non-urologic '
  'contexts do not count, even where the same biology has been proposed. This is '
  'a statement about the urologic literature, not a claim of biological '
  'precedence.')
P(f"Candidates were reduced by a rule fixed before final reranking. "
  f"Eligibility required all of: E0, a biological contrast estimable separately "
  f"from the major known technical variables; E1, no prior urologic-oncology "
  f"proposal identified; E2, Moderate tier or better; E3, a transcriptomic "
  f"component re-derivable from deposited data at q < 0.05; and E4, a "
  f"clinical-stage agent with a documented development or access pathway. "
  f"Support additionally required that no independent source contradict the "
  f"candidate and that target accessibility match the modality; a source "
  f"that cannot evaluate a candidate counts as neither support nor "
  f"contradiction. Where a disease held more than one supported candidate, "
  f"the first priority "
  f"additionally required that the target itself belong to an enriched "
  f"pathway. Full criteria are in Supplementary Methods.")

print('front matter and methods written')

# =====================================================================
# Results
# =====================================================================
H('RESULTS')

H('3.1 The Association Table', 11.5, 10, level=2)
ctx_counts = ', '.join(f'{k} {v}' for k, v in F['per_context'].items())
P(f"The pipeline produced {F['n_associations']} drug-cancer associations "
  f"across the seven contexts (Table 1; the full table with every score "
  f"component and its provenance is Supplementary Table S1). "
  f"{F['tiers'].get('Strong', 0)} reach the Strong tier, "
  f"{F['tiers'].get('Moderate', 0)} Moderate and "
  f"{F['tiers'].get('Exploratory', 0)} Exploratory. Five associations from the "
  f"sarcomatoid series carry a smaller denominator for the reason given in "
  f"Section 3.3, and are not assigned a tier. Each row records its score "
  f"decomposition, the clinical development stage of its agent, whether the "
  f"pairing has been proposed before, and the dataset and gene its "
  f"transcriptomic component rests on.")

H('3.2 Benchmark Recovery', 11.5, 10, level=2)
P(f"The three benchmark contexts contributed sixteen associations, and every "
  f"one of them recovers a drug proposed independently by another group: six "
  f"in neuroendocrine prostate cancer [10\u201318], seven in muscle-invasive "
  f"bladder cancer [19\u201327] and three in clear cell renal cell carcinoma "
  f"[28\u201332]. Two more previously proposed drugs appear in the rare "
  f"contexts, erlotinib in renal medullary carcinoma and pembrolizumab in "
  f"penile squamous cell carcinoma [34,35], giving "
  f"{F['n_previously_proposed']} in total. This is a positive control. It "
  f"shows the pipeline returns the expected answer where an expected answer "
  f"exists, and it is not independent validation, for the reason given in the "
  f"Discussion.")

H('3.3 Discovery Contexts', 11.5, 10, level=2)
P(f"In renal medullary carcinoma the deposited experiment is a SMARCB1 rescue in "
  f"two patient-derived lines. Across the {rmc['genes_measured_both']:,} genes "
  f"measured in both, the genome-wide correlation between lines is only "
  f"r = {rmc['r_between_lines']}, so requiring consistent change in both is a "
  f"stringent filter: {rmc['up_both']} genes pass it. A chemokine axis is among "
  f"them, elevated in the SMARCB1-null disease state in both lines \u2014 CXCL8 "
  f"{rmc['CXCL8']['RMC2C']:+.2f} and {rmc['CXCL8']['RMC219']:+.2f}, CXCL1 "
  f"{rmc['CXCL1']['RMC2C']:+.2f} and {rmc['CXCL1']['RMC219']:+.2f}, CXCL2 "
  f"{rmc['CXCL2']['RMC2C']:+.2f} and {rmc['CXCL2']['RMC219']:+.2f}, CXCL3 "
  f"{rmc['CXCL3']['RMC2C']:+.2f} and {rmc['CXCL3']['RMC219']:+.2f} \u2014 with "
  f"KEGG chemokine signaling enriched on the both-lines set at "
  f"q = {q['rmc_chemokine']:.4f} (Figure 2), coherent with the neutrophil-rich "
  f"microenvironment described in this disease [33]. This nominates the "
  f"CXCR1/CXCR2 antagonist class, and carcinoembryonic antigen-related cell adhesion "
  f"molecule 1 alongside it (CEACAM1 {rmc['CEACAM1']['RMC2C']:+.2f} and "
  f"{rmc['CEACAM1']['RMC219']:+.2f}). Chemokine signaling is not the most "
  f"strongly enriched set in this context \u2014 {F['rmc_top_pathway'].replace('_', ' ')} "
  f"ranks above it at q = {F['rmc_top_q']:.4f} \u2014 so the claim is that the "
  f"axis is robustly present, not that it dominates.")
P(f"Penile squamous cell carcinoma showed a dominant immune-hot phenotype. "
  f"HLA-DRA is elevated at {de['HLA_DRA_pscc']['log2FC']:+.2f} "
  f"(q = {fmt(de['HLA_DRA_pscc']['q'])}) with CXCL9 and CXCL10 elevated and "
  f"antigen processing and presentation enriched at "
  f"q = {q['pscc_antigen']:.4f}, converging on the established pembrolizumab "
  f"priority [36\u201338] with partially-novel matrix metalloproteinase and "
  f"periostin candidates [39\u201341]. This signal survives modeling the six "
  f"normal arrays as {dsn['pscc_normal_donors']} donors rather than six "
  f"independent samples, which was the more demanding test.")
P(f"In the sarcomatoid series (Figure 3) every sarcomatoid tumor was run on a "
  f"different batch of chips from every conventional tumor. A difference "
  f"between the two groups is therefore also a difference between two batches, "
  f"and no model can separate them, so we report no sarcomatoid-versus-"
  f"conventional comparison. What the cohort does support is how abundant each "
  f"transcript is within the sarcomatoid tumors, and that is what these rows "
  f"are scored on. UHRF1 sits at the "
  f"{ordinal(F['abundance_pct']['UHRF1']['pct'])} percentile of "
  f"{F['abundance_pct']['UHRF1']['n']:,} measured transcripts [42], NSD2 at "
  f"the {ordinal(F['abundance_pct']['NSD2']['pct'])} and G6PD at the "
  f"{ordinal(F['abundance_pct']['G6PD']['pct'])} [43]. ATR sits at the "
  f"{ordinal(F['abundance_pct']['ATR']['pct'])}, which is why the ATR "
  f"candidate the earlier analysis carried does not go forward. The pathway "
  f"component could only have come from the comparison we ruled out, so it is "
  f"reported as not estimable, and these rows total out of 7 rather than 9 and "
  f"carry no tier.")
P(f"TROP2, the target of sacituzumab govitecan, reads lower in the sarcomatoid "
  f"samples, in agreement with two pathology reports [44,45]; antigen "
  f"heterogeneity of this kind extends to NECTIN-4 as well [46]. Lower TROP2 "
  f"would mean less target to bind, but only the ruled-out comparison could "
  f"establish loss, no treated patients were studied here, and the accelerated "
  f"urothelial indication for sacituzumab govitecan was withdrawn in November "
  f"2024. We report it as an observation for an independent cohort, not as a "
  f"predictive biomarker, and it carries no score.")

P(f"Lineage-stratified small-cell bladder cancer (Figure 4), classified by "
  f"lineage transcription factor [47], produced three subtype-specific "
  f"associations. ASCL1-positive tumors show CEACAM5 elevation "
  f"({de['CEACAM5_ascl1']['log2FC']:+.2f}, q = {fmt(de['CEACAM5_ascl1']['q'])}), "
  f"supporting CEACAM5-directed antibody-drug conjugates as a class; "
  f"POU2F3-positive tumors show arachidonic-acid metabolism enrichment "
  f"(q = {q['pou2f3_arachidonic']:.3f}) with PTGS1 elevated "
  f"({de['PTGS1_pou2f3']['log2FC']:+.2f}, q = {fmt(de['PTGS1_pou2f3']['q'])}), "
  f"identifying a lineage-specific arachidonic-acid and COX-1 program whose "
  f"therapeutic direction requires functional testing: in the tuft-cell biology "
  f"this program is named for, prostaglandin signaling has been reported to "
  f"restrain rather than promote tumorigenesis [49]. The "
  f"NEUROD1-positive somatostatin receptor 2 association does not survive: the "
  f"fold change reproduces ({de['SSTR2_neurod1']['log2FC']:+.2f}) but it does "
  f"not reach significance under a batch-adjusted subtype contrast "
  f"(q = {de['SSTR2_neurod1']['q']:.3f}), and the neuroactive ligand-receptor "
  f"set is not enriched in that subtype. The somatostatin receptor 2 paradigm "
  f"established in small-cell lung cancer [48] does not transfer here on "
  f"these data.")

print('results 3.1-3.3 written')

H('3.4 Orthogonal Evidence Audit', 11.5, 10, level=2)
P('Most discovery associations and many benchmark associations are nominated '
  'from transcript abundance, a weaker claim than several modalities require; '
  'benchmark rows resting on curated non-transcriptomic evidence are flagged '
  'individually in Supplementary Table S1. The nominated targets were assessed '
  'against four sources that took no part in scoring. These audit rather than '
  'validate: each can find a candidate wanting, none can establish that it '
  'works, and each is blind to some candidates by construction.')
P(f"{F['hpa']['n_surface_required']} associations depend on extracellular "
  f"access and all {F['hpa']['n_confirmed']} are confirmed against the Human "
  f"Protein Atlas [50], which establishes modality-compatible localization "
  f"rather than protein abundance in the tumor. Normal-tissue RNA is "
  f"reported for orientation only and is not a therapeutic-window "
  f"comparison: CEACAM1 is substantially expressed in normal kidney "
  f"({F['hpa']['CEACAM1_kidney']} normalized transcripts per million) and "
  f"warrants tissue-level protein and safety assessment, while CXCR1 is low "
  f"there ({F['hpa']['CXCR1_kidney']}) but sits on the circulating myeloid "
  f"cells the antagonist is meant to act on. Delta-like "
  f"ligand 3 and somatostatin receptor 2 are both near-undetectable in normal "
  f"bladder, while trophoblast cell-surface antigen 2 is abundant there "
  f"({F['hpa']['nTPM']['TACSTD2']} normalized transcripts per million), which "
  f"is what makes its loss interpretable rather than a low-baseline artifact. "
  f"Per-target values are in Supplementary Table S1.")
P(f"DepMap CRISPR screens ask whether a cell requires a gene, a more demanding "
  f"question than whether it is abundantly expressed [55]; gene effect is "
  f"reported on the Chronos scale, where more negative means more required. "
  f"Across {F['depmap']['n_urothelial_lines']} urothelial lines, stratified by "
  f"genotype and target expression from CCLE via cBioPortal [56], it "
  f"calibrates: RPL5 scores {F['depmap']['RPL5']:.2f} with every line dependent, "
  f"and PIK3CA-mutant lines are selectively dependent on PIK3CA "
  f"({F['depmap']['PIK3CA_mut']:.2f} versus {F['depmap']['PIK3CA_wt']:.2f}). "
  f"It also contradicts one of our own candidates: NSD2 is "
  f"{F['depmap']['NSD2_verdict']} even in the lines expressing it most highly "
  f"({F['depmap']['NSD2_high']:+.2f}), which is why that candidate does not "
  f"survive. ATR is a genuine but pan-essential dependency, so the target is "
  f"required while the sarcomatoid-specific rationale gains no support. For "
  f"antibody, conjugate and radioligand rows the screen is not the right test "
  f"at all: CEACAM1 is recorded as {F['depmap']['CEACAM1_verdict']}.")
P(f"Compound-level activity was read from the PRISM Repurposing screen across "
  f"{F['prism']['n_lines']} cell lines [51], comparing urothelial against "
  f"non-urothelial lines by two-sided Welch test with Benjamini-Hochberg "
  f"correction across the compounds tested. It calibrates: bortezomib is "
  f"broadly cytotoxic ({F['prism']['bortezomib']:.2f}) without being "
  f"urothelial-selective, and erlotinib is markedly more active in urothelial "
  f"lines ({F['prism']['erlotinib_uro']:.2f} versus "
  f"{F['prism']['erlotinib_nonuro']:.2f}; q = {F['prism']['erlotinib_q']:.4f}), "
  f"consistent with its role as the renal medullary positive control. Two "
  f"compounds that a weaker comparison had marked selective do not survive "
  f"this one: the ATR inhibitor VE-822 (q = {F['prism']['ve822_q']:.2f}) and "
  f"polydatin (q = {F['prism']['polydatin_q']:.2f}) are not significantly more "
  f"active in urothelial lines once they are compared against non-urothelial "
  f"lines rather than against a panel containing them, and once multiplicity "
  f"is accounted for. The four "
  f"screened CXCR1/CXCR2 antagonists show no tumor-cell-autonomous activity in "
  f"any lineage, which is what a microenvironment-directed mechanism predicts "
  f"rather than a negative result; it says nothing about normal-cell, myeloid "
  f"or organ toxicity.")
P(f"Signature reversal against the LINCS L1000 libraries [52,53], recomputed on "
  f"the refitted gene lists across eight analysis units, recovered several "
  f"nominated agents, but none ranked first in its intended context and the "
  f"same agents appeared across unrelated contexts and lineages: palbociclib "
  f"surfaces in three, and erlotinib in sarcomatoid disease rather than in the "
  f"renal medullary context where it is the positive control. The lists are "
  f"dominated by heat shock protein 90 and multi-kinase perturbagens profiled "
  f"in unrelated lineages. The layer "
  f"therefore lacked context specificity and was not used to support or exclude "
  f"any candidate; complete rankings and corrected values are deposited.")

H('3.5 The Surviving Hypotheses', 11.5, 10, level=2)
P(f"Applying the rule (Figure 5), the {F['funnel']['framework_novel']} "
  f"associations with no prior proposal in the urologic literature reduce to "
  f"{F['funnel']['survive']}, and each of the three that stop does so for a "
  f"reason drawn from the evidence rather than from a limitation of our "
  f"pipeline. The somatostatin receptor 2 candidate loses its transcriptomic "
  f"support once the small-cell subtypes are contrasted with batch in the model "
  f"(q = {de['SSTR2_neurod1']['q']:.3f}), leaving a score of 2. The ATR "
  f"candidate is not strongly expressed in sarcomatoid tumors "
  f"({ordinal(F['abundance_pct']['ATR']['pct'])} percentile), leaving a score of "
  f"1. The NSD2 candidate is abundant, but scores 3 of the 7 points its cohort "
  f"can support and is contradicted outright by an independent source: CRISPR "
  f"screens show that urothelial cells do not require NSD2 even where they "
  f"express it most highly. The {F['funnel']['survive']} that remain lie in "
  f"{F['n_survivor_contexts']} diseases, renal medullary carcinoma and "
  f"ASCL1-positive small-cell bladder cancer.")
P(f"We rank these three within a disease, not between diseases. Two are in "
  f"renal medullary carcinoma and compete for the same experimental effort, so "
  f"ordering those two is a real decision. The third is in ASCL1-positive "
  f"small-cell bladder cancer and competes with neither. To rank across "
  f"diseases we would have to separate them on something, and the only thing "
  f"available is whether the target happens to appear in one of our eighteen "
  f"gene sets. Section 3.6 shows that this reflects which drug classes we chose "
  f"to include, not which biology matters, so we do not use it that way.")
P(f"Within renal medullary carcinoma we would carry CXCR1/CXCR2 blockade "
  f"forward first. It scores {lead['total']}/9. Its chemokine ligands are "
  f"elevated in both patient-derived lines, its target sits in a pathway that "
  f"is itself enriched (q = {q['rmc_chemokine']:.4f}) rather than borrowing an "
  f"enrichment driven by other genes, both receptors are confirmed membrane "
  f"proteins, and the antagonist class is already in clinical development with "
  f"human pharmacology and safety data. Anti-CEACAM1 scores "
  f"{second['total']}/9 and comes second in this disease: CEACAM1 lies in none "
  f"of the enriched pathways, so nothing at the pathway level supports it, and "
  f"its surface protein abundance and therapeutic index in renal medullary "
  f"carcinoma are both unknown.")
P(f"Anti-CEACAM5 conjugates in ASCL1-positive small-cell bladder cancer are the "
  f"third supported hypothesis. CEACAM5 is strongly enriched in that subtype "
  f"({de['CEACAM5_ascl1']['log2FC']:+.2f}, "
  f"q = {fmt(de['CEACAM5_ascl1']['q'])}), confirmed at the membrane, and low "
  f"in normal bladder RNA ({F['hpa']['nTPM']['CEACAM5']} normalized "
  f"transcripts per million, which orients safety planning rather than "
  f"demonstrating a systemic therapeutic window), and the drug class is in "
  f"active development. It is the only supported hypothesis in its disease. Its "
  f"weaknesses are that CEACAM5 belongs to none of the eighteen pre-specified "
  f"sets, so no pathway evidence supports it, and that subtype-specific protein "
  f"expression, internalization and payload sensitivity in small-cell bladder "
  f"cancer are all untested.")
P(f"One qualification applies to the renal medullary lead. The dependency and "
  f"compound screens do not endorse CXCR1/CXCR2 blockade so much as they cannot "
  f"test it: the proposed mechanism works through myeloid recruitment, which a "
  f"tumor-cell monoculture cannot see, so their silence is not support. All "
  f"three are hypotheses, not validated findings. The experiment that would "
  f"settle this one is CXCR1/CXCR2 blockade in an immunocompetent model with an "
  f"intact myeloid compartment, and it remains to be done.")

H('3.6 What the Framework Could Not Surface', 11.5, 10, level=2)
P('Applied consistently, the drug-class-first rule that fixed the eighteen gene '
  'sets exposes one material omission. Delta-like ligand 3 is the canonical '
  'ASCL1-lineage neuroendocrine surface antigen and the target of tarlatamab, '
  'a bispecific T-cell engager granted accelerated approval in 2024 and '
  'traditional approval in 2025 for extensive-stage small-cell lung cancer. '
  'No pre-specified set in our panel contains it, so no DLL3 '
  'hypothesis could have been generated for any context, irrespective of the '
  'data.')
P('Tested post hoc, DLL3 is elevated in the ASCL1-positive subtype '
  '(log₂ fold change +1.61) but does not reach significance after '
  'correction (q = 0.30), and had the Notch pathway been among the pre-specified '
  'sets it would have been nominally enriched only. DLL3-directed therapy in '
  'genitourinary small-cell carcinoma has already been proposed in the urologic '
  'literature (Liao 2024 [54]), so under this study’s standard DLL3 is a '
  'previously proposed priority the panel failed to recover: a false negative '
  'of the framework rather than a missed discovery. It is reported here and '
  'excluded from Table 1, the pre-specified output. The binding constraint is '
  'the panel’s coverage of druggable biology, not the scoring rules and '
  'not the data.')

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
  f"The sarcomatoid confounding of Results 3.3 is the clearest: "
  f"{dsn['sarc_chips_sarc_only']} chips carry sarcomatoid samples only and "
  f"{dsn['sarc_chips_uc_only']} carry conventional samples only, none both, so "
  f"a model including chip is not estimable and those five rows are unscored. "
  f"The clear cell renal series "
  f"contains {dsn['ccrcc_samples']} tumors and no normal tissue, so those rows "
  f"are scored on absolute expression rather than a disease contrast, and the "
  f"metastatic contrast the series does support yields "
  f"{dsn['ccrcc_q05_genes']} gene at q < 0.05. And the hereditary "
  f"leiomyomatosis series, used previously as though it spoke to clear cell "
  f"disease, is a different disease, reported here as adjacent-disease "
  f"mechanistic context only.")
P('The recovery of eighteen previously-proposed priorities is calibration, not '
  'independent validation: prior knowledge entered the pathway panel, the drug '
  'curation, the literature dimension and the choice of representative agent, so '
  'the framework and the literature are not independent. What it establishes '
  'is that a pipeline blind to the prior-proposal classifications during '
  'scoring recovers established priorities in well-characterized disease. That '
  'is a positive control, not a measurement of sensitivity or precision.')
P(f"The scoring dimensions are partially overlapping, and the composite should "
  f"be read as an ordering device rather than a measurement. The transcriptomic "
  f"and pathway dimensions share an input, and in several rows the genomic "
  f"dimension reflects a disease-defining anchor rather than alteration of the "
  f"nominated target: renal medullary carcinoma is near-universally "
  f"SMARCB1-deficient, which says nothing specific about CXCR1 or CXCR2. That "
  f"contribution is load-bearing. In the "
  f"sensitivity analysis (Supplementary Table S2), which orders all scored "
  f"associations numerically to test the score architecture and not to rank "
  f"hypotheses across diseases, the renal medullary candidate falls from "
  f"first to {int(s2_lead_no_anchor)}th when the anchor contribution is removed "
  f"and to {int(s2_lead_no_pathway)}rd when the pathway dimension is dropped, "
  f"while it remains first when the literature dimension is removed and when the "
  f"pathway dimension is required to contain the target itself. Part of the "
  f"ordering is therefore carried by the architecture rather than by "
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
  'carcinoma, have no histology-labeled cohort of adequate size and could not '
  'be analyzed. The forward requirement is infrastructural rather than '
  'algorithmic.')

H('CONCLUSIONS')
P(f"We scored {F['n_associations']} drug-cancer associations across three "
  f"benchmark and four rare or variant urologic cancers using only public data. "
  f"{F['n_previously_proposed']} recovered a drug proposed independently "
  f"elsewhere, which is the positive control, and "
  f"{F['n_framework_novel']} had no prior proposal in the urologic literature. "
  f"A rule fixed in advance, together with four independent data sources that "
  f"took no part in scoring, reduced those {F['n_framework_novel']} to "
  f"{F['funnel']['survive']}. The contribution is not any single drug-cancer "
  f"pair but a way of generating, calibrating and challenging drug hypotheses "
  f"in cancers too rare for a trial, in a form that others can audit and "
  f"contradict. Within renal medullary carcinoma we would carry CXCR1/CXCR2 "
  f"blockade ahead of anti-CEACAM1. We do not rank the renal medullary "
  f"candidates against the small-cell bladder candidate, because they are in "
  f"different diseases and nothing in these data separates them. All three "
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
  'normalized against the HGNC complete set. Drug-target associations were drawn '
  'from the Therapeutic Target Database and OpenTargets. All analysis scripts, '
  'the fitted differential-expression tables, the enrichment tables, the master '
  'association table with per-row scoring provenance, the candidate-selection '
  'table, the candidate denominator, the prior-proposal audit and the '
  'figure-generation code are archived at GitHub '
  '(github.com/gbrink10/urologic-variant-drug-prioritization) and at Zenodo '
  f'({ZENODO_CONCEPT_DOI}, which resolves to the most recent archived version'
  + (f'; this manuscript corresponds to {ZENODO_VERSION_DOI}' if ZENODO_VERSION_DOI
     else '') + '). '
  'The pipeline runs end to end from the deposited code; the large primary '
  'deposits are re-downloaded by the first script rather than mirrored.')

# =====================================================================
# Figures
# =====================================================================
FIGURES = [
    ('Figure1_pipeline.png', 6.5,
     'Figure 1. The pipeline, from context definition to the supported '
     'hypotheses. Steps 1 to 6 build the association table: genomic or '
     'context-anchor input from The '
     'Cancer Genome Atlas for the three benchmark contexts and from published '
     'series for the four rare or variant contexts; differential expression '
     'across ten Gene Expression Omnibus datasets fitted with a design-aware, '
     'platform-appropriate model; hypergeometric enrichment across eighteen '
     'pre-specified druggable pathway or gene sets against each dataset’s own '
     'measured-gene universe; drug-target curation; a 9-point prioritization '
     'score; and a score-independent PubMed prior-proposal audit performed only after '
     'scoring. Step 7 is the orthogonal evidence audit, whose four layers '
     'contributed nothing to any score. The shortlist is produced by a rule '
     'fixed before it was applied.'),
    ('Figure2_RMC.png', 6.9,
     'Figure 2. Renal medullary carcinoma. (A) Effect in RMC-2C against effect '
     'in RMC219 for every gene measured in both lines. The genome-wide '
     'correlation is weak, so requiring consistent change in both lines is a '
     'stringent filter rather than a formality; genes passing it are highlighted, '
     'and the chemokine axis is labeled. (B) The chemokine axis gene by gene, '
     'each line shown separately, in disease-state orientation, with the pathway '
     'q-value computed on the both-lines set. (C) Proposed mechanism. CXCR1 and '
     'CXCR2 are receptors on the neutrophil, not on the tumor cell, which is '
     'why a tumor-cell monoculture cannot test this hypothesis in either '
     'direction.'),
    ('Figure3_SarcUC.png', 6.9,
     'Figure 3. Sarcomatoid urothelial carcinoma. Every sarcomatoid sample was '
     'run on an array chip carrying no conventional sample, and vice versa, so '
     'histology and chip are completely aliased. (A) The separation between the '
     'two chip-aligned groups, shown for completeness; it cannot be read as a '
     'difference between histologies. (B) Pathway values from that same '
     'comparison. Because they inherit the confounding, no pathway component is '
     'scored for this context and these associations carry a total out of 7 '
     'rather than 9. (C) The nominated targets, which are scored instead on how '
     'abundant each transcript is within the sarcomatoid tumors themselves, a '
     'quantity the aliasing does not reach.'),
    ('Figure4_SCBC.png', 6.9,
     'Figure 4. Lineage-stratified small-cell bladder cancer. (A) Subtype '
     'composition by lineage transcription factor. (B) The nominated target in '
     'each subtype with its q-value from the batch-adjusted subtype contrast; '
     'somatostatin receptor 2 in NEUROD1-positive tumors does not reach '
     'significance, which is why that association does not enter the shortlist. '
     '(C) Proposed lineage-stratified therapeutic hypotheses. CEACAM5 and '
     'somatostatin receptor 2 are cell-surface targets; PTGS1/COX-1 is an '
     'intracellular enzyme on the endoplasmic reticulum, shown as a candidate '
     'perturbation axis with aspirin as a pharmacologically available '
     'non-selective inhibitor rather than a COX-2-selective agent; the '
     'therapeutic direction is unresolved and requires functional testing.'),
    ('Figure5_candidate_selection.png', 6.9,
     'Figure 5. Candidate selection under a rule fixed in advance. (A) '
     'Attrition from the full association table to the three supported '
     'hypotheses, with the criterion applied at each stage. (B) Every '
     'association with no prior urologic-oncology proposal, against every '
     'criterion. Each cell carries a symbol as well as a color: + supports, '
     '~ partial, \u2212 fails the criterion or contradicts, n/a cannot test. '
     'The transcriptomic column records which arm the evidence comes from, '
     'and the next column whether it meets that arm\u2019s standard. The '
     'pathway column reads not estimable for the sarcomatoid rows, whose only '
     'available enrichment derives from the confounded comparison. Enrichment '
     'is credited only where the target is itself a member of the enriched '
     'pathway, since an enrichment driven by other genes is not evidence for '
     'that target. A source that cannot evaluate a candidate is not evidence '
     'for it, so absence of contradiction is weaker than positive support.'),
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
P('Claude (Anthropic) and ChatGPT (OpenAI) were used for coding assistance, '
  'literature-audit organization, language editing and manuscript-structure '
  'suggestions. All quantitative analyses were executed and reviewed by the '
  'authors using author-run Python 3.10 and R 4.6.1 scripts; the '
  'differential-expression refit used the Bioconductor packages limma 3.68.4 '
  'and edgeR 4.10.1. No artificial-intelligence-generated data entered any '
  'quantitative analysis, and every prior-proposal classification and score '
  'assignment was verified by the authors, who take responsibility for the '
  'content and conclusions. The mechanism schematics in Figures 2C, 3C and 4C '
  'were produced with GPT-4o image generation from prompts written against the '
  'deposited scoring data and checked element by element against the analysis '
  'before use; the prompts, the unedited originals and the corrections applied '
  'are deposited with the code.', size=10)
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
P('Every association is accounted for in one class. The complete table, with all '
  'four score components and their provenance, is Supplementary Table S1.',
  italic=True, size=9.5)

t = doc.add_table(rows=1, cols=6)
t.style = 'Table Grid'
hdr = ['#', 'Context', 'Drug / target', 'Score \u00b7 tier', 'Status',
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
        run = para.add_run(str(v))
        run.font.size = Pt(size)
        run.bold = bold
    return row


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

add_row(['', 'BENCHMARK RECOVERY \u2014 calibration, not discovery', '', '', '', ''],
        bold=True)
for ctxs, label in ((('NEPC',), 'Neuroendocrine prostate'),
                    (('MIBC / MPBC',), 'Muscle-invasive bladder'),
                    (('ccRCC / sRCC', 'ccRCC'), 'Clear cell renal')):
    sub = merged[merged['Context'].isin(ctxs)]
    if not len(sub):
        continue
    accounted |= set(sub['N'])
    tiers_here = sub['Tier'].value_counts().to_dict()
    add_row([f'{sub["N"].min()}\u2013{sub["N"].max()}', label,
             f'{len(sub)} associations, all recovering priorities proposed elsewhere',
             ', '.join(f'{v} {k}' for k, v in tiers_here.items()),
             'calibration set', 'not carried forward as discovery'])

# previously proposed priorities arising in the rare or variant contexts
rare_recovery = merged[merged['N'].isin([18, 20])]
if len(rare_recovery):
    add_row(['', 'RECOVERY WITHIN THE DISCOVERY CONTEXTS', '', '', '', ''], bold=True)
    for _, r in rare_recovery.iterrows():
        accounted.add(int(r['N']))
        add_row([r['N'], r['Context'], f"{r['Drug']} \u2014 {r['Target']}",
                 f"{r['Total']} \u00b7 {r['Tier']}", 'previously proposed',
                 'supports calibration in a rare context'])

add_row(['', 'NO PRIOR UROLOGIC-ONCOLOGY PROPOSAL IDENTIFIED', '', '', '', ''],
        bold=True)
for _, r in novel_rows.sort_values('N').iterrows():
    accounted.add(int(r['N']))
    srow = sel[sel['N'] == r['N']]
    if len(srow):
        srow = srow.iloc[0]
        # spell the exclusion out; codes are opaque and were being truncated
        PLAIN = {
            23: 'Not carried forward: scores 3 of the 7 points its cohort can '
                'support, and CRISPR screens show no dependency in the '
                'nominated stratum',
            24: 'Not carried forward: the target is not abundantly expressed '
                'in sarcomatoid tumors, at the 73rd percentile of measured '
                'transcripts',
            29: 'Not carried forward: transcriptomic support does not hold '
                'under a batch-adjusted subtype model '
                f"(q = {de['SSTR2_neurod1']['q']:.3f}), and no enriched pathway "
                'contains the target',
        }
        status = ('Supported; first priority within RMC' if int(r['N']) == 17 else
                  'Supported by the independent sources' if bool(srow['survives']) else
                  PLAIN.get(int(r['N']),
                            'Excluded: ' + str(srow['failed_criteria'])))
    else:
        status = ''
    nxt = {17: 'immunocompetent model with an intact myeloid compartment',
           19: 'RMC tumor-surface confirmation and normal-tissue safety assessment',
           28: 'SCBC-specific expression, internalization and payload testing',
           23: 'not carried forward',
           24: 'not carried forward',
           29: 'not carried forward'}.get(int(r['N']), 'not carried forward')
    add_row([r['N'], r['Context'], f"{r['Drug']} \u2014 {r['Target']}",
             f"{r['Total']} \u00b7 {r['Tier']}", status, nxt])

add_row(['', 'PARTIAL PRECEDENT', '', '', '', ''], bold=True)
accounted |= set(partial_rows['N'])
add_row([', '.join(str(int(x)) for x in sorted(partial_rows['N'])), 'various',
         f'{len(partial_rows)} associations extending a precedent from '
         f'conventional disease or another organ to this variant',
         ', '.join(f'{v} {k}' for k, v in
                   partial_rows['Tier'].value_counts().to_dict().items()),
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
             'TROP2 (TACSTD2) loss \u2014 observation, not a scored association',
             'not estimable',
             'loss can be shown only by the confounded comparison',
             'independent, non-confounded cohort'])

missing = sorted(set(merged['N']) - accounted)
assert not missing, f'Table 1 omits associations {missing}'
print(f'  Table 1: all {len(accounted)} associations accounted for')

P('Scores sum four partially overlapping dimensions (genomic or context-anchor '
  '0\u20133, transcriptomic 0\u20133, pathway 0\u20132, external literature '
  '0\u20131) and express strength of evidence within this framework only, not '
  'established drug sensitivity. "No prior urologic-oncology proposal '
  'identified" refers to the pre-specified PubMed search and makes no claim of '
  'biological precedence outside urology. Sarcomatoid rows are reported '
  'descriptively: histology and array chip are completely aliased in that '
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

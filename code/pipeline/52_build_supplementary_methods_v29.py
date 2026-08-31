"""Build the v30 Supplementary Methods.

The v28 file documented the six pipeline steps only. It predates the refit, so
it described elementary per-gene tests, a fixed gene universe, and no selection
rule, none of which is what the v30 analysis does.

Writes: output/Supplementary_Methods_v31.docx
"""
import json
import re
import sys
from pathlib import Path

import paths

import docx
import pandas as pd
from docx.shared import Pt

sys.stdout.reconfigure(encoding='utf-8')
RF = paths.REFIT
OUT = paths.OUTPUT / 'Supplementary_Methods_v31.docx'
F = json.loads((RF / 'MANUSCRIPT_FACTS.json').read_text(encoding='utf-8'))
summary = pd.read_csv(RF / 'REFIT_SUMMARY.csv')
manifest = pd.read_csv(paths.PREPARED / 'PREPARED_MANIFEST.csv')

doc = docx.Document()
doc.styles['Normal'].font.name = 'Calibri'
doc.styles['Normal'].font.size = Pt(10.5)


def H(t, size=12.5, before=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(t)
    r.bold = True
    r.font.size = Pt(size)


def P(t, size=10.5, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(t)
    r.font.size = Pt(size)
    r.italic = italic


H('Supplementary Methods', 15, 0)
P('An Auditable Public-Data Framework for Prioritizing Biomarker-Matched Drug '
  'Hypotheses Across Benchmark and Rare Urologic Cancers', italic=True)
P('Brinkley GJ, Greenberg J, Caso J')

H('1. Contexts and their role')
P('Seven contexts were analyzed. Three are better-studied benchmark contexts '
  'with abundant prior literature, and serve as positive controls: their '
  'purpose is to establish what the framework returns for diseases whose '
  'therapeutic priorities are already documented. Four are rare or variant '
  'diseases for which no such reference exists. The distinction is not cosmetic: recovery of established '
  'priorities in the benchmark contexts is calibration, and cannot be counted as '
  'independent validation of the output in the discovery contexts, because prior '
  'knowledge entered the pathway panel, the drug curation and the choice of '
  'representative agent.')

H('1b. Provenance of the frozen candidate set')
P('An earlier implementation of this pipeline generated the 30-association candidate set. Association membership was frozen before design-aware refitting. The analysis reported here re-estimated the transcriptomic and pathway evidence for that fixed set, recalculated scores and tiers, and applied the eligibility and orthogonal-audit rules to it. It does not claim that the final models would independently regenerate the same thirty associations, and the changes the refit produced are themselves a result. The curated half of each row - drug, target, genomic frequency and its source, clinical stage and prior-proposal status - is deposited as data/master_row_definitions.csv; the computed half is emitted by 39_rescore_from_refit.py.')

H('2. Genomic and context-anchor input')
P('Somatic alteration frequencies for the benchmark contexts came from The '
  'Cancer Genome Atlas Pan-Cancer Atlas 2018 through the cBioPortal programmatic '
  'interface. The rare-disease contexts are not represented there, so '
  'frequencies were curated from published genomic series. Where a rare disease '
  'is defined by an alteration that is not the therapeutic target, that '
  'alteration is used as a context anchor. This is recorded explicitly because '
  'an anchor certifies that the samples represent the disease rather than '
  'providing target-specific evidence, and the score-sensitivity analysis '
  '(Supplementary Table S2) reports how far the ordering depends on it.')

H('3. Differential expression')
P('Ten Gene Expression Omnibus series were used. Each was fitted with the '
  'standard Bioconductor treatment for its platform rather than one elementary '
  'test applied uniformly, using limma 3.68.4 and edgeR 4.10.1 under R 4.6.1.')
P('Count-based series were filtered with edgeR filterByExpr against the design '
  'matrix, normalized by trimmed mean of M-values, and given voom precision '
  'weights before the linear model. Log-scale and summarized series were fitted '
  'with limma-trend, that is eBayes with an intensity-dependent prior variance '
  'and robust estimation of the hyperparameters.')
P('Three design features present in the primary deposits were modeled. First, '
  f"the penile series contains {F['design']['pscc_normal_arrays']} normal arrays "
  f"derived from only {F['design']['pscc_normal_donors']} donors; donor was "
  f"included as a blocking factor through duplicate correlation. Treating those "
  f"arrays as independent would have declared roughly twice as many features "
  f"significant. Second, the muscle-invasive bladder kinome panel is a matched "
  f"tumor-normal design and patient was included as a blocking factor. Third, "
  f"in the lineage-stratified small-cell series each subtype was contrasted "
  f"against the mean of the remaining subtypes with batch in the model.")
P('Two series could not be modeled as intended, and this is reported rather '
  'than worked around. In the sarcomatoid series every sarcomatoid sample was '
  'hybridized on a chip carrying no conventional sample and vice versa, so chip '
  'and group are completely confounded and a model including chip is not '
  'estimable; the contrast is fitted without it and the confounding is stated '
  'wherever those rows appear. For renal medullary carcinoma the repository '
  'serves only an author differential-expression spreadsheet and no sample-level '
  'matrix, so no design-aware model can be fitted from deposited data; the two '
  'patient-derived cell lines were instead treated as two independent models, '
  'not as an inferential cohort, and only genes changing consistently in both '
  'were carried forward. A gene was required to exceed a log2 fold change of '
  '0.5 in the disease-state orientation at q < 0.05 in each line separately; '
  'the reported q-value for such a gene is the larger of the two line-specific '
  'values, and the enrichment universe is the genes measured in both lines.')
P('The NanoString kinome panel carries no housekeeping probes, so the usual '
  'housekeeping normalization was unavailable. Counts were background-corrected '
  'against the negative controls, rescaled on the positive spike-ins, and passed '
  'to TMM and voom.')

H('4. Gene symbol normalization')
P('Gene symbols were mapped to current HGNC nomenclature before any enrichment '
  'test, using the HGNC complete set and its previous-symbol and alias fields, '
  'with mappings discarded where a legacy symbol is itself the current symbol of '
  'a different gene. This matters more than it sounds: the pathway definitions '
  'use current symbols while the older expression platforms use the symbols of '
  'their day, so any gene renamed in the interval was being dropped from its own '
  'pathway. Interleukin 8, now CXCL8, is the clearest instance; it is the '
  'strongest single gene in the renal medullary chemokine signal and was being '
  'excluded from the chemokine pathway it helps define.')

H('5. Pathway enrichment')
P('Eighteen pathway or gene sets were fixed before any context-specific '
  'analysis, chosen drug-class-first: each was included because it contains the '
  'target of a clinically developed drug class, so that enrichment translates '
  'into a testable drug-class hypothesis. Enrichment used the '
  'direction-specific up-regulated gene list as the query and the genes actually '
  'measured and retained in that dataset as the background, rather than a fixed '
  'transcriptome-wide count; the earlier fixed 20,000-gene universe inflated the '
  'test on targeted panels. Benjamini-Hochberg correction was applied across the '
  'eighteen sets within each context. It was not applied across contexts, across '
  'drug candidates, or across the downstream comparisons, and reported q-values '
  'should be read with that scope in mind. Two thresholds were pre-specified. '
  'Differential-expression significance is q < 0.05. Pathway enrichment uses an '
  'exploratory q < 0.10, and values between 0.05 and 0.10 are described as '
  'suggestive rather than conventionally significant. Both a q-based and a p-based '
  'gene list were run so that the dependence of each enrichment on the '
  'significance rule is visible in the deposited tables.')

KEGG_ID = {
    'Cell_Cycle': ('hsa04110', 'CDK4/6 and cell-cycle inhibitors'),
    'Apoptosis': ('hsa04210', 'BCL-2 and IAP-directed agents'),
    'HIF1_signaling': ('hsa04066', 'HIF-2alpha inhibitors'),
    'VEGF_signaling': ('hsa04370', 'VEGF/VEGFR inhibitors'),
    'Homologous_Recombination': ('hsa03440', 'PARP inhibitors'),
    'PI3K_AKT_signaling': ('hsa04151', 'PI3K, AKT and mTOR inhibitors'),
    'p53_signaling': ('hsa04115', 'MDM2 and WEE1/ATR-directed agents'),
    'Chemokine_signaling': ('hsa04062', 'CXCR1/CXCR2 antagonists'),
    'Cytokine_receptor_interaction': ('hsa04060', 'cytokine-receptor-directed biologics'),
    'Antigen_processing_presentation': ('hsa04612', 'immune-hot context marker'),
    'PDL1_PD1_checkpoint': ('hsa05235', 'PD-1/PD-L1 checkpoint inhibitors'),
    'Pentose_phosphate_pathway': ('hsa00030', 'G6PD inhibitors'),
    'Arachidonic_acid_metabolism': ('hsa00590', 'COX-1/COX-2 inhibitors'),
    'Neuroactive_ligand_receptor': ('hsa04080', 'somatostatin-receptor-directed agents'),
    'Prostate_cancer': ('hsa05215', 'disease-context set'),
    'Bladder_cancer': ('hsa05219', 'disease-context set'),
    'Renal_cell_carcinoma': ('hsa05211', 'disease-context set'),
    'Epigenetic_Regulation': ('custom', 'DNMT, EZH2, HDAC, BET and NSD-directed agents'),
}

P('The eighteen sets, their identifiers, their size at the frozen analysis date '
  'and the drug class each was included for are listed below. Seventeen are '
  'KEGG human pathways retrieved through the KEGG programmatic interface. The '
  'eighteenth, Epigenetic_Regulation, is a custom set because no single KEGG '
  'pathway spans the chromatin-directed drug classes: it is the union of the '
  'DNMT, PRC2/EZH, SWI-SNF, lysine methyltransferase, lysine demethylase, HDAC '
  'and sirtuin, histone acetyltransferase and bromodomain, and UHRF reader '
  'families, assembled from the gene families themselves and deposited in '
  'results/KEGG_PATHWAYS_18.json alongside the seventeen retrieved sets. All '
  'nineteen thousand-odd member symbols were normalized to current HGNC '
  'nomenclature before use.')

_sets = json.loads((paths.RESULTS / 'KEGG_PATHWAYS_18.json')
                   .read_text(encoding='utf-8'))
tp = doc.add_table(rows=1, cols=4)
tp.style = 'Table Grid'
for c, hh in zip(tp.rows[0].cells,
                 ('Set', 'Identifier', 'Genes', 'Included for')):
    c.paragraphs[0].add_run(hh).bold = True
for name, genes in _sets.items():
    ident, cls = KEGG_ID.get(name, ('', ''))
    row = tp.add_row()
    for c, v in zip(row.cells,
                    (name.replace('_', ' '), ident, str(len(genes)), cls)):
        c.paragraphs[0].add_run(v).font.size = Pt(8.6)
for _r in tp.rows:
    for _c in _r.cells:
        for _p in _c.paragraphs:
            for _run in _p.runs:
                _run.font.size = Pt(8.6)
doc.add_paragraph()

H('6. Prioritization score')
P('The genomic or context-anchor dimension is binned by alteration frequency in '
  'the source or disease cohort: 3 points above 30%, 2 points from 15% to 30% '
  'inclusive, 1 point from 5% up to but not including 15%, and 0 below 5% or '
  'where the gene is not assessed in the cohort. Frequencies falling exactly on '
  '15% or 30% take the higher bin. Where a disease is defined by a single '
  'alteration - renal medullary carcinoma by SMARCB1 loss, small-cell bladder '
  'cancer by TP53 and RB1 - the anchor value certifies that the samples '
  'represent the disease and says nothing about the nominated target, which is '
  'why the sensitivity analysis removes it.')
P('The literature dimension is separate from the prior-proposal audit and must '
  'not be read as its inverse. It awards 1 point for a PubMed-indexed '
  'mechanistic or clinical report linking the agent or its class to the '
  'nominated target, in any disease. The prior-proposal audit asks a narrower '
  'question: whether that pairing has been proposed in the urologic-oncology '
  'literature specifically. An association can therefore hold a mechanistic '
  'literature point from a non-urologic context and still be classified as '
  'having no prior urologic-oncology proposal; anti-CEACAM5 in ASCL1-positive '
  'small-cell bladder cancer is exactly that case. The two are kept apart so '
  'that the novelty classification cannot be an artefact of the score.')
P('Each association receives 0 to 9 points across four dimensions: genomic or '
  'context-anchor evidence (0-3, binned as above), transcriptomic '
  'evidence (0-3), pathway evidence (0-2) and external mechanistic-literature '
  'concordance (0-1). The dimensions are partially overlapping rather than '
  'independent, and are described that way: the transcriptomic and pathway '
  'dimensions derive from the same expression data, and in several rows the '
  'genomic dimension reflects a disease anchor rather than alteration of the '
  'nominated target.')
P('The transcriptomic dimension uses whichever of two arms applies. Where a '
  'disease-versus-comparator contrast exists, 3 points are given for a '
  'significant change with absolute log2 fold change at least 1, 2 for 0.5 to 1, '
  '1 for a smaller significant change, and 0 where the change does not reach '
  'q < 0.05. The absolute-expression arm applies where the available dataset '
  'does not provide an interpretable disease-state-versus-comparator contrast '
  'for the nominated target. A perturbation experiment is not automatically in '
  'this arm: the renal medullary series is a SMARCB1 rescue, and its '
  'rescued-versus-null comparison is itself an interpretable disease-state '
  'contrast, so it is scored on the contrast arm. The absolute-expression '
  'arm applies: 3 points for the top 5% of measured transcripts, 2 for the top '
  '15%, 1 for the top third. The pathway dimension gives 2 points where the '
  'pathway is enriched at the pre-specified threshold and the target is a member '
  'of that pathway’s defining set, and 1 where only one of those holds.')
P('Both data-derived dimensions are emitted by one function from the deposited '
  'fitted tables, so the manuscript table and the deposited table are generated '
  'from a shared source and reconciled by an automated check '
  '(49_audit_manuscript_v29.py). That reduces the risk of divergence; it does '
  'not make divergence logically impossible. Where a target is absent from its platform the row retains a curated '
  'value and is flagged as not re-derivable, individually, in Supplementary '
  'Table S1. Totals map to Strong (7-9), Moderate (4-6) and Exploratory (1-3) '
  'tiers, which express strength of evidence within this framework only.')

H('7. Prior-proposal audit')
P('The audit was performed after scoring was complete, so that prior proposals '
  'could not influence prioritization. For each association multiple PubMed '
  'query variants were run and reviews, position papers and trial registries '
  'examined. Novelty was assessed against urologic-oncology literature only: a '
  'prior proposal in small-cell lung, gastric or another non-urologic context '
  'does not count. The resulting label is a statement about what the '
  'pre-specified search found in the urologic literature, not a claim of '
  'biological precedence.')
P('The procedure is reported in full, including its limits. Searches were run '
  'on PubMed with no date or language restriction, using the template '
  '("<target>" OR "<drug>" OR "<drug class>") AND ("<disease>" OR its '
  'synonyms), with reviews, position papers and ClinicalTrials.gov '
  'registrations screened alongside primary reports. A primary report, review, '
  'position paper or trial registration proposing the agent or its class '
  'against the nominated target in a urologic-oncology context counts as a '
  'prior proposal; conference abstracts and patents do not. Three limits '
  'apply. The audit was performed by one author, classifications were not '
  'duplicated by a second independent reviewer, and no adjudication procedure '
  'was therefore required. The exact per-row query strings were not logged when '
  'the searches were run, so the template rather than the string is what is '
  'deposited. For these reasons the audit is described throughout as '
  'score-independent - it could not be influenced by the score, because it '
  'followed it - and not as independent in the dual-reviewer sense. The '
  'per-row classification, its supporting citations and PubMed identifiers, '
  'the template and these limits are deposited as '
  'results/refit/PRIOR_PROPOSAL_AUDIT.csv.')

H('7b. Drug-target curation and the candidate denominator')
P('A differentially expressed gene entered the association table only if it '
  'mapped to an agent that could be evaluated clinically. Candidate entry '
  'required the transcriptomic entry condition for its context, a protein '
  'product with a described binding or degradation modality, and at least one '
  'agent against it in human study. Where several agents shared a target, the '
  'representative agent was chosen by clinical stage first, then by the '
  'specificity of the target engagement, then by whether human pharmacokinetic '
  'and safety data were published; rows naming a class rather than a molecule '
  'do so because no single agent dominated on those grounds. Discontinued '
  'agents were retained where the class remains in development and are '
  'labelled as discontinued, since the hypothesis is about the target rather '
  'than the molecule. Preclinical-only agents were admitted only where no '
  'clinical-stage agent existed against the target, and are labelled as such '
  'in the clinical-stage column.')
P('The denominator behind the frozen set is deposited as '
  'results/refit/CANDIDATE_UNIVERSE.csv, and it is deliberately incomplete. '
  'For each analysis unit it records the genes tested, the genes meeting the '
  'transcriptomic entry rule, and the associations retained. It does not '
  'record how many of those genes mapped to a druggable target, or how many '
  'drug classes were considered and set aside, because the mapping was '
  'performed by hand against the Therapeutic Target Database and OpenTargets '
  'web interfaces in the earlier implementation and no query log, release '
  'snapshot or intermediate mapping file was written at the time. Those two '
  'columns are published as not reconstructible rather than estimated after '
  'the fact. This is the weakest link in the audit trail of the frozen set, '
  'and a prospective application of the pipeline should log the mapping step '
  'as the fitted steps are now logged.')

_uni = pd.read_csv(RF / 'CANDIDATE_UNIVERSE.csv')
tu = doc.add_table(rows=1, cols=5)
tu.style = 'Table Grid'
for c, hh in zip(tu.rows[0].cells,
                 ('Analysis unit', 'Genes tested', 'Meeting entry rule',
                  'Druggable genes mapped', 'Retained')):
    c.paragraphs[0].add_run(hh).bold = True
for _, r in _uni.iterrows():
    row = tu.add_row()
    for c, v in zip(row.cells,
                    (r['analysis_unit'], f"{int(r['genes_tested']):,}",
                     f"{int(r['genes_meeting_entry_rule']):,}",
                     r['druggable_genes_mapped'],
                     str(int(r['associations_retained_in_frozen_set'])))):
        c.paragraphs[0].add_run(str(v))
for _r in tu.rows:
    for _c in _r.cells:
        for _p in _c.paragraphs:
            for _run in _p.runs:
                _run.font.size = Pt(8.6)
doc.add_paragraph()
P('Counts are rows of the fitted table, which are probes on the two array '
  'platforms and genes elsewhere; the clear cell unit has no normal '
  'comparator, so its contrast count is zero by construction and its rows are '
  'scored on the absolute-expression arm. Per-unit notes are in the deposited '
  'file.')

H('8. Orthogonal evidence audit')
P('Four sources that took no part in scoring were interrogated after the table '
  'was fixed. They constitute an audit rather than a validation: each can find a '
  'candidate wanting, none can establish that a candidate works, and each is '
  'blind to some candidates by construction.')
P('Protein-level evidence came from the Human Protein Atlas: curated protein '
  'class, subcellular location, and normalized transcripts per million in normal '
  'bladder, kidney and prostate. Rows were adjudicated on the curated protein '
  'class rather than the immunofluorescence call, which derives from a small '
  'cell-line panel. Genetic dependency came from the DepMap 24Q4 CRISPR screen '
  'on the Chronos scale, restricted to urothelial lines and stratified as the '
  'framework nominates each target, by mutation where biomarker-defined and by '
  'expression tertile where the hypothesis rests on over-expression, with '
  'genotype and expression from CCLE through cBioPortal. Compound activity came '
  'from the PRISM Repurposing 19Q4 primary screen, comparing urothelial lines '
  'against NON-urothelial lines by two-sided Welch t-test with '
  'Benjamini-Hochberg correction across the compounds tested; comparing them '
  'against the whole panel would test a subset against a group containing it. '
  'Signature reversal was tested '
  'through the Enrichr interface against the LINCS L1000 chemical-perturbation '
  'libraries, with the up-perturbation library reported as an internal control '
  'so that a compound appearing in both directions can be recognized as '
  'non-specific.')
P('Two interpretive rules were fixed in advance. A tumor-cell monoculture '
  'cannot test a mechanism that runs through the microenvironment, so for such '
  'candidates the dependency and compound screens are informative only if '
  'positive and never disconfirming. And antibody, conjugate, engager and '
  'radioligand agents are absent from a small-molecule screen altogether rather '
  'than negative in it. Throughout, a layer that cannot evaluate a candidate '
  'counts as neither support nor contradiction.')

H('9. Candidate selection rule')
P('The rule was fixed before it was applied, and every exclusion in the '
  'manuscript is attributable to a named criterion. Eligibility requires, first, that the biological contrast be estimable separately from the major '
  'known technical variable: a transcript can be re-derived exactly and still be uninterpretable, and where histology is completely aliased with array chip no model can attribute a difference to biology. It then requires all '
  'four of: no prior urologic-oncology proposal identified by the audit; a total '
  'reaching Moderate tier or better; a transcriptomic component re-derivable '
  'from deposited data at q < 0.05; and an available clinical-stage agent. '
  'Survival additionally requires that no orthogonal layer contradict the '
  'candidate, and that target accessibility match the modality, so that a row '
  'whose agent acts from outside the cell requires confirmed extracellular '
  'access. The first-priority candidate within a disease additionally requires '
  'that the target itself '
  'belong to a pathway that is enriched, because an enrichment driven by other '
  'genes is not evidence for that target. The rule identifies surviving '
  'hypotheses but does not rank them across diseases. Within a disease holding '
  'more than one survivor, candidates are ordered first by whether the '
  'nominated target belongs to an enriched pathway and then by total score. '
  'Normal-tissue bulk RNA is reported for orientation and safety planning and '
  'is not used as a comparative therapeutic-window measure, because agents '
  'acting on different normal compartments cannot be ranked against each other '
  'on organ-level RNA.')

H('10. Sensitivity analyses')
P('Because the scoring dimensions overlap, the ordering was recomputed under '
  'four variants, ordering all scoreable associations numerically: removal of '
  'the context-anchor contribution, removal of the '
  'pathway dimension, removal of the literature dimension, and a requirement '
  'that the pathway dimension be credited only where the target is a member of '
  'the enriched set. Results are in Supplementary Table S2. The renal medullary '
  'CXCR1/CXCR2 candidate holds first place in that global arithmetic score '
  'ordering under the full score, under removal of the literature '
  'dimension and under the membership requirement, but falls to fourth when the '
  'context-anchor contribution is removed, which locates part of the ordering in '
  'the scoring architecture rather than in target-specific biology.')

P('This ordering is a descriptive numerical rank across all scoreable '
  'associations, used only to test how much of the ordering the score '
  'architecture carries. It is not a biological ranking, and the surviving '
  'hypotheses are not ranked against one another across diseases on the '
  'strength of it.')

H('11. Software and reproducibility')
P('Analyses ran under Python 3.10 (numpy, scipy, pandas, matplotlib, '
  'python-docx, Pillow) and R 4.6.1 with Bioconductor limma 3.68.4 and edgeR '
  '4.10.1. Every path in the deposited pipeline resolves relative to the '
  'repository root, so the code runs from a clone without editing. An '
  'independent Python implementation of the same variance-moderated linear model '
  'is deposited and used as a cross-check: on the like-for-like design the two '
  'engines agree on log-fold changes to within 2 × 10⁻¹⁴ and '
  'share 99% of significant genes. The manuscript itself is generated from the '
  'deposited result tables rather than typed, and an audit script checks '
  'sixty-nine properties of the finished document against the data. That '
  'makes divergence between the manuscript and the deposit detectable rather '
  'than impossible.')

H('12. Per-dataset design summary')
P('The table below records what was fitted for each context. The full version, '
  'including sample counts and the confounding identified, is Supplementary '
  'Table S3.')
t = doc.add_table(rows=1, cols=3)
t.style = 'Table Grid'
for c, h in zip(t.rows[0].cells, ('Context', 'Model fitted', 'Note')):
    c.text = ''
    r = c.paragraphs[0].add_run(h)
    r.bold = True
    r.font.size = Pt(8.5)
# the renal medullary series is not in the refit summary because no
# sample-level matrix exists for it; it is described explicitly instead
extra = pd.DataFrame([{ 'context': 'RMC (GSE180999)',
    'method': 'author DE spreadsheet; two independent patient-derived models',
    'notes': 'no sample-level matrix deposited; required log2FC > 0.5 and '
             'q < 0.05 separately in each model, with the larger line-specific '
             'q reported'}])
summary = pd.concat([summary, extra], ignore_index=True)
def _readable(v):
    s = str(v)
    if s in ('nan', 'NA', ''):
        return 'No preliminary expression filter was applied.'
    s = s.replace('NA of ', 'No preliminary expression filter was applied; of ')
    s = s.replace('no filter applied; of ',
                  'No preliminary expression filter was applied; of ')
    # 'of 26473 features passed expression filter; dropped 32 ...' reads as a
    # fragment; say what was removed and what remained
    m = re.search(r'of (\d+) features passed expression filter; '
                  r'dropped (\d+) non-?finite/constant rows', s)
    if m:
        total, dropped = int(m.group(1)), int(m.group(2))
        s = (f'No preliminary expression filter was applied; {dropped} '
             f'non-finite or constant rows were removed from {total:,} '
             f'features, leaving {total - dropped:,}.')
    return s[0].upper() + s[1:] if s else s

summary['notes'] = summary['notes'].map(_readable)
for _, r in summary.iterrows():
    row = t.add_row()
    for c, v in zip(row.cells, (r['context'], r['method'], str(r['notes']))):
        c.text = ''
        run = c.paragraphs[0].add_run(str(v))
        run.font.size = Pt(8)


# every table header repeats when the table breaks across a page
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

for _t in doc.tables:
    _tr = _t.rows[0]._tr
    _pr = _tr.get_or_add_trPr()
    _h = OxmlElement('w:tblHeader')
    _h.set(qn('w:val'), 'true')
    _pr.append(_h)

doc.save(str(OUT))
d2 = docx.Document(str(OUT))
print(f"Saved {OUT}")
print(f"  {sum(len(p.text.split()) for p in d2.paragraphs)} words, "
      f"{len(d2.paragraphs)} paragraphs, {len(d2.tables)} table")

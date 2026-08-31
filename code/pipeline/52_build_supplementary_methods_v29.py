"""Build the v29 Supplementary Methods.

The v28 file documented the six pipeline steps only. It predates the refit, so
it described elementary per-gene tests, a fixed gene universe, and no selection
rule, none of which is what the v29 analysis does.

Writes: output/Supplementary_Methods_v29.docx
"""
import json
import sys
from pathlib import Path

import paths

import docx
import pandas as pd
from docx.shared import Pt

sys.stdout.reconfigure(encoding='utf-8')
RF = paths.REFIT
OUT = paths.OUTPUT / 'Supplementary_Methods_v29.docx'
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
P('Seven contexts were analysed. Three are common source diseases with abundant '
  'prior literature and are used as benchmarks: their purpose is to show what '
  'the framework does where the answer is already known. Four are rare or '
  'variant diseases where the framework is asked to prioritize without a '
  'yardstick. The distinction is not cosmetic: recovery of established '
  'priorities in the benchmark contexts is calibration, and cannot be counted as '
  'independent validation of the output in the discovery contexts, because prior '
  'knowledge entered the pathway panel, the drug curation and the choice of '
  'representative agent.')

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
  'matrix, normalised by trimmed mean of M-values, and given voom precision '
  'weights before the linear model. Log-scale and summarised series were fitted '
  'with limma-trend, that is eBayes with an intensity-dependent prior variance '
  'and robust estimation of the hyperparameters.')
P('Three design features present in the primary deposits were modelled. First, '
  f"the penile series contains {F['design']['pscc_normal_arrays']} normal arrays "
  f"derived from only {F['design']['pscc_normal_donors']} donors; donor was "
  f"included as a blocking factor through duplicate correlation. Treating those "
  f"arrays as independent would have declared roughly twice as many features "
  f"significant. Second, the muscle-invasive bladder kinome panel is a matched "
  f"tumour-normal design and patient was included as a blocking factor. Third, "
  f"in the lineage-stratified small-cell series each subtype was contrasted "
  f"against the mean of the remaining subtypes with batch in the model.")
P('Two series could not be modelled as intended, and this is reported rather '
  'than worked around. In the sarcomatoid series every sarcomatoid sample was '
  'hybridised on a chip carrying no conventional sample and vice versa, so chip '
  'and group are completely confounded and a model including chip is not '
  'estimable; the contrast is fitted without it and the confounding is stated '
  'wherever those rows appear. For renal medullary carcinoma the repository '
  'serves only an author differential-expression spreadsheet and no sample-level '
  'matrix, so no design-aware model can be fitted from deposited data; the two '
  'patient-derived cell lines were instead treated as two biological replicates '
  'and only genes changing consistently in both were carried forward.')
P('The NanoString kinome panel carries no housekeeping probes, so the usual '
  'housekeeping normalisation was unavailable. Counts were background-corrected '
  'against the negative controls, rescaled on the positive spike-ins, and passed '
  'to TMM and voom.')

H('4. Gene symbol normalisation')
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
  'should be read with that scope in mind. A 10% false-discovery threshold was '
  'pre-specified for this exploratory setting; values between 5% and 10% are '
  'described as suggestive rather than significant. Both a q-based and a p-based '
  'gene list were run so that the dependence of each enrichment on the '
  'significance rule is visible in the deposited tables.')

H('6. Prioritization score')
P('Each association receives 0 to 9 points across four dimensions: genomic or '
  'context-anchor evidence (0-3, by alteration frequency), transcriptomic '
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
  'q < 0.05. Where no such contrast exists, because the series contains no '
  'comparator tissue or is a perturbation experiment, the absolute-expression '
  'arm applies: 3 points for the top 5% of measured transcripts, 2 for the top '
  '15%, 1 for the top third. The pathway dimension gives 2 points where the '
  'pathway is enriched at the pre-specified threshold and the target is a member '
  'of that pathway’s defining set, and 1 where only one of those holds.')
P('Both data-derived dimensions are emitted by one function from the deposited '
  'fitted tables, so the manuscript table and the deposited table cannot '
  'diverge. Where a target is absent from its platform the row retains a curated '
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

H('8. Orthogonal evidence audit')
P('Four sources that took no part in scoring were interrogated after the table '
  'was fixed. They constitute an audit rather than a validation: each can find a '
  'candidate wanting, none can establish that a candidate works, and each is '
  'blind to some candidates by construction.')
P('Protein-level evidence came from the Human Protein Atlas: curated protein '
  'class, subcellular location, and normalised transcripts per million in normal '
  'bladder, kidney and prostate. Rows were adjudicated on the curated protein '
  'class rather than the immunofluorescence call, which derives from a small '
  'cell-line panel. Genetic dependency came from the DepMap 24Q4 CRISPR screen '
  'on the Chronos scale, restricted to urothelial lines and stratified as the '
  'framework nominates each target, by mutation where biomarker-defined and by '
  'expression tertile where the hypothesis rests on over-expression, with '
  'genotype and expression from CCLE through cBioPortal. Compound activity came '
  'from the PRISM Repurposing 19Q4 primary screen, comparing urothelial lines '
  'against the panel by two-sided Welch t-test. Signature reversal was tested '
  'through the Enrichr interface against the LINCS L1000 chemical-perturbation '
  'libraries, with the up-perturbation library reported as an internal control '
  'so that a compound appearing in both directions can be recognised as '
  'non-specific.')
P('Two interpretive rules were fixed in advance. A tumour-cell monoculture '
  'cannot test a mechanism that runs through the microenvironment, so for such '
  'candidates the dependency and compound screens are informative only if '
  'positive and never disconfirming. And antibody, conjugate, engager and '
  'radioligand agents are absent from a small-molecule screen altogether rather '
  'than negative in it. Throughout, a layer that cannot evaluate a candidate '
  'counts as neither support nor contradiction.')

H('9. Candidate selection rule')
P('The rule was fixed before it was applied, and every exclusion in the '
  'manuscript is attributable to a named criterion. Eligibility requires all '
  'four of: no prior urologic-oncology proposal identified by the audit; a total '
  'reaching Moderate tier or better; a transcriptomic component re-derivable '
  'from deposited data at q < 0.05; and an available clinical-stage agent. '
  'Survival additionally requires that no orthogonal layer contradict the '
  'candidate, and that target accessibility match the modality, so that a row '
  'whose agent acts from outside the cell requires confirmed extracellular '
  'access. The lead candidate additionally requires that the target itself '
  'belong to a pathway that is enriched, because an enrichment driven by other '
  'genes is not evidence for that target, and among candidates meeting that '
  'condition the widest therapeutic window in the organ of origin.')

H('10. Sensitivity analyses')
P('Because the scoring dimensions overlap, the ordering was recomputed under '
  'four variants: removal of the context-anchor contribution, removal of the '
  'pathway dimension, removal of the literature dimension, and a requirement '
  'that the pathway dimension be credited only where the target is a member of '
  'the enriched set. Results are in Supplementary Table S2. The lead candidate '
  'holds first place under the full score, under removal of the literature '
  'dimension and under the membership requirement, but falls to fourth when the '
  'context-anchor contribution is removed, which locates part of the ordering in '
  'the scoring architecture rather than in target-specific biology.')

H('11. Software and reproducibility')
P('Analyses ran under Python 3.10 (numpy, scipy, pandas, matplotlib, '
  'python-docx, Pillow) and R 4.6.1 with Bioconductor limma 3.68.4 and edgeR '
  '4.10.1. Every path in the deposited pipeline resolves relative to the '
  'repository root, so the code runs from a clone without editing. An '
  'independent Python implementation of the same variance-moderated linear model '
  'is deposited and used as a cross-check: on the like-for-like design the two '
  'engines agree on log-fold changes to within 2 × 10⁻¹⁴ and '
  'share 99% of significant genes. The manuscript itself is generated from the '
  'deposited result tables, so its numbers and the deposit cannot diverge, and '
  'an audit script checks fifty-three properties of the finished document '
  'against the data.')

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
for _, r in summary.iterrows():
    row = t.add_row()
    for c, v in zip(row.cells, (r['context'], r['method'], str(r['notes'])[:90])):
        c.text = ''
        run = c.paragraphs[0].add_run(str(v))
        run.font.size = Pt(8)

doc.save(str(OUT))
d2 = docx.Document(str(OUT))
print(f"Saved {OUT}")
print(f"  {sum(len(p.text.split()) for p in d2.paragraphs)} words, "
      f"{len(d2.paragraphs)} paragraphs, {len(d2.tables)} table")

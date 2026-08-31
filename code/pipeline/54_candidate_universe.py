"""Deposit the candidate denominator, including the part that is not recoverable.

The reviewers of a paper called "auditable" are entitled to the funnel that ends
in thirty associations, not only the thirty. This script emits what the deposited
artefacts can actually support:

  genes_tested          rows in the refitted table for that context
  genes_entry_rule      genes an association could have been built from:
                        q < 0.05 and log2FC > 0.5 in the up direction, which is
                        the transcriptomic entry condition the scoring uses
  also_in_the_18...    of those, the ones that are members of the eighteen
                        pre-specified druggable sets. This is a deterministic
                        set intersection and it is the last step of the funnel
                        that can be recomputed.
  associations_retained rows of the association table anchored to that context

Two columns a complete funnel would carry are NOT emitted, because the artefacts
to reconstruct them do not exist:

  druggable_genes_mapped / drug_classes_reviewed
      The mapping from a differentially expressed gene to a clinically evaluable
      agent was performed by hand against the Therapeutic Target Database and
      OpenTargets web interfaces in the earlier implementation. No query log,
      release snapshot or intermediate mapping file was written at the time, so
      the number of genes that mapped to an agent, and the number of drug
      classes considered and set aside, cannot be recovered. They are reported
      as not reconstructible rather than estimated after the fact.

That gap is a real limitation of the frozen set and is stated as one in the
Supplementary Methods rather than papered over.

Writes: results/refit/CANDIDATE_UNIVERSE.csv
        results/refit/PRIOR_PROPOSAL_AUDIT.csv
"""
import sys
from pathlib import Path

import json

import paths
import lib_symbols
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'

Q_ENTRY = 0.05
LFC_ENTRY = 0.5

# the eighteen pre-specified druggable sets, as one gene universe
PANEL = set()
for _v in json.loads((REPO / 'results' / 'KEGG_PATHWAYS_18.json')
                     .read_text(encoding='utf-8')).values():
    PANEL |= set(lib_symbols.normalize(pd.Series(_v)).values)

# the two array platforms index by probe; the DE tables carry the annotation
_sarc = pd.read_csv(REPO / 'data' / 'DE_results' / 'SarcomatoidUC_DE_full.csv.gz')
_pen = pd.read_csv(REPO / 'data' / 'DE_results' / 'PenileSCC_DE_full.csv.gz')


def _hta(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    sym = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if sym in ('---', 'NULL', 'NAN') else sym


MAPS = {
    'SarcUC': dict(zip(_sarc['probe_id'].astype(str),
                       _sarc['gene'].astype(str).str.upper())),
    'PSCC': dict(zip(_pen['probe_id'].astype(str), _pen['gene'].map(_hta))),
}


def _symbols(unit, series):
    g = series.astype(str)
    if unit in MAPS:
        g = g.map(MAPS[unit]).fillna('')
    return set(lib_symbols.normalize(g.str.upper()).values) - {''}

# refit table -> the context label the frozen set uses
CONTEXT_OF = {
    'NEPC_CXCR7': 'NEPC', 'NEPC_DECITABINE': 'NEPC', 'NEPC_DNMT': 'NEPC',
    'MIBC_KINOME': 'MIBC', 'ccRCC_METS': 'ccRCC', 'PSCC': 'PSCC',
    'SarcUC': 'SarcUC', 'SCBC_ASCL1': 'SCBC', 'SCBC_NEUROD1': 'SCBC',
    'SCBC_POU2F3': 'SCBC', 'SCBC_YAP1': 'SCBC', 'HLRCC': 'HLRCC',
}

defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
# attribute each frozen row to the analysis unit that actually scores it
retained = defs['refit_context'].value_counts().to_dict()

NOTE = {
    'ccRCC_METS': 'no normal comparator in the series, so the entry rule is '
                  'the absolute-expression arm rather than a contrast; the '
                  'contrast count is 0 by construction',
    'PSCC': 'probe-level rows on a HTA 2.0 array; distinct genes are fewer',
    'SarcUC': 'probe-level rows; histology aliased with array chip, so the '
              'count is descriptive and no row is scored from it',
    'MIBC_KINOME': 'targeted 489-gene kinome panel, not a transcriptome',
}

rows = []
for f in sorted(RF.glob('DE_*.csv')):
    unit = f.stem[3:]
    de = pd.read_csv(f)
    qcol = next((c for c in ('q', 'adj.P.Val', 'FDR', 'q_value')
                 if c in de.columns), None)
    lcol = next((c for c in ('log2FC', 'logFC', 'l2fc')
                 if c in de.columns), None)
    if qcol is None or lcol is None:
        print(f"  skip {unit}: no q/logFC column ({list(de.columns)[:6]})")
        continue
    passing = de[(de[qcol] < Q_ENTRY) & (de[lcol] > LFC_ENTRY)]
    in_panel = _symbols(unit, passing['gene']) & PANEL
    rows.append({
        'analysis_unit': unit,
        'context': CONTEXT_OF.get(unit, unit),
        'genes_tested': len(de),
        'genes_meeting_entry_rule': len(passing),
        'also_in_the_18_pre_specified_sets': len(in_panel),
        'entry_rule': f'q < {Q_ENTRY} and log2FC > {LFC_ENTRY} (up)',
        'druggable_genes_mapped': 'not reconstructible',
        'drug_classes_reviewed': 'not reconstructible',
        'note': NOTE.get(unit, ''),
    })

# renal medullary carcinoma has no sample-level matrix; its entry rule is the
# both-lines consistency filter, which is recorded in its own table
rmc = pd.read_csv(RF / 'RMC_REANALYSIS.csv')
rows.append({
    'analysis_unit': 'RMC',
    'context': 'RMC',
    'genes_tested': len(rmc),
    'genes_meeting_entry_rule': int(rmc['up_both'].sum()),
    'also_in_the_18_pre_specified_sets': len(
        _symbols('RMC', rmc.loc[rmc['up_both'], 'gene']) & PANEL),
    'entry_rule': 'up in both patient-derived models (q < 0.05, log2FC > 0.5 '
                  'in each)',
    'druggable_genes_mapped': 'not reconstructible',
    'drug_classes_reviewed': 'not reconstructible',
    'note': 'no sample-level matrix is deposited; counts come from the author '
            'differential-expression tables for the two models',
})

uni = pd.DataFrame(rows)
uni['associations_retained_in_frozen_set'] = (
    uni['analysis_unit'].map(lambda u: retained.get(u, 0)))
assert uni['associations_retained_in_frozen_set'].sum() == len(defs), (
    'every frozen row must be attributed to exactly one analysis unit')
uni = uni[['analysis_unit', 'context', 'genes_tested',
           'genes_meeting_entry_rule', 'also_in_the_18_pre_specified_sets',
           'entry_rule', 'druggable_genes_mapped', 'drug_classes_reviewed',
           'associations_retained_in_frozen_set', 'note']]

uni.to_csv(RF / 'CANDIDATE_UNIVERSE.csv', index=False)
print(f"CANDIDATE_UNIVERSE.csv  {len(uni)} analysis units, "
      f"{int(uni['associations_retained_in_frozen_set'].sum())} associations")
print(uni[['analysis_unit', 'genes_tested', 'genes_meeting_entry_rule',
           'also_in_the_18_pre_specified_sets',
           'associations_retained_in_frozen_set']].to_string(index=False))
print(f"\nfunnel: {int(uni['genes_meeting_entry_rule'].sum()):,} gene-context "
      f"pairs meet a transcriptomic entry rule -> "
      f"{int(uni['also_in_the_18_pre_specified_sets'].sum()):,} of those are "
      f"also members of the 18 pre-specified sets -> "
      f"{int(uni['associations_retained_in_frozen_set'].sum())} retained.")
print("the last step is the one that was not logged: which of those genes had "
      "a clinically\nevaluable agent, and which agent was chosen where several "
      "existed.")

# --------------------------------------------------------------------------
# prior-proposal audit, deposited per row with its classification and the
# query template. The per-row query strings were not logged when the audit was
# run; the template is given so the search is reproducible, and the absence of
# the strings is recorded in the file itself rather than only in the prose.
# --------------------------------------------------------------------------
TEMPLATE = ('("<target>" OR "<drug>" OR "<drug class>") AND '
            '("<disease>" OR "<disease synonyms>") — PubMed, all years, '
            'no language limit; reviews, position papers and '
            'ClinicalTrials.gov registrations screened alongside primary '
            'reports')

audit = defs[['N', 'Context', 'Drug', 'Target', 'Prior status']].copy()
audit.columns = ['row', 'context', 'drug', 'target', 'classification']
audit['query_template'] = TEMPLATE
audit['exact_query_string_logged'] = 'no'
audit['reviewers'] = 1
audit['classifications_duplicated'] = 'no'
audit['adjudication'] = 'not applicable (single reviewer)'
audit['counts_as_prior_proposal'] = (
    'primary report, review, position paper or trial registration proposing '
    'the agent or its class against the nominated target in a '
    'urologic-oncology context; conference abstracts and patents were not '
    'treated as prior proposals')
audit.to_csv(RF / 'PRIOR_PROPOSAL_AUDIT.csv', index=False)
print(f"\nPRIOR_PROPOSAL_AUDIT.csv  {len(audit)} rows")
print(audit['classification'].value_counts().to_string())

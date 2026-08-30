"""Separate the Master Table's curated inputs from its computed scores.

In v26-v28 the Master Table was a hard-coded list in which every score component
was typed by hand, which is why the deposited CSV and the manuscript table could
drift apart and why 13 of 30 transcriptomic components could not be re-derived.

This splits the table in two:

  curated   what a human must supply - the drug, the target, the genomic
            frequency and its published source, clinical stage, prior-proposal
            status, and which dataset/gene the row is nominated on
  computed  everything derivable from data - the transcriptomic component, the
            pathway component, the total and the tier

Only the curated half is written here, as data rather than code. 39_rescore.py
computes the rest.

Writes: data/master_row_definitions.csv
"""
import ast
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'code' / 'pipeline' / '11_master_table_uniform.py'
OUT = REPO / 'data' / 'master_row_definitions.csv'

src = SRC.read_text(encoding='utf-8')
seg = src[src.index('MASTER_ROWS = ['):]
seg = seg[:seg.index('\n]') + 2]
rows = ast.literal_eval(seg.split('=', 1)[1].strip())

# row -> (evidence arm, refit context, gene symbol used for scoring)
# "de"         a disease-vs-comparator contrast exists in the refit
# "expression" no such contrast exists, so the row is scored on absolute
#              expression rank within its own dataset (NEPC perturbation
#              experiments; the ccRCC series contains no normal tissue)
SCORING = {
    1:  ('expression', 'NEPC_DECITABINE', 'BCL2'),
    2:  ('de',         'NEPC_CXCR7',      'AURKA'),
    3:  ('expression', 'NEPC_DECITABINE', 'EZH2'),
    4:  ('de',         'NEPC_DNMT',       'DNMT1'),
    5:  ('expression', 'NEPC_DECITABINE', 'TP53'),
    6:  ('expression', 'NEPC_DECITABINE', 'PARP1'),
    7:  ('de',         'MIBC_KINOME',     'AURKA'),
    8:  ('expression', 'MIBC_KINOME',     'ATM'),
    9:  ('de',         'MIBC_KINOME',     'PIK3CA'),
    10: ('de',         'MIBC_KINOME',     'FGFR3'),
    11: ('expression', 'MIBC_KINOME',     'NECTIN4'),
    12: ('expression', 'MIBC_KINOME',     'CD274'),
    13: ('de',         'MIBC_KINOME',     'CDK4'),
    # The ccRCC rows are scored on the ccRCC series, which contains tumours
    # only, so the framework's absolute-expression arm applies. GSE157256 is
    # hereditary leiomyomatosis RCC - a different disease - and is reported as
    # adjacent-disease mechanistic support rather than used to score these rows.
    14: ('expression', 'ccRCC_METS',      'KDR'),
    15: ('expression', 'ccRCC_METS',      'EPAS1'),
    16: ('expression', 'ccRCC_METS',      'CDK4'),
    17: ('de',         'RMC',             'CXCL8'),
    18: ('de',         'RMC',             'HBEGF'),
    19: ('de',         'RMC',             'CEACAM1'),
    20: ('de',         'PSCC',            'HLA-DRA'),
    21: ('de',         'PSCC',            'MMP1'),
    22: ('de',         'PSCC',            'POSTN'),
    23: ('de',         'SarcUC',          'NSD2'),
    24: ('de',         'SarcUC',          'ATR'),
    25: ('de',         'SarcUC',          'UHRF1'),
    26: ('de',         'SarcUC',          'G6PD'),
    27: ('de',         'SarcUC',          'TACSTD2'),
    28: ('de',         'SCBC_ASCL1',      'CEACAM5'),
    29: ('de',         'SCBC_NEUROD1',    'SSTR2'),
    30: ('de',         'SCBC_POU2F3',     'PTGS1'),
}

# the pathway whose enrichment, if any, the row's pathway component may draw on;
# None means the row is nominated on expression alone and takes P = 0
PATHWAY = {
    2: 'Neuroactive_ligand_receptor', 3: 'Epigenetic_Regulation',
    4: 'Epigenetic_Regulation', 5: 'p53_signaling', 7: 'Cell_Cycle',
    13: 'Cell_Cycle', 14: 'VEGF_signaling', 15: 'HIF1_signaling',
    17: 'Chemokine_signaling', 18: 'Chemokine_signaling',
    19: 'Cytokine_receptor_interaction', 20: 'Antigen_processing_presentation',
    21: 'Cytokine_receptor_interaction', 22: 'Cytokine_receptor_interaction',
    23: 'Epigenetic_Regulation', 24: 'Cell_Cycle', 25: 'Epigenetic_Regulation',
    26: 'Pentose_phosphate_pathway', 29: 'Neuroactive_ligand_receptor',
    30: 'Arachidonic_acid_metabolism',
}

# Agent status corrections that the hard-coded v26 rows never carried. These
# are stated in the v28 manuscript text but were absent from the row data, so
# the selection rule could not see them.
STAGE_OVERRIDE = {
    28: ('Phase III in NSCLC; lead agent tusamitamab ravtansine DISCONTINUED '
         'Dec 2023 after CARMEN-LC03. Class remains of interest only if a '
         'successor anti-CEACAM5 conjugate is in active development - verify '
         'before submission.'),
}

recs = []
for r in rows:
    n = r[0]
    arm, ctx, gene = SCORING[n]
    recs.append({
        'N': n, 'Context': r[1], 'Drug': r[2], 'Target': r[3],
        'genomic_score_curated': r[4], 'literature_score_curated': r[7],
        'Stage': STAGE_OVERRIDE.get(n, r[8]),
        'Prior status': r[9], 'Trial readiness': r[10],
        'scoring_arm': arm, 'refit_context': ctx, 'scoring_gene': gene,
        'pathway_for_component': PATHWAY.get(n, ''),
        'published_E': r[5], 'published_P': r[6],
    })

df = pd.DataFrame(recs)
df.to_csv(OUT, index=False)
print(f"wrote {len(df)} curated row definitions to {OUT}")
print(df.groupby(['scoring_arm'])['N'].count().to_string())
print("\nrows per refit context:")
print(df['refit_context'].value_counts().to_string())

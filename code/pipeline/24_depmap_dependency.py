"""Orthogonal functional check: are the nominated targets genetic dependencies?

Every association in Master Table 1 is nominated from transcript abundance.
Abundance says a target is present; it does not say the cancer cell needs it.
DepMap CRISPR knockout screens (Chronos gene effect) answer the second question
directly, in the disease lineage of interest, using data entirely independent of
the Gene Expression Omnibus datasets used to build the table.

One distinction is essential to interpreting this correctly, and is enforced
below rather than left to the reader. Genetic dependency is the right test for a
target whose drug INHIBITS or DEGRADES it - NSD2, UHRF1, ATR, G6PD, EZH2, DNMT1,
AURKA, PARP1, CDK4/6, EGFR, FGFR3, EPAS1, BCL2. It is the WRONG test for a
target addressed by an antibody, antibody-drug conjugate, engager or radioligand
- NECTIN4, TACSTD2, CEACAM5, CEACAM1, SSTR2, DLL3 - because those agents kill
through a delivered payload or recruited immune effector, not by removing the
target's function. A surface antigen can be an excellent ADC target while being
entirely dispensable for cell survival. Those rows are therefore reported but
explicitly marked as not evaluable by this method.

Chronos scale: 0 = no effect, -1 = median common-essential gene. A gene effect
below -0.5 is conventionally treated as a dependency.

Writes: results/DEPMAP_DEPENDENCY.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
SCRATCH = Path(r"C:\Users\garre\AppData\Local\Temp\claude\C--Users-garre"
               r"\6e817035-d63f-47ec-a06b-299c00bcd5aa\scratchpad")
CRISPR = SCRATCH / 'CRISPRGeneEffect.csv'
LINES = REPO / 'results' / 'DEPMAP_CELL_LINES.csv'
OUT = REPO / 'results' / 'DEPMAP_DEPENDENCY.csv'

DEPENDENCY_THRESHOLD = -0.5

# gene -> (Master Table rows, modality, is genetic dependency the right test?)
TARGETS = {
    # sarcomatoid UC - the rows this analysis is really for
    'NSD2':    ('23', 'KTX-1001, methyltransferase inhibitor', True),
    'UHRF1':   ('25', 'UM-002, PROTAC degrader', True),
    'ATR':     ('24', 'ceralasertib class, kinase inhibitor', True),
    'G6PD':    ('26', '6-aminonicotinamide, metabolic inhibitor', True),
    'PHC2':    ('23', 'co-enriched epigenetic regulator (not drugged)', True),
    'ATRIP':   ('24', 'the transcript actually scored for row 24', True),
    'PLA2G4A': ('30', 'upstream partner of PTGS1 in the POU2F3 cascade', True),
    # not in Master Table 1: tests a panel-coverage gap identified in the
    # Discussion - no proteasome gene set was pre-specified, so bortezomib in
    # renal medullary carcinoma could not have been surfaced
    'PSMB5':   ('n/a', 'bortezomib target (panel-coverage gap probe)', True),
    'SMARCB1': ('n/a', 'renal medullary carcinoma context anchor', True),
    # other inhibitor/degrader targets across the table
    'BCL2':    ('1',  'venetoclax, BH3 mimetic', True),
    'AURKA':   ('2, 7', 'alisertib, kinase inhibitor', True),
    'EZH2':    ('3',  'tazemetostat, methyltransferase inhibitor', True),
    'DNMT1':   ('4',  'decitabine, hypomethylating agent', True),
    'PARP1':   ('6, 8', 'olaparib / talazoparib', True),
    'PIK3CA':  ('9',  'alpelisib', True),
    'FGFR3':   ('10', 'erdafitinib', True),
    'CDK4':    ('13, 16', 'palbociclib / abemaciclib', True),
    'CDK6':    ('13, 16', 'palbociclib / abemaciclib', True),
    'EPAS1':   ('15', 'belzutifan, HIF2a antagonist', True),
    'KDR':     ('14', 'pazopanib, VEGFR multikinase', True),
    'EGFR':    ('18', 'erlotinib', True),
    'PTGS1':   ('30', 'aspirin / celecoxib', True),
    # antibody / ADC / engager / radioligand targets - dependency is NOT the test
    'NECTIN4': ('11', 'enfortumab vedotin (ADC)', False),
    'TACSTD2': ('27', 'sacituzumab govitecan (ADC) - negative biomarker', False),
    'CEACAM1': ('19', 'CM24 (antibody)', False),
    'CEACAM5': ('28', 'anti-CEACAM5 ADC', False),
    'SSTR2':   ('29', '177Lu-DOTATATE (radioligand)', False),
    'DLL3':    ('3.3', 'tarlatamab (engager), post hoc', False),
    # calibration controls
    'RPL5':    ('control', 'common-essential positive control', True),
    'POLR2A':  ('control', 'common-essential positive control', True),
    'GFP':     ('control', 'non-expressed negative control', True),
}

lines_df = pd.read_csv(LINES)
context_of = dict(zip(lines_df['ModelID'], lines_df['context']))
name_of = dict(zip(lines_df['ModelID'], lines_df['cell_line']))

# DepMap column headers are "SYMBOL (entrez)"; read the header first so only the
# needed columns are parsed out of a 429 MB file.
header = pd.read_csv(CRISPR, nrows=0)
col_for = {}
for col in header.columns:
    sym = col.split(' (')[0].strip()
    if sym in TARGETS and sym not in col_for:
        col_for[sym] = col
missing = [g for g in TARGETS if g not in col_for]
print(f"resolved {len(col_for)} of {len(TARGETS)} target columns")
if missing:
    print(f"not present in DepMap: {missing}")

usecols = [header.columns[0]] + list(col_for.values())
df = pd.read_csv(CRISPR, usecols=usecols)
df = df.rename(columns={header.columns[0]: 'ModelID'})
df = df.rename(columns={v: k for k, v in col_for.items()})
print(f"gene effect matrix: {df.shape[0]} cell lines x {len(col_for)} targets")

df['context'] = df['ModelID'].map(context_of)
uro = df[df['context'] == 'urothelial']
renal = df[df['context'].isin(['renal', 'renal medullary'])]
print(f"urothelial lines screened: {len(uro)}   renal lines screened: {len(renal)}")

rows = []
for gene, (mtrows, modality, evaluable) in TARGETS.items():
    if gene not in df.columns:
        continue
    allv = df[gene].dropna()
    urov = uro[gene].dropna()
    renv = renal[gene].dropna()
    if urov.empty:
        continue
    frac_dep = float((urov < DEPENDENCY_THRESHOLD).mean() * 100)
    pan_mean = float(allv.mean())
    uro_mean = float(urov.mean())

    if not evaluable:
        verdict = 'not evaluable - payload/effector modality, target need not be essential'
    elif pan_mean < DEPENDENCY_THRESHOLD and frac_dep >= 80:
        verdict = 'common essential (dependency, but not lineage-selective)'
    elif uro_mean < DEPENDENCY_THRESHOLD:
        verdict = 'DEPENDENCY in urothelial lines'
    elif frac_dep >= 25:
        verdict = f'dependency in a subset ({frac_dep:.0f}% of lines)'
    else:
        verdict = 'not a dependency'

    rows.append({
        'gene': gene, 'master_table_rows': mtrows, 'modality': modality,
        'dependency_is_the_right_test': evaluable,
        'n_urothelial_lines': len(urov),
        'mean_gene_effect_urothelial': round(uro_mean, 3),
        'mean_gene_effect_pan_cancer': round(pan_mean, 3),
        'selectivity_uro_minus_pan': round(uro_mean - pan_mean, 3),
        'pct_urothelial_lines_dependent': round(frac_dep, 1),
        'mean_gene_effect_renal': round(float(renv.mean()), 3) if not renv.empty else None,
        'verdict': verdict,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

show = ['gene', 'master_table_rows', 'mean_gene_effect_urothelial',
        'mean_gene_effect_pan_cancer', 'pct_urothelial_lines_dependent', 'verdict']
print("\n" + out[show].to_string(index=False))
print(f"\nWrote {OUT}")

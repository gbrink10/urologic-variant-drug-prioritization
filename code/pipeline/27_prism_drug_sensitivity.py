"""Compound-level validation against the PRISM Repurposing screen.

DepMap asks whether a cell needs a GENE. PRISM asks whether an actual COMPOUND
kills a cell, which is one step closer to the clinical question. This script
takes the drugs nominated in Master Table 1 and reads their measured viability
effect in the lineages of interest.

Data: PRISM Repurposing 19Q4 primary screen (Corsello et al., Nat Cancer 2020),
figshare DOI 10.6084/m9.figshare.9393293. Values are log2 fold-change viability
after 5 days at ~2.5 uM; MORE NEGATIVE MEANS MORE KILLING, the same sign
convention as DepMap gene effect and the reverse of the expression fold changes
used elsewhere in this study.

Two interpretive rules are enforced rather than left to the reader:

  * A monoculture viability screen cannot test a mechanism that runs through the
    microenvironment. The CXCR1/CXCR2 candidates are proposed to act by blocking
    myeloid recruitment, so a tumour-cell-autonomous readout is the wrong test
    for them - informative only if positive, never disconfirming.
  * Antibody, ADC, engager and radioligand agents are not in a small-molecule
    screen at all and are simply absent.

Writes: results/PRISM_DRUG_SENSITIVITY.csv
"""
import sys
from pathlib import Path

import paths

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
SCRATCH = paths.DATA / 'cache'   # large third-party downloads; see README for how to populate
OUT = REPO / 'results' / 'PRISM_DRUG_SENSITIVITY.csv'

SENSITIVE = -0.5          # log2 fold-change viability treated as a response

# drug (as named in PRISM) -> (Master Table rows, note, is monoculture the right test?)
DRUGS = {
    'reparixin':    ('17', 'CXCR1/CXCR2 antagonist', False),
    'navarixin':    ('17', 'CXCR1/CXCR2 antagonist', False),
    'AZD5069':      ('17', 'CXCR1/CXCR2 antagonist', False),
    'danirixin':    ('17', 'CXCR1/CXCR2 antagonist', False),
    'erlotinib':    ('18', 'EGFR inhibitor, RMC positive control', True),
    'VE-822':       ('24', 'ATR inhibitor (berzosertib)', True),
    'polydatin':    ('26', 'nominated with 6-aminonicotinamide for G6PD', True),
    'celecoxib':    ('30', 'COX inhibitor', True),
    'aspirin':      ('30', 'COX inhibitor', True),
    'venetoclax':   ('1',  'BCL2 inhibitor', True),
    'alisertib':    ('2, 7', 'aurora kinase inhibitor', True),
    'tazemetostat': ('3',  'EZH2 inhibitor', True),
    'decitabine':   ('4',  'hypomethylating agent', True),
    'azacitidine':  ('4',  'hypomethylating agent', True),
    'olaparib':     ('6',  'PARP inhibitor', True),
    'talazoparib':  ('8',  'PARP inhibitor', True),
    'alpelisib':    ('9',  'PI3K inhibitor', True),
    'erdafitinib':  ('10', 'FGFR inhibitor', True),
    'palbociclib':  ('13', 'CDK4/6 inhibitor', True),
    'abemaciclib':  ('16', 'CDK4/6 inhibitor', True),
    'pazopanib':    ('14', 'VEGFR multikinase inhibitor', True),
    'marimastat':   ('21', 'MMP inhibitor', True),
    'bortezomib':   ('n/a', 'proteasome inhibitor - panel-coverage probe and '
                            'pan-active positive control', True),
}

lfc = pd.read_csv(SCRATCH / 'prism_primary_lfc.csv', index_col=0)
treat = pd.read_csv(SCRATCH / 'prism_treatment_info.csv')
cells = pd.read_csv(SCRATCH / 'prism_cellline_info.csv')
print(f"PRISM primary screen: {lfc.shape[0]} cell lines x {lfc.shape[1]} treatments")

tissue = dict(zip(cells['depmap_id'], cells['primary_tissue'].astype(str)))
uro_ids = [i for i in lfc.index if 'urinary' in tissue.get(i, '')]
kid_ids = [i for i in lfc.index if 'kidney' in tissue.get(i, '')]
RMC_ID = 'ACH-001163'                     # the renal medullary carcinoma line
print(f"urothelial lines {len(uro_ids)} | kidney lines {len(kid_ids)} | "
      f"RMC line present: {RMC_ID in lfc.index}")

cols_for = {}
for name in DRUGS:
    sel = treat[treat['name'].astype(str).str.lower() == name.lower()]
    cols = [c for c in sel['column_name'] if c in lfc.columns]
    if cols:
        cols_for[name] = cols

rows = []
for name, (mtrows, note, monoculture_valid) in DRUGS.items():
    if name not in cols_for:
        rows.append({'drug': name, 'master_table_rows': mtrows, 'note': note,
                     'verdict': 'not in PRISM'})
        continue
    # average across doses/screens for that compound
    vals = lfc[cols_for[name]].mean(axis=1)
    allv = vals.dropna()
    urov = vals.reindex(uro_ids).dropna()
    kidv = vals.reindex(kid_ids).dropna()
    rmc = vals.get(RMC_ID, np.nan)

    p_uro = (float(stats.mannwhitneyu(urov, allv, alternative='less').pvalue)
             if len(urov) >= 3 else np.nan)
    rmc_pct = float((allv < rmc).mean() * 100) if pd.notna(rmc) else np.nan

    if not monoculture_valid:
        verdict = ('active in monoculture despite microenvironment rationale'
                   if pd.notna(rmc) and rmc < SENSITIVE
                   else 'no tumour-cell-autonomous activity (expected; '
                        'mechanism is microenvironmental and untestable here)')
    elif allv.mean() < -1 and (allv < SENSITIVE).mean() > 0.8:
        verdict = 'broadly cytotoxic (active but not selective)'
    elif len(urov) and urov.mean() < SENSITIVE:
        verdict = 'active in urothelial lines'
    elif pd.notna(rmc) and rmc < SENSITIVE:
        verdict = 'active in the RMC line specifically'
    else:
        verdict = 'not active at screened dose'

    rows.append({
        'drug': name, 'master_table_rows': mtrows, 'note': note,
        'monoculture_is_valid_test': monoculture_valid,
        'n_lines': len(allv),
        'mean_lfc_all_lines': round(float(allv.mean()), 3),
        'mean_lfc_urothelial': round(float(urov.mean()), 3) if len(urov) else None,
        'mean_lfc_kidney': round(float(kidv.mean()), 3) if len(kidv) else None,
        'lfc_RMC_line': round(float(rmc), 3) if pd.notna(rmc) else None,
        'RMC_percentile_of_all_lines': round(rmc_pct, 1) if pd.notna(rmc_pct) else None,
        'pct_all_lines_sensitive': round(float((allv < SENSITIVE).mean() * 100), 1),
        'p_urothelial_vs_all': f'{p_uro:.3g}' if pd.notna(p_uro) else None,
        'verdict': verdict,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
show = ['drug', 'master_table_rows', 'mean_lfc_all_lines', 'mean_lfc_urothelial',
        'lfc_RMC_line', 'pct_all_lines_sensitive', 'verdict']
print("\n" + out[[c for c in show if c in out.columns]].to_string(index=False))
print(f"\nWrote {OUT}")

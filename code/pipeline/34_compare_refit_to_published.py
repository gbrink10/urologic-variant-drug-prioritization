"""Compare the v29 design-aware refit against the numbers v28 quotes.

Every value the manuscript states in text is checked against the refit, so the
revision can report exactly which claims survive, which move, and which do not
hold up once the design is modelled properly.

Writes: results/refit/REFIT_VS_PUBLISHED.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
DE = REPO / 'data' / 'DE_results'

# probe -> gene maps from the deposited platform annotation
maps = {}
sarc = pd.read_csv(DE / 'SarcomatoidUC_DE_full.csv.gz')
maps['SarcUC'] = dict(zip(sarc['probe_id'].astype(str), sarc['gene'].astype(str)))
# HTA-2.0 annotation is "accession // SYMBOL // description // locus // entrez",
# optionally repeated with "///" separators, so the symbol is the second field
pen = pd.read_csv(DE / 'PenileSCC_DE_full.csv.gz')


def hta_symbol(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    sym = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if sym in ('---', 'NULL', 'NAN') else sym


pen['sym'] = pen['gene'].map(hta_symbol)
maps['PSCC'] = dict(zip(pen['probe_id'].astype(str), pen['sym']))


def load(ctx):
    df = pd.read_csv(RF / f'DE_{ctx}.csv')
    df['gene'] = df['gene'].astype(str)
    if ctx in maps:
        df['symbol'] = df['gene'].map(maps[ctx]).fillna(df['gene'])
    else:
        df['symbol'] = df['gene'].str.upper()
    return df


def lookup(ctx, symbol):
    df = load(ctx)
    s = df[df['symbol'].astype(str).str.upper() == symbol.upper()]
    if not len(s):
        return None
    # a gene can appear on several probes; report the most significant
    s = s.sort_values('P.Value')
    return s.iloc[0]


# claim -> (context, gene, published logFC, published q or None, what it supports)
CLAIMS = [
    ('PSCC', 'HLA-DRA', 9.01, None, 'penile immune-hot phenotype; pembrolizumab row'),
    ('PSCC', 'CXCL9', None, None, 'penile immune-hot phenotype'),
    ('PSCC', 'CXCL10', None, None, 'penile immune-hot phenotype'),
    ('SarcUC', 'TACSTD2', -2.06, None, 'TROP2-low negative biomarker (row 27)'),
    ('SarcUC', 'NSD2', None, None, 'framework-novel NSD2 row 23'),
    ('SarcUC', 'WHSC1', None, None, 'framework-novel NSD2 row 23 (alias)'),
    ('SarcUC', 'ATR', None, None, 'framework-novel ATR row 24'),
    ('SarcUC', 'UHRF1', None, None, 'partially novel UHRF1 row 25'),
    ('SarcUC', 'G6PD', None, None, 'partially novel G6PD row 26'),
    ('SCBC_ASCL1', 'CEACAM5', 6.19, None, 'framework-novel anti-CEACAM5 row 28'),
    ('SCBC_ASCL1', 'DLL3', 1.42, 0.42, 'DLL3 false-negative analysis, Section 3.6'),
    ('SCBC_NEUROD1', 'SSTR2', 2.16, None, 'framework-novel Lu-DOTATATE row 29'),
    ('SCBC_POU2F3', 'PLA2G4A', None, None, 'COX inhibition row 30'),
    ('SCBC_POU2F3', 'PTGS1', None, None, 'COX inhibition row 30'),
    ('MIBC_KINOME', 'ERBB2', None, None, 'MIBC kinome context'),
    ('MIBC_KINOME', 'FGFR3', None, None, 'erdafitinib row'),
    ('NEPC_CXCR7', 'AURKA', None, None, 'alisertib row (CXCR7-AURKA axis)'),
    ('HLRCC', 'EPAS1', None, None, 'belzutifan row (adjacent-disease support)'),
]

rows = []
print(f"{'context':<16}{'gene':<10}{'published':>10}{'refit logFC':>13}"
      f"{'refit P':>11}{'refit q':>11}  verdict")
print('-' * 92)
for ctx, gene, pub_fc, pub_q, note in CLAIMS:
    r = lookup(ctx, gene)
    if r is None:
        print(f"{ctx:<16}{gene:<10}{'-':>10}{'NOT FOUND':>13}")
        rows.append({'context': ctx, 'gene': gene, 'published_log2FC': pub_fc,
                     'refit_log2FC': np.nan, 'refit_P': np.nan, 'refit_q': np.nan,
                     'verdict': 'not measured on this platform', 'supports': note})
        continue
    fc, p, q = float(r['logFC']), float(r['P.Value']), float(r['adj.P.Val'])
    if pub_fc is None:
        verdict = 'direction ' + ('up' if fc > 0 else 'down') + \
                  (', q<0.05' if q < 0.05 else ', not significant')
    else:
        same_dir = np.sign(fc) == np.sign(pub_fc)
        close = abs(fc - pub_fc) < max(0.5, 0.25 * abs(pub_fc))
        verdict = ('reproduced' if same_dir and close else
                   'same direction, different magnitude' if same_dir else
                   'DIRECTION REVERSED')
        if q >= 0.05:
            verdict += '; not significant after refit'
    print(f"{ctx:<16}{gene:<10}{'' if pub_fc is None else f'{pub_fc:+.2f}':>10}"
          f"{fc:>+13.2f}{p:>11.2e}{q:>11.2e}  {verdict}")
    rows.append({'context': ctx, 'gene': gene, 'published_log2FC': pub_fc,
                 'published_q': pub_q, 'refit_log2FC': round(fc, 4),
                 'refit_P': p, 'refit_q': q, 'refit_AveExpr': float(r['AveExpr']),
                 'verdict': verdict, 'supports': note})

out = pd.DataFrame(rows)
out.to_csv(RF / 'REFIT_VS_PUBLISHED.csv', index=False)
print(f"\nwrote {RF / 'REFIT_VS_PUBLISHED.csv'}")

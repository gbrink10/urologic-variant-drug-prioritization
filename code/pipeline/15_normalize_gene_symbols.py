"""Normalise the `gene` column of the deposited DE table to clean HGNC symbols.

The penile SCC rows carry raw Affymetrix probeset annotation strings, e.g.

    NM_019111 // HLA-DRA // major histocompatibility complex, class II, DR
    alpha // 6p21.3 // 3122 /// BC032350 // HLA-DRA // ...

which makes the deposited table impossible to key by gene and therefore
impossible for a reader to audit a specific score against. This script adds a
`gene_symbol` column carrying the parsed symbol (unchanged where the `gene`
column already holds a clean symbol) and keeps the original string in
`gene_annotation_raw` for provenance.

Also stamps the RMC rows with an explicit disease-state orientation column so
the sign convention cannot be misread: the deposited RMC contrast is
rescue-vs-null, so log2FC_disease_state = -mean_l2fc_48h.

Rewrites: data/DE_results/FULL_DE_RESULTS_ALL10.csv
"""
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
PATH = REPO / 'data' / 'DE_results' / 'FULL_DE_RESULTS_ALL10.csv'


def parse_symbol(value: str) -> str:
    """Extract the HGNC symbol from an Affymetrix annotation string."""
    if not isinstance(value, str):
        return value
    if '//' not in value:
        return value.strip()
    # first transcript block: "ACCESSION // SYMBOL // description // ..."
    first_block = value.split('///')[0]
    parts = [p.strip() for p in first_block.split('//')]
    if len(parts) >= 2 and parts[1] and parts[1] != 'NULL':
        return parts[1]
    return value.strip()


df = pd.read_csv(PATH)
raw_is_annotation = df['gene'].astype(str).str.contains('//', na=False)
print(f"{int(raw_is_annotation.sum())} of {len(df)} rows carry raw annotation strings")

df['gene_annotation_raw'] = df['gene'].where(raw_is_annotation)
df['gene_symbol'] = df['gene'].map(parse_symbol)

# Explicit disease-state orientation for the RMC cell-line rescue contrast.
is_rmc = df['context'] == 'RMC'
df.loc[is_rmc, 'log2FC_disease_state'] = -df.loc[is_rmc, 'mean_l2fc_48h']
df.loc[is_rmc, 'comparison'] = (
    'SMARCB1-null vs SMARCB1-rescue (disease state vs rescued control); '
    'raw l2fc columns are rescue-vs-null, so log2FC_disease_state = -mean_l2fc_48h'
)
df.loc[~is_rmc, 'log2FC_disease_state'] = df.loc[~is_rmc, 'log2fc']

df.to_csv(PATH, index=False)
print(f"Wrote {PATH}")

check = ['HLA-DRA', 'MMP1', 'POSTN', 'CXCL10', 'WHSC1', 'SSTR2', 'IL8']
print("\nSpot-check of newly keyable symbols:")
for g in check:
    sub = df[df['gene_symbol'].astype(str).str.upper() == g]
    if sub.empty:
        print(f"  {g:<9} not present")
        continue
    r = sub.iloc[0]
    print(f"  {g:<9} context={r['context']:<22} "
          f"log2FC_disease={float(r['log2FC_disease_state']):+.3f}")

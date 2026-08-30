"""Build a legacy -> current gene symbol map from the HGNC complete set.

The pre-specified pathway sets use current HGNC symbols (CXCL8, NSD2) while the
older expression platforms use the symbols of their day (IL8, WHSC1). Every
enrichment test in v26-v28 therefore silently dropped genes whose symbol had
been renamed - including IL-8, the strongest single gene in the renal medullary
carcinoma chemokine signal, which was excluded from the chemokine pathway it
defines.

This downloads the authoritative HGNC table and derives the mapping from its
withdrawn/previous/alias symbol columns rather than curating one by hand.

Writes: data/hgnc_symbol_map.csv  (legacy_symbol -> current_symbol)
"""
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'data' / 'hgnc_symbol_map.csv'
CACHE = REPO / 'data' / 'hgnc_complete_set.txt'

URL = ('https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/'
       'hgnc_complete_set.txt')

if not CACHE.exists() or CACHE.stat().st_size < 1_000_000:
    print(f"downloading {URL}")
    with urllib.request.urlopen(URL, timeout=600) as r:
        CACHE.write_bytes(r.read())
print(f"HGNC table: {CACHE.stat().st_size:,} bytes")

hg = pd.read_csv(CACHE, sep='\t', low_memory=False)
print(f"  {len(hg):,} records; columns include "
      f"{[c for c in hg.columns if 'symbol' in c]}")

rows = []
for _, r in hg.iterrows():
    cur = str(r.get('symbol', '')).strip().upper()
    if not cur or cur == 'NAN':
        continue
    for col in ('prev_symbol', 'alias_symbol'):
        v = r.get(col)
        if isinstance(v, str) and v.strip():
            for old in v.replace('"', '').split('|'):
                old = old.strip().upper()
                if old and old != cur:
                    rows.append({'legacy_symbol': old, 'current_symbol': cur,
                                 'source': col})

m = pd.DataFrame(rows)
# a legacy symbol that is itself a current symbol for another gene is ambiguous
current = set(hg['symbol'].astype(str).str.upper())
ambiguous = m['legacy_symbol'].isin(current)
n_amb = int(ambiguous.sum())
m = m[~ambiguous]
# prefer prev_symbol over alias_symbol, then drop remaining duplicates
m['rank'] = (m['source'] == 'prev_symbol').map({True: 0, False: 1})
m = (m.sort_values(['legacy_symbol', 'rank'])
       .drop_duplicates('legacy_symbol')[['legacy_symbol', 'current_symbol', 'source']])
m.to_csv(OUT, index=False)

print(f"  dropped {n_amb:,} mappings whose legacy symbol is a current symbol "
      f"elsewhere (ambiguous)")
print(f"  wrote {len(m):,} legacy -> current mappings to {OUT}")
for g in ('IL8', 'WHSC1', 'TACSTD2', 'MLL2', 'PARK2'):
    hit = m[m['legacy_symbol'] == g]
    print(f"    {g:<9} -> {hit['current_symbol'].iloc[0] if len(hit) else '(unchanged)'}")

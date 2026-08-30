"""Map DepMap cell lines to the disease contexts of this study, via Cellosaurus.

The DepMap portal is behind a bot check and the release Model.csv is no longer
mirrored on figshare, so cell-line lineage is resolved from Cellosaurus instead,
which cross-references DepMap accessions directly. Resolving the lines by
disease term and depositing the resulting list is in any case more auditable
than filtering on an opaque lineage column: the exact cell lines behind every
dependency statement are named.

Writes: results/DEPMAP_CELL_LINES.csv
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results' / 'DEPMAP_CELL_LINES.csv'
API = "https://api.cellosaurus.org/search/cell-line"

# disease term -> the study context the lines stand in for
QUERIES = {
    'Bladder carcinoma': 'urothelial',
    'Bladder urothelial carcinoma': 'urothelial',
    'Bladder squamous cell carcinoma': 'urothelial',
    'Bladder small cell neuroendocrine carcinoma': 'small-cell bladder',
    'Renal cell carcinoma': 'renal',
    'Clear cell renal cell carcinoma': 'renal',
    'Renal medullary carcinoma': 'renal medullary',
    'Prostate carcinoma': 'prostate',
    'Prostate small cell neuroendocrine carcinoma': 'prostate neuroendocrine',
}


def fetch(disease, rows=400):
    q = urllib.parse.quote(f'di:"{disease}"')
    url = f"{API}?q={q}&rows={rows}&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode('utf-8'))


records = {}
for disease, context in QUERIES.items():
    try:
        data = fetch(disease)
    except Exception as exc:                                   # noqa: BLE001
        print(f"{disease:<46} FAILED {exc}")
        continue
    lines = data.get('Cellosaurus', {}).get('cell-line-list', [])
    hits = 0
    for cl in lines:
        depmap = [x['accession'] for x in (cl.get('xref-list') or [])
                  if x.get('database') == 'DepMap']
        if not depmap:
            continue
        # keep only cancer cell lines, not immortalised normals
        if cl.get('category') not in (None, 'Cancer cell line'):
            continue
        name = next((n['value'] for n in cl.get('name-list', [])
                     if n.get('type') == 'identifier'), None)
        dis = next((d.get('label') for d in (cl.get('disease-list') or [])), '')
        for ach in depmap:
            # first disease term wins, so the more specific queries listed
            # later do not overwrite a broader earlier assignment
            records.setdefault(ach, {
                'ModelID': ach, 'cell_line': name,
                'cellosaurus_disease': dis, 'context': context,
            })
            hits += 1
    print(f"{disease:<46} {hits:>4} lines with DepMap IDs")
    time.sleep(0.4)

df = pd.DataFrame(records.values()).sort_values(['context', 'cell_line'])
df.to_csv(OUT, index=False)
print(f"\n{len(df)} unique DepMap cell lines mapped")
print(df['context'].value_counts().to_string())
print(f"\nurothelial lines: "
      f"{', '.join(sorted(df[df['context'] == 'urothelial']['cell_line'].dropna())[:24])}")
print(f"\nWrote {OUT}")

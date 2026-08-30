"""Download GEO series matrix files: the sample-level metadata the refit needs.

The expression matrices carry column names only. Group assignment, batch, cell
line, treatment and time all live in the series matrix, and the v26-v28 analyses
never deposited them - which is part of why the designs could not be audited.

Writes: data/raw_matrices/<acc>/<acc>_series_matrix.txt.gz
"""
import sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parents[2] / 'data' / 'raw_matrices'
ACC = ['GSE199274','GSE216053','GSE216052','GSE130598','GSE143630',
       'GSE157256','GSE180999','GSE196978','GSE128192','GSE269750']
for a in ACC:
    dest = OUT / a / f'{a}_series_matrix.txt.gz'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f'  have  {a}'); continue
    url = (f'https://ftp.ncbi.nlm.nih.gov/geo/series/{a[:-3]}nnn/{a}/matrix/'
           f'{a}_series_matrix.txt.gz')
    try:
        with urllib.request.urlopen(url, timeout=300) as r, open(dest,'wb') as f:
            f.write(r.read())
        print(f'  got   {a} ({dest.stat().st_size:,} bytes)')
    except Exception as e:
        print(f'  FAIL  {a}: {type(e).__name__} {e}')

"""Download the deposited expression matrices for all ten GEO series.

Written for the v29 refit: the v26-v28 analyses ran on DE tables rather than on
sample-level data for several contexts, which is why the differential expression
could not be refit with a design-aware model. This script pulls what GEO
actually serves, so the refit runs from primary deposited data.

Note on GSE180999 (renal medullary carcinoma): GEO serves ONLY an author
differential-expression spreadsheet for this series - there is no sample-level
expression matrix in the supplementary files. A cell-line x treatment x time
model therefore cannot be fitted from deposited data; it would require raw reads
from SRA. This is recorded here rather than worked around silently.

Writes: data/raw_matrices/<accession>/<file>
"""
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'data' / 'raw_matrices'
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    'GSE199274': ['GSE199274_mr99-mr110_RPKM.txt.gz'],
    'GSE216053': ['GSE216053_TPM_PM154_decitabine.txt.gz'],
    'GSE216052': ['GSE216052_TPM_PM154_sgDNMTs.txt.gz'],
    'GSE130598': ['GSE130598_RAW.tar', 'filelist.txt'],
    'GSE143630': ['GSE143630_RCC_htseq_counts.txt.gz'],
    'GSE157256': ['GSE157256_RSEM_counts.txt.gz', 'GSE157256_VST_normalized.txt.gz'],
    'GSE180999': ['GSE180999_rnaseq_rmc_cell_lines_differential_expression.xlsx'],
    'GSE196978': ['GSE196978_RAW.tar', 'filelist.txt'],
    'GSE128192': ['GSE128192_RAW.tar', 'filelist.txt'],
    'GSE269750': ['GSE269750_SCBC_after_batch_adjusting_after_normalization_2024_01_24.txt.gz'],
}


def fetch(acc, name):
    dest = OUT / acc / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  have  {acc}/{name} ({dest.stat().st_size:,} bytes)")
        return
    url = (f"https://ftp.ncbi.nlm.nih.gov/geo/series/{acc[:-3]}nnn/{acc}/suppl/{name}")
    try:
        with urllib.request.urlopen(url, timeout=600) as r, open(dest, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        print(f"  got   {acc}/{name} ({dest.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"  FAIL  {acc}/{name}: {type(e).__name__} {e}")


for acc, names in FILES.items():
    for n in names:
        fetch(acc, n)

total = sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file())
print(f"\n{sum(1 for f in OUT.rglob('*') if f.is_file())} files, {total/1e6:.1f} MB in {OUT}")

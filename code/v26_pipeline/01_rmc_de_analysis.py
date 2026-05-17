"""RMC differential expression analysis.

GSE180999: 18 samples = 2 RMC cell lines (RMC219, RMC-2C) × 3 conditions
  (DMSO/NEG, dox-12hr, dox-48hr) × 3 replicates each.

Doxycycline induces SMARCB1 re-expression in RMC cell lines (which are
biallelic SMARCB1-null in their endogenous state). So:
  - NEG (DMSO, 0hr) = SMARCB1-null state (mimics RMC tumor biology)
  - dox 12hr / 48hr = SMARCB1-restored state (biological control)

Comparison: NEG vs dox-treated (12hr + 48hr combined, or 48hr alone for
more SMARCB1-restored steady state). Genes UP in NEG = up due to SMARCB1
loss = candidate drug targets for RMC.
"""
import sys, os
from pathlib import Path
import GEOparse
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\garre\framework_expansion\data")
RESULTS_DIR = Path(r"C:\Users\garre\framework_expansion\results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(DATA_DIR)

print("=" * 70)
print("RMC DE Analysis: GSE180999")
print("=" * 70)

# Download expression matrix
print("\nFetching GSE180999...")
gse = GEOparse.get_GEO(geo='GSE180999', destdir='.', silent=True)

# Build sample table from metadata
samples = []
for gsm_id, gsm in gse.gsms.items():
    title = gsm.metadata.get('title', [''])[0]
    chars = {c.split(':', 1)[0].strip(): c.split(':', 1)[1].strip()
             for c in gsm.metadata.get('characteristics_ch1', []) if ':' in c}
    samples.append({
        'gsm': gsm_id,
        'title': title,
        'cell_line': chars.get('cell line', ''),
        'treatment': chars.get('treatment', ''),
        'time': chars.get('time after treatment', ''),
    })
sample_df = pd.DataFrame(samples)
# Define group: NEG (SMARCB1-null) vs treated (SMARCB1-restored)
sample_df['group'] = sample_df['treatment'].map(
    lambda x: 'NEG' if x == 'DMSO' else 'DOX'
)
print(f"\nSample table:")
print(sample_df.to_string(index=False))


# Expression matrix — RNA-seq counts; GEO usually distributes via supplementary file
# Look for supplementary files
print(f"\nSupplementary files in GSE180999:")
for f in gse.metadata.get('supplementary_file', []):
    print(f"  {f}")

# Try to get table from GSE.table or pivot_samples
# Method 1: pivot_samples (works for some platforms)
print("\nAttempting to build expression matrix...")
try:
    # pivot_samples returns expression as DataFrame
    expr_df = gse.pivot_samples('VALUE')
    print(f"  Expression matrix from pivot_samples: shape={expr_df.shape}")
    if expr_df.shape[0] > 0:
        print(expr_df.iloc[:5, :5])
except Exception as e:
    print(f"  pivot_samples failed: {e}")
    expr_df = pd.DataFrame()

# If no expression data, we'll need to fetch the supplementary file (RNA-seq counts)
if expr_df.empty or expr_df.shape[0] == 0:
    print("  pivot_samples returned empty — RNA-seq data is in supplementary file")
    print("  Will need to download supplementary files separately")
    # Save sample table for next step
    sample_df.to_csv(RESULTS_DIR / 'GSE180999_samples.csv', index=False)
    print(f"\n  Saved sample table → {RESULTS_DIR / 'GSE180999_samples.csv'}")
else:
    # Save matrix
    expr_df.to_csv(RESULTS_DIR / 'GSE180999_expression.csv')
    sample_df.to_csv(RESULTS_DIR / 'GSE180999_samples.csv', index=False)
    print(f"\n  Saved expression matrix + samples")

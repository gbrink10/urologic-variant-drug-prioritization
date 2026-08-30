"""Turn ten heterogeneous GEO deposits into standardized matrices + metadata.

The v26-v28 analyses applied one elementary t-test to every platform. Refitting
with design-aware models first requires the designs, which live in the series
matrices, and the expression on a consistent footing. This script does the
parsing only; all modelling happens in 33_refit_limma.R.

For each context it writes
    data/prepared/<CTX>_expr.csv    genes x samples
    data/prepared/<CTX>_meta.csv    samples x covariates (first column sample)
and records the data type (counts / log2 / linear) in PREPARED_MANIFEST.csv so
the R side picks the right model.

GSE180999 (renal medullary carcinoma) is deliberately absent: GEO serves only an
author differential-expression spreadsheet for that series, so there is no
sample-level matrix to model. It is handled separately in 34_rmc_reanalysis.py.
"""
import gzip
import io
import re
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RAW = REPO / 'data' / 'raw_matrices'
OUT = REPO / 'data' / 'prepared'
OUT.mkdir(parents=True, exist_ok=True)
manifest = []


def series_meta(acc):
    """Sample-level metadata from a GEO series matrix header."""
    rows = {}
    with gzip.open(RAW / acc / f'{acc}_series_matrix.txt.gz', 'rt',
                   errors='replace') as f:
        for line in f:
            if line.startswith('!series_matrix_table_begin'):
                break
            if line.startswith('!Sample_'):
                key = line.split('\t')[0].strip('!')
                vals = [v.strip().strip('"') for v in line.rstrip('\n').split('\t')[1:]]
                rows.setdefault(key, []).append(vals)
    meta = pd.DataFrame({'sample': rows['Sample_geo_accession'][0],
                         'title': rows['Sample_title'][0]})
    for i, vals in enumerate(rows.get('Sample_characteristics_ch1', [])):
        if len(set(vals)) > 1:
            tag = re.sub(r'\W+', '_', vals[0].split(':')[0].strip().lower())
            meta[tag or f'char{i}'] = [v.split(':', 1)[-1].strip() for v in vals]
    for i, vals in enumerate(rows.get('Sample_source_name_ch1', [])):
        if len(set(vals)) > 1:
            meta['source'] = vals
    for i, vals in enumerate(rows.get('Sample_description', [])):
        meta[f'description{i or ""}'] = vals
    return meta


def series_table(acc):
    """The expression table embedded in a GEO series matrix."""
    with gzip.open(RAW / acc / f'{acc}_series_matrix.txt.gz', 'rt',
                   errors='replace') as f:
        text = f.read()
    body = text.split('!series_matrix_table_begin\n', 1)[1]
    body = body.split('!series_matrix_table_end', 1)[0]
    df = pd.read_csv(io.StringIO(body), sep='\t', index_col=0)
    df.index = df.index.astype(str).str.strip('"')
    df.columns = [c.strip('"') for c in df.columns]
    return df.apply(pd.to_numeric, errors='coerce').dropna(how='all')


def emit(ctx, expr, meta, dtype, design, contrast, note=''):
    expr = expr.loc[~expr.index.duplicated(keep='first')]
    expr.to_csv(OUT / f'{ctx}_expr.csv')
    meta.to_csv(OUT / f'{ctx}_meta.csv', index=False)
    manifest.append({'context': ctx, 'genes': expr.shape[0],
                     'samples': expr.shape[1], 'data_type': dtype,
                     'design': design, 'contrast': contrast, 'note': note})
    print(f"  {ctx:<16} {expr.shape[0]:>6} x {expr.shape[1]:<4} {dtype:<8} {design}")


print("PREPARING MATRICES")

# ---- GSE199274  NEPC: CXCR7 knockdown in two MDV-resistant lines -----------
df = pd.read_csv(RAW / 'GSE199274' / 'GSE199274_mr99-mr110_RPKM.txt.gz',
                 sep='\t', index_col=0)
m = series_meta('GSE199274')
m['cell_line'] = m['title'].str.extract(r'^(LNCaP|C4-2B)')
m['treatment'] = np.where(m['title'].str.contains('shCXCR7'), 'shCXCR7', 'LKO')
m['column'] = m['title'].str.extract(r'\[(mr\d+)\]')
df = df[[c for c in m['column'] if c in df.columns]]
m = m[m['column'].isin(df.columns)].reset_index(drop=True)
df.columns = m['sample'].values
emit('NEPC_CXCR7', df, m, 'linear', '~ cell_line + treatment',
     'shCXCR7 - LKO', 'RPKM; two cell lines, three replicates each')

# ---- GSE216053  NEPC: decitabine -----------------------------------------
df = pd.read_csv(RAW / 'GSE216053' / 'GSE216053_TPM_PM154_decitabine.txt.gz',
                 sep='\t', index_col=0)
m = series_meta('GSE216053')
m['treatment'] = np.where(m['title'].str.contains('decitaine|decitabine', case=False),
                          'decitabine', 'control')
df.columns = [c.strip() for c in df.columns]
order = ['control_1', 'control_2', 'control_3', 'day14_1', 'day14_2', 'day14_3']
df = df[[c for c in order if c in df.columns]]
m = m.iloc[:df.shape[1]].reset_index(drop=True)
df.columns = m['sample'].values
emit('NEPC_DECITABINE', df, m, 'linear', '~ treatment', 'decitabine - control',
     'TPM; PM154 patient-derived line, three replicates per arm')

# ---- GSE216052  NEPC: DNMT knockouts --------------------------------------
df = pd.read_csv(RAW / 'GSE216052' / 'GSE216052_TPM_PM154_sgDNMTs.txt.gz',
                 sep='\t', index_col=0)
gene_col = 'ensgene' if 'ensgene' in df.columns else None
if gene_col:
    df = df.groupby(df[gene_col]).sum(numeric_only=True)
m = series_meta('GSE216052')
m['genotype'] = (m['title'].str.extract(r'(Control|DNMT1 knockout|DNMT3A knockout)')[0]
                 .replace({'Control': 'WT', 'DNMT1 knockout': 'DNMT1KO',
                           'DNMT3A knockout': 'DNMT3AKO'}))
cols = [c for c in df.columns if c.startswith(('WT_', 'DNMT1KO', 'DNMT3AKO'))]
df = df[cols]
m = m.iloc[:len(cols)].reset_index(drop=True)
df.columns = m['sample'].values
emit('NEPC_DNMT', df, m, 'linear', '~ genotype', 'DNMT1KO - WT',
     'TPM aggregated to gene; three genotypes, three replicates each')

# ---- GSE130598  MIBC kinome: paired tumour / adjacent normal --------------
tar = tarfile.open(RAW / 'GSE130598' / 'GSE130598_RAW.tar')
counts, classes = {}, {}
for name in tar.getnames():
    gsm = name.split('_')[0]
    raw = tar.extractfile(name).read()
    txt = gzip.decompress(raw).decode('utf-8', 'replace') if name.endswith('.gz') \
        else raw.decode('utf-8', 'replace')
    block = txt.split('<Code_Summary>')[1].split('</Code_Summary>')[0]
    rdr = pd.read_csv(io.StringIO(block.strip()), sep=',')
    rdr.columns = [c.strip() for c in rdr.columns]
    counts[gsm] = rdr.set_index('Name')['Count']
    classes[gsm] = rdr.set_index('Name')['CodeClass']
expr = pd.DataFrame(counts)
cls = pd.DataFrame(classes).iloc[:, 0]
m = series_meta('GSE130598')
m['patient'] = m['title'].str.extract(r'(Patient \d+)')
m['tissue_group'] = np.where(m['title'].str.contains('-tumor'), 'tumor', 'normal')
expr = expr[[s for s in m['sample'] if s in expr.columns]]
# This panel carries no Housekeeping probes - only Endogenous, Positive and
# Negative code classes - so the usual housekeeping normalisation is not
# available. Use the NanoString standard fallback: subtract the negative-control
# background, rescale on the positive spike-ins, and hand the counts to
# TMM + voom, which handles the remaining composition differences.
pos = cls[cls == 'Positive'].index
neg = cls[cls == 'Negative'].index
endo = cls[cls == 'Endogenous'].index
background = expr.loc[neg].mean() + 2 * expr.loc[neg].std()
pos_gm = expr.loc[pos].apply(lambda c: np.exp(np.log(c.clip(lower=1)).mean()))
pos_factor = pos_gm / pos_gm.mean()
norm = (expr.loc[endo].sub(background, axis=1).clip(lower=0)
        .div(pos_factor, axis=1))
emit('MIBC_KINOME', norm.round(), m, 'counts', '~ patient + tissue_group',
     'tumor - normal',
     f'NanoString kinome panel, no housekeeping probes; negative-control '
     f'background subtracted, positive spike-in scaled, {m["patient"].nunique()} '
     f'matched pairs')

# ---- GSE143630  ccRCC: metastatic vs non ----------------------------------
df = pd.read_csv(RAW / 'GSE143630' / 'GSE143630_RCC_htseq_counts.txt.gz',
                 sep=' ', index_col=0)
m = series_meta('GSE143630')
m['metastatic'] = m['metastatic'].str.strip()
name_map = dict(zip(m['title'], m['sample']))
df = df[[c for c in df.columns if c in name_map]]
m = m[m['title'].isin(df.columns)].set_index('title').loc[df.columns].reset_index()
df.columns = m['sample'].values
emit('ccRCC_METS', df, m, 'counts', '~ gender + metastatic', 'Yes - No',
     'htseq counts, 44 tumours; this series contains NO normal tissue')

# ---- GSE157256  HLRCC: tumour vs adjacent normal --------------------------
df = pd.read_csv(RAW / 'GSE157256' / 'GSE157256_RSEM_counts.txt.gz',
                 sep=' ', index_col=0)
df = df.iloc[:, 1:] if df.dtypes.iloc[0] == object else df
df.index = [str(i).split('|')[-1] for i in df.index]
# matrix columns carry a submission prefix ("1031-Linehan-8") that the sample
# titles ("Linehan-8") do not, so match on the trailing Linehan-<n> token
df.columns = [re.sub(r'^\d+-', '', str(c)) for c in df.columns]
m = series_meta('GSE157256')
tt = [c for c in m.columns if c.startswith('tissue_type')][0]
m['group'] = np.where(m[tt].str.contains('Normal'), 'Normal', 'Tumor')
keep = [c for c in df.columns if c in set(m['title'])]
df = df[keep]
m = m[m['title'].isin(keep)].set_index('title').loc[keep].reset_index()
df.columns = m['sample'].values
emit('HLRCC', df.round(), m, 'counts', '~ group', 'Tumor - Normal',
     'RSEM counts; primary tumour and metastasis vs adjacent normal')

# ---- GSE196978  penile SCC: tumour vs normal, replicate-aware -------------
expr = series_table('GSE196978')
m = series_meta('GSE196978')
m['group'] = np.where(m['title'].str.startswith('N'), 'Normal', 'Tumor')
m['donor'] = m['title'].str.replace(r'\.\d+$', '', regex=True)
expr = expr[[s for s in m['sample'] if s in expr.columns]]
m = m[m['sample'].isin(expr.columns)].reset_index(drop=True)
n_donor = m.loc[m['group'] == 'Normal', 'donor'].nunique()
emit('PSCC', expr, m, 'log2', '~ group (+ duplicateCorrelation on donor)',
     'Tumor - Normal',
     f'HTA-2.0 series matrix; {n_donor} normal donors across '
     f'{(m["group"] == "Normal").sum()} arrays - technical replicates')

# ---- GSE128192  sarcomatoid vs conventional urothelial --------------------
expr = series_table('GSE128192')
m = series_meta('GSE128192')
m['group'] = np.where(m['source'].str.contains('SARC'), 'SARC', 'UC')
m['chip'] = m[[c for c in m.columns if c.startswith('description')][0]] \
    .str.extract(r'X?(\d+)')
expr = expr[[s for s in m['sample'] if s in expr.columns]]
m = m[m['sample'].isin(expr.columns)].reset_index(drop=True)
emit('SarcUC', expr, m, 'log2', '~ chip + group', 'SARC - UC',
     f'Illumina series matrix; {m["chip"].nunique()} chips as batch')

# ---- GSE269750  small-cell bladder cancer, lineage subtypes ---------------
expr = pd.read_csv(RAW / 'GSE269750' /
                   'GSE269750_SCBC_after_batch_adjusting_after_normalization_'
                   '2024_01_24.txt.gz', sep='\t', index_col=0)
m = series_meta('GSE269750')
sub = pd.read_csv(REPO / 'data' / 'DE_results' / 'SCBC_subtype_calls.csv',
                  index_col=0)
m['batch'] = m[[c for c in m.columns if c.startswith('description')][0]]
m['subtype'] = m['title'].map(sub['subtype'])
expr = expr[[t for t in m['title'] if t in expr.columns]]
m = m[m['title'].isin(expr.columns)].set_index('title').loc[expr.columns].reset_index()
expr.columns = m['sample'].values
emit('SCBC', expr, m, 'log2', '~ batch + subtype', 'each subtype - rest',
     f'batch-adjusted matrix; batches {m["batch"].value_counts().to_dict()}; '
     f'subtypes {m["subtype"].value_counts().to_dict()}')

pd.DataFrame(manifest).to_csv(OUT / 'PREPARED_MANIFEST.csv', index=False)
print(f"\nwrote {len(manifest)} contexts to {OUT}")
print(pd.DataFrame(manifest)[['context', 'genes', 'samples', 'data_type']]
      .to_string(index=False))

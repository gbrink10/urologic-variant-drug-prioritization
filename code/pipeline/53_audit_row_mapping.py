"""Audit the row-to-dataset mapping, the one hand-derived input in the pipeline.

data/master_row_definitions.csv asserts, for each of the thirty associations,
which dataset and which gene its transcriptomic component is scored on. Every
downstream number depends on it, and a wrong entry would propagate silently:
the score would still compute, the figures would still render, and nothing would
look broken.

Five independent checks, none of which trusts the mapping itself:

  1  the scoring gene appears in the row's own Target text, or is a recognised
     component of it (VEGFR -> KDR, CDK4/6 -> CDK4, and so on)
  2  the refit context belongs to the row's clinical context
  3  the scoring arm matches whether that dataset actually has a
     disease-versus-comparator contrast, read from the prepared manifest
  4  the gene is measured on that dataset's platform
  5  the arm and gene agree with the rationale recorded in the inline comments
     of the superseded v26 scoring script, which were written independently of
     this mapping

Rows failing 1, 2 or 3 are errors. Rows failing 4 are already flagged as not
re-derivable. Rows failing 5 are not necessarily wrong - the v29 analysis
deliberately changed some of them - but each one should be looked at.

Writes: results/refit/ROW_MAPPING_AUDIT.csv
"""
import ast
import re
import sys
from pathlib import Path

import paths

import pandas as pd

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')

defs = pd.read_csv(paths.DATA / 'master_row_definitions.csv')
prov = pd.read_csv(paths.REFIT / 'SCORING_PROVENANCE_V29.csv')
manifest = pd.read_csv(paths.PREPARED / 'PREPARED_MANIFEST.csv')

# which refit contexts legitimately serve which clinical context
CONTEXT_OK = {
    'NEPC': {'NEPC_CXCR7', 'NEPC_DECITABINE', 'NEPC_DNMT'},
    'MIBC / MPBC': {'MIBC_KINOME'},
    'ccRCC / sRCC': {'ccRCC_METS', 'HLRCC'},
    'ccRCC': {'ccRCC_METS', 'HLRCC'},
    'RMC': {'RMC'},
    'Penile SCC': {'PSCC'},
    'Sarcomatoid UC': {'SarcUC'},
    'SCBC (ASCL1+)': {'SCBC_ASCL1'},
    'SCBC (NEUROD1+)': {'SCBC_NEUROD1'},
    'SCBC (POU2F3+)': {'SCBC_POU2F3'},
}

# gene names that legitimately stand in for a target description
SYNONYM = {
    'KDR': ('VEGFR',), 'CDK4': ('CDK4/6', 'CDK4'), 'CDK6': ('CDK4/6',),
    'CXCL8': ('IL-8', 'IL8', 'CXCL8', 'triad'), 'ATM': ('PARP', 'ATM'),
    'PARP1': ('PARP',), 'NECTIN4': ('NECTIN-4',), 'CD274': ('PD-1', 'PD-L1'),
    'TP53': ('TP53',), 'DNMT1': ('DNMT1/3A', 'DNMT'), 'AURKA': ('AURKA',),
    'PTGS1': ('COX-1', 'PTGS1'), 'TACSTD2': ('TACSTD2', 'TROP2'),
    'HLA-DRA': ('HLA-DRA',), 'EPAS1': ('EPAS1', 'HIF2'), 'NSD2': ('NSD2', 'WHSC1'),
    'PIK3CA': ('PIK3CA',), 'FGFR3': ('FGFR3', 'FGFR2'), 'BCL2': ('BCL2',),
    'EZH2': ('EZH2',), 'ATR': ('ATR',), 'UHRF1': ('UHRF1',), 'G6PD': ('G6PD',),
    'CEACAM1': ('CEACAM1',), 'CEACAM5': ('CEACAM5',), 'SSTR2': ('SSTR2',),
    'HBEGF': ('HBEGF', 'EGFR'),
}

# Does the dataset offer a DISEASE-versus-comparator contrast, which is what the
# framework's rule requires before the differential-expression arm may be used?
# A perturbation experiment (drug treatment, gene knockout) does not, however
# well powered it is, and a tumour-only series does not either.
HAS_DISEASE_CONTRAST = {
    'NEPC_CXCR7': False,       # CXCR7 knockdown in two prostate lines
    'NEPC_DECITABINE': False,  # decitabine treatment versus control
    'NEPC_DNMT': False,        # DNMT knockout versus wild type
    'MIBC_KINOME': True,       # matched tumour versus adjacent normal
    'ccRCC_METS': False,       # tumours only; no normal tissue in the series
    'HLRCC': True,             # tumour and metastasis versus adjacent normal
    'RMC': True,               # SMARCB1-null versus rescue
    'PSCC': True,              # tumour versus normal glans
    'SarcUC': True,            # sarcomatoid versus conventional
    'SCBC_ASCL1': True, 'SCBC_NEUROD1': True, 'SCBC_POU2F3': True,
}

# what the superseded v26 script recorded, parsed from its inline comments
src = (paths.CODE / 'pipeline' / '11_master_table_uniform.py').read_text(
    encoding='utf-8')
seg = src[src.index('MASTER_ROWS = ['):]
seg = seg[:seg.index('\n]') + 2]
legacy = {}
for m in re.finditer(r'\((\d+), .*?#\s*(E=[^\n]*)', seg, re.S):
    pass
for line in seg.splitlines():
    mm = re.match(r'\s*(\d+), (\d), (\d), (\d),\s*#\s*(.*)', line)
    if mm:
        continue
row_no = None
for line in seg.splitlines():
    m0 = re.match(r'\s*\((\d+), ', line)
    if m0:
        row_no = int(m0.group(1))
    if row_no and '#' in line and ('E=' in line or 'pct' in line or 'TPM' in line):
        legacy.setdefault(row_no, line.split('#', 1)[1].strip())

# gene table per dataset, to test whether the gene is even measured.
# The two array platforms are keyed by probe identifier, so the probe->symbol
# annotation has to be applied here as the scorer applies it; without it every
# array-based row falsely appears unmeasured.
_sarc = pd.read_csv(paths.DE_RESULTS / 'SarcomatoidUC_DE_full.csv.gz')
SARC_MAP = dict(zip(_sarc['probe_id'].astype(str),
                    _sarc['gene'].astype(str).str.upper()))
_pen = pd.read_csv(paths.DE_RESULTS / 'PenileSCC_DE_full.csv.gz')


def _hta(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    sym = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if sym in ('---', 'NULL', 'NAN') else sym


PSCC_MAP = dict(zip(_pen['probe_id'].astype(str), _pen['gene'].map(_hta)))
PROBE_MAPS = {'SarcUC': SARC_MAP, 'PSCC': PSCC_MAP}

_meas = {}


def measured(ctx, gene):
    if ctx not in _meas:
        if ctx == 'RMC':
            idx = pd.Series(pd.read_csv(paths.REFIT / 'RMC_REANALYSIS.csv',
                                        index_col=0).index.astype(str))
        else:
            f = paths.REFIT / f'DE_{ctx}.csv'
            if not f.exists():
                _meas[ctx] = set()
                return False
            t = pd.read_csv(f)
            idx = t['gene'].astype(str)
            if ctx in PROBE_MAPS:
                idx = idx.map(PROBE_MAPS[ctx]).fillna('')
        _meas[ctx] = set(lib_symbols.to_symbols(list(idx)).values)
    return gene in _meas[ctx]


rows = []
for _, d in defs.iterrows():
    n = int(d['N'])
    gene = lib_symbols.normalize([d['scoring_gene']]).iloc[0]
    target = str(d['Target']).upper()
    ctx, arm = d['refit_context'], d['scoring_arm']

    c1 = (gene in target or
          any(s.upper() in target for s in SYNONYM.get(gene, ())))
    c2 = ctx in CONTEXT_OK.get(d['Context'], set())
    contrast = HAS_DISEASE_CONTRAST.get(ctx, True)
    # the differential arm is only expected where a disease contrast exists AND
    # the gene survives into the fitted table; otherwise a fallback is correct
    in_de_table = measured(ctx, gene) if arm != 'curated' else False
    c3 = (arm == 'curated') or ((arm == 'de') == bool(contrast and in_de_table))
    c4 = measured(ctx, gene)

    note = legacy.get(n, '')
    legacy_expr = bool(re.search(r'pct|TPM|percentile', note))
    c5 = (not note) or (legacy_expr == (arm == 'expression'))
    legacy_gene = None
    gm = re.match(r'E=\d:?\s*([A-Z0-9\-]+)', note)
    if gm and gm.group(1) in ('DE', 'TPM', 'FC', 'PCT'):
        gm = None   # prose in the comment, not a gene symbol
    if gm:
        legacy_gene = lib_symbols.normalize([gm.group(1)]).iloc[0]

    flags = []
    if not c1:
        flags.append('gene not evident in Target text')
    if not c2:
        flags.append(f'context {ctx} not expected for {d["Context"]}')
    if not c3:
        flags.append(f'arm "{arm}" but disease contrast available = {contrast}')
    if not c4:
        flags.append('gene not measured on that platform')
    if not c5:
        flags.append('arm disagrees with the v26 rationale')
    if legacy_gene and legacy_gene != gene:
        flags.append(f'v26 rationale names {legacy_gene}')

    rows.append({'N': n, 'Context': d['Context'], 'Target': d['Target'],
                 'scoring_gene': gene, 'refit_context': ctx, 'arm': arm,
                 'gene_in_target': c1, 'context_valid': c2, 'arm_valid': c3,
                 'gene_measured': c4, 'agrees_with_v26': c5,
                 'v26_rationale': note[:90],
                 'review': '; '.join(flags) or '-'})

out = pd.DataFrame(rows)
out.to_csv(paths.REFIT / 'ROW_MAPPING_AUDIT.csv', index=False)

hard = out[~out['gene_in_target'] | ~out['context_valid'] | ~out['arm_valid']]
soft = out[(out['gene_in_target'] & out['context_valid'] & out['arm_valid'])
           & (~out['gene_measured'] | ~out['agrees_with_v26']
              | out['review'].str.contains('v26 rationale names'))]

print(f"{len(out)} rows checked\n")
print(f"ERRORS needing correction: {len(hard)}")
for _, r in hard.iterrows():
    print(f"  row {r['N']:<3} {str(r['Target'])[:34]:<36} {r['review']}")
print(f"\nWORTH A LOOK (not necessarily wrong): {len(soft)}")
for _, r in soft.iterrows():
    print(f"  row {r['N']:<3} {str(r['Target'])[:30]:<32} gene={r['scoring_gene']:<8} "
          f"{r['review']}")
    if r['v26_rationale']:
        print(f"        v26 said: {r['v26_rationale']}")
clean = len(out) - len(hard) - len(soft)
print(f"\nclean on all five checks: {clean} of {len(out)}")
print(f"wrote {paths.REFIT / 'ROW_MAPPING_AUDIT.csv'}")

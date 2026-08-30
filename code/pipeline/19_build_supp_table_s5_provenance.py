"""Build the real Supplementary Table S5: per-row scoring provenance.

The manuscript states that S5 enumerates "the specific gene or alteration used to
assign the genomic / context-anchor score for each Master Table 1 row". The file
currently shipped as S5 (code/manuscript_build/add_supp_table_s5.py) is a
different artefact - a 16-row pathway / drug-class landscape table carried over
from v25 - so that claim has no supporting document.

This script builds the table the manuscript actually promises, by pairing each
Master Table 1 row with:
  * the inline scoring rationale recorded in 11_master_table_uniform.py,
  * the four score components as deposited, and
  * the verdict from the two audit scripts (14_ and 18_) on whether the
    transcriptomic component is reproducible from deposited DE tables.

Writes: results/Supplementary_Table_S5_scoring_provenance.csv
"""
import ast
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
BUILDER = REPO / 'code' / 'pipeline' / '11_master_table_uniform.py'
MASTER = REPO / 'results' / 'MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv'
AUDIT_RARE = REPO / 'results' / 'GEO_SCORE_AUDIT.csv'
AUDIT_SRC = REPO / 'results' / 'SOURCE_DISEASE_SCORE_AUDIT.csv'
V25_PROV = REPO / 'data' / 'v25_source_disease_provenance.csv'
RANK_AUDIT = REPO / 'results' / 'EXPRESSION_RANK_AUDIT.csv'
TPM_PCT = REPO / 'results' / 'NEPC_TPM_PERCENTILES.csv'
OUT = REPO / 'results' / 'Supplementary_Table_S5_scoring_provenance.csv'

# ---- harvest the inline rationale comments that precede each row tuple ----
src = BUILDER.read_text(encoding='utf-8').split('\n')
comments = {}
buffer = []
for line in src:
    stripped = line.strip()
    if stripped.startswith('#'):
        buffer.append(stripped.lstrip('#').strip())
        continue
    m = re.match(r'\((\d+),\s*[\'"]', stripped)
    if m:
        comments[int(m.group(1))] = ' | '.join(b for b in buffer if b)
        buffer = []
    elif stripped and not stripped.startswith(('\'', '"', ')')):
        buffer = []

# trailing same-line comments carry the score rationale too
inline_note = {}
current = None
for line in src:
    m = re.match(r'\s*\((\d+),\s*[\'"]', line)
    if m:
        current = int(m.group(1))
    if current and '#' in line and re.search(r'\d,\s*\d,\s*\d,\s*\d,', line):
        inline_note[current] = line.split('#', 1)[1].strip()

print(f"harvested rationale for {len(comments)} rows")

master = pd.read_csv(MASTER)
master['row'] = pd.to_numeric(master['N'], errors='coerce')

rare = pd.read_csv(AUDIT_RARE) if AUDIT_RARE.exists() else pd.DataFrame()
srcaud = pd.read_csv(AUDIT_SRC) if AUDIT_SRC.exists() else pd.DataFrame()

audit_verdict, audit_detail = {}, {}
for _, r in rare.iterrows():
    audit_verdict[int(r['row'])] = (
        'reproducible from deposited DE' if r['agrees'] == 'yes' else str(r['agrees']))
    audit_detail[int(r['row'])] = (
        f"{r['transcript']} log2FC={r['log2FC_disease']} q={r['q']}")
for _, r in srcaud.iterrows():
    v = str(r['verdict'])
    audit_verdict[int(r['row'])] = {
        'agrees': 'reproducible from deposited DE',
        'n/a - genomic-only row': 'n/a (genomic-only row, E=0)',
    }.get(v, v)
    audit_detail[int(r['row'])] = (
        f"{r.get('genes', '')} log2FC={r.get('log2FC')} q={r.get('q')} "
        f"expr_pct={r.get('expr_pct')}")

# recovered provenance for the source-disease rows, transcribed from the v25
# manuscript's validation table (the only surviving record of how the E
# component was assigned for rows 1-16)
v25 = pd.read_csv(V25_PROV) if V25_PROV.exists() else pd.DataFrame()
v25_ev = {int(r['row']): r['geo_evidence_as_recorded_v25'] for _, r in v25.iterrows()}
v25_type = {int(r['row']): r['evidence_type'] for _, r in v25.iterrows()}
v25_score = {int(r['row']): r['v25_score'] for _, r in v25.iterrows()}

rank = pd.read_csv(RANK_AUDIT) if RANK_AUDIT.exists() else pd.DataFrame()
rank_note = {}
for _, r in rank.iterrows():
    rank_note.setdefault(int(r['row']), []).append(
        f"{r['gene']}: {r['verdict']}")
rank_note = {k: ' ; '.join(v) for k, v in rank_note.items()}

# percentiles recomputed from the primary GEO expression matrices
tpm = pd.read_csv(TPM_PCT) if TPM_PCT.exists() else pd.DataFrame()
GENE_ROW = {'BCL2': 1, 'EZH2': 3, 'DNMT1': 4, 'PARP1': 6, 'PARP2': 6}
tpm_note = {}
if not tpm.empty:
    primary = tpm[tpm['source'].str.startswith('GSE216053')]
    for _, r in primary.iterrows():
        n = GENE_ROW.get(r['gene'])
        if n is None:
            continue
        tpm_note.setdefault(n, []).append(
            f"{r['gene']}={r['value']} TPM (v25 recorded {r['v25_quoted']}); "
            f"{r['pct_all_genes']}th pct of all transcripts")
tpm_note = {k: ' ; '.join(v) for k, v in tpm_note.items()}

rows = []
for _, m in master.sort_values('row').iterrows():
    n = m['row']
    if pd.isna(n):
        continue
    n = int(n)
    rows.append({
        'Row': n,
        'Context': m['Context'],
        'Drug': m['Drug'],
        'Target': m['Target'],
        'G (0-3)': m['TCGA(0-3)'],
        'E (0-3)': m['GEO(0-3)'],
        'P (0-2)': m['KEGG(0-2)'],
        'L (0-1)': m['Lit(0-1)'],
        'Total': m['Total'],
        'Tier': m['Tier'],
        'Scoring rationale (as recorded at build time)': comments.get(n, ''),
        'Score note': inline_note.get(n, ''),
        'E component evidence as recorded (v25 validation table)':
            v25_ev.get(n, ''),
        'E component evidence type': v25_type.get(n, ''),
        'Score in v25': v25_score.get(n, ''),
        'Expression percentile (primary GEO matrix)': tpm_note.get(n, ''),
        'Expression-rank arm check': rank_note.get(n, ''),
        'E component reproducible from deposited DE?':
            audit_verdict.get(n, 'not audited'),
        'Audit measurement': audit_detail.get(n, ''),
        'Prior status': m['Prior status'],
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False, encoding='utf-8-sig')

print(f"\nS5 provenance table: {len(df)} rows -> {OUT}")
print("\nreproducibility of the E component across all 30 rows:")
print(df['E component reproducible from deposited DE?'].value_counts().to_string())
missing = df[df['Scoring rationale (as recorded at build time)'] == '']
if len(missing):
    print(f"\nrows with no recorded rationale: {list(missing['Row'])}")

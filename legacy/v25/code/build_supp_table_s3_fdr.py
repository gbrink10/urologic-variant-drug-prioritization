"""Compute Supp Table S3: headline findings surviving BH-FDR q < 0.10."""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

VAL = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")
df = pd.read_csv(VAL / "FULL_DE_RESULTS.csv")

# BH-FDR per DE comparison (dataset + group_a + group_b)
def bh_qvals(pvals):
    pvals = np.asarray(pvals, dtype=float)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    qvals_sorted = ranked * n / (np.arange(n) + 1)
    # Enforce monotonicity
    for i in range(n - 2, -1, -1):
        qvals_sorted[i] = min(qvals_sorted[i], qvals_sorted[i + 1])
    qvals = np.empty(n)
    qvals[order] = np.minimum(qvals_sorted, 1.0)
    return qvals

df['q_value'] = np.nan
for (ds, ga, gb), sub in df.groupby(['dataset', 'group_a', 'group_b']):
    mask = (df['dataset'] == ds) & (df['group_a'] == ga) & (df['group_b'] == gb)
    valid = ~df.loc[mask, 'p_value'].isna()
    pvals = df.loc[mask & valid, 'p_value'].values
    if len(pvals) > 0:
        qvals = bh_qvals(pvals)
        df.loc[mask & valid, 'q_value'] = qvals

# Headline genes per cancer context (those reported prominently in the manuscript)
headline_genes = {
    "NEPC (CXCR7 KD, GSE199274)": {
        'dataset': 'GSE199274',
        'genes': ['AURKA', 'SYP', 'ENO2', 'ACKR3', 'CHGA', 'CHGB', 'NEUROD1', 'INSM1', 'MYCN'],
    },
    "NEPC (decitabine, GSE216053)": {
        'dataset': 'GSE216053',
        'genes': ['BCL2', 'PARP1', 'RB1', 'EZH2', 'DNMT1', 'FOXA2', 'EPAS1', 'MYCN', 'TP53'],
    },
    "MIBC kinome (GSE130598)": {
        'dataset': 'GSE130598',
        'genes': ['AURKA', 'AURKB', 'CDK1', 'CDK2', 'PLK1', 'PLK4', 'BUB1', 'BUB1B', 'CHEK1', 'CHEK2',
                  'PRKDC', 'PBK', 'TTK', 'FGFR1', 'FGFR3', 'ERBB2', 'ERBB3', 'ATR', 'WEE1'],
    },
    "ccRCC (T1 vs T2, GSE143630)": {
        'dataset': 'GSE143630',
        'genes': ['VEGFA', 'EPAS1', 'HIF1A', 'FLT1', 'KDR', 'PDGFRB', 'CDK4', 'CDK6'],
    },
    "HLRCC vs normal kidney (GSE157256)": {
        'dataset': 'GSE157256',
        'genes': ['EPAS1', 'VEGFA', 'HIF1A', 'FH'],
    },
}

print(f"{'Context':<40} {'N total':>10} {'p<0.05':>10} {'q<0.10':>10} {'q<0.25':>10}")
print("=" * 90)

rows_out = []
for label, info in headline_genes.items():
    sub = df[df['dataset'] == info['dataset']]
    headline = sub[sub['gene'].isin(info['genes'])]
    n_total = len(headline)
    if n_total == 0:
        print(f"{label:<40}  (no genes found)")
        continue
    p_05 = (headline['p_value'] < 0.05).sum()
    q_10 = (headline['q_value'] < 0.10).sum()
    q_25 = (headline['q_value'] < 0.25).sum()
    print(f"{label:<40} {n_total:>10} {p_05:>10} {q_10:>10} {q_25:>10}")
    rows_out.append({
        'analysis_context': label,
        'dataset': info['dataset'],
        'n_headline_genes': n_total,
        'n_p_lt_0.05': int(p_05),
        'n_q_lt_0.10': int(q_10),
        'n_q_lt_0.25': int(q_25),
        'pct_q_lt_0.10': f"{100*q_10/n_total:.1f}%" if n_total else "—",
    })

# Save Supp Table S3
out_path = VAL / "Supplementary_Table_S3_FDR_survival.csv"
pd.DataFrame(rows_out).to_csv(out_path, index=False)
print(f"\nSaved: {out_path}")

# Also save the full enriched FULL_DE_RESULTS with q_value column
out_full = VAL / "FULL_DE_RESULTS_with_qvalues.csv"
df.to_csv(out_full, index=False)
print(f"Saved enriched DE table with q-values: {out_full}")

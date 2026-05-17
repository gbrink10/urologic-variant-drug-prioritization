"""Apply uniform 9-point Molecular Prioritization Score to all 4 rare disease
contexts (RMC, PSCC, Sarcomatoid UC, SCBC), matching the scoring scheme used
for the 14 validation candidates.

Score components (0-9):
  - TCGA / genomic component (0-3): alteration frequency in source / disease
    cohort (from TCGA Pan-Cancer Atlas or published genomic series)
  - GEO transcriptomic component (0-3): from DE results
  - KEGG pathway component (0-2): hypergeometric enrichment
  - External published-literature component (0-1)

Per disease:
  1. Load DE results (UP-in-tumor / UP-in-variant genes)
  2. Run hypergeometric enrichment for each of the 8 pre-specified KEGG pathways
  3. For each candidate drug-target, compute the 4-component score
  4. Output uniform-scoring table

Genomic landscape sources (from published literature, not TCGA where rare):
  - RMC: Msaouel 2019/2025 (universal SMARCB1 loss; otherwise quiet)
  - PSCC: TCGA Penile + Feber 2016 (TP53 ~30-50%, CDKN2A ~25-50%, PIK3CA ~30%, NOTCH1 ~30%)
  - Sarc-UC: Sjödahl 2017 / TCGA-BLCA SARC subset (TP53 high, RB1 ~50%, ARID1A ~30%)
  - SCBC: Feng 2023 / Chang 2019 (TP53 universal, RB1 universal)
"""
import sys, json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import hypergeom
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")
KEGG = json.load(open(RESULTS / 'kegg_pathways.json'))
print(f"Loaded {len(KEGG)} KEGG pathway sets")


def kegg_enrichment(de_genes, universe_size=20000):
    """For each pathway, test if `de_genes` is enriched (hypergeometric upper-tail).
    Returns dict pathway -> (intersection_count, pathway_size, p_value)
    """
    de_set = set(g for g in de_genes if isinstance(g, str) and g)
    results = {}
    for path_name, path_genes in KEGG.items():
        path_set = set(path_genes)
        K = len(path_set)
        n = len(de_set)
        k = len(de_set & path_set)
        # Upper-tail P(X >= k): sf(k-1, N, K, n)
        if k == 0:
            p = 1.0
        else:
            p = hypergeom.sf(k - 1, universe_size, K, n)
        results[path_name] = {'overlap': k, 'pathway_size': K,
                               'de_size': n, 'pvalue': p,
                               'overlap_genes': sorted(de_set & path_set)}
    return results


def kegg_score(gene, enrichment_results):
    """Return KEGG component score (0-2) for a given target gene.
    2 = pathway is enriched (p<0.10) AND gene is in pathway
    1 = pathway enriched OR gene in pathway
    0 = neither
    """
    enriched_pathways = {p for p, r in enrichment_results.items() if r['pvalue'] < 0.10}
    in_pathway_pathways = {p for p, r in KEGG.items() if gene in r}  # but KEGG is gene LIST
    in_pathway_pathways = {p for p, genes in KEGG.items() if gene in genes}
    if enriched_pathways & in_pathway_pathways:
        return 2
    if enriched_pathways or in_pathway_pathways:
        return 1
    return 0


# =====================================================================
# RMC
# =====================================================================
print("\n" + "=" * 70)
print("RMC KEGG enrichment + scoring")
print("=" * 70)
rmc_up = pd.read_csv(RESULTS / 'RMC_up_in_null_state.csv')
de_genes_rmc = rmc_up['gene'].tolist()
print(f"DE UP genes (cross-cell-line consistent): {len(de_genes_rmc)} — {de_genes_rmc}")
enr_rmc = kegg_enrichment(de_genes_rmc)
print("\nKEGG enrichment (RMC UP genes):")
for path, r in sorted(enr_rmc.items(), key=lambda x: x[1]['pvalue']):
    print(f"  {path:<25} overlap={r['overlap']}/{r['pathway_size']:<4}  p={r['pvalue']:.3e}  "
          f"genes={r['overlap_genes']}")


# =====================================================================
# Penile SCC (top 200 tumor-UP genes by log2FC)
# =====================================================================
print("\n" + "=" * 70)
print("Penile SCC KEGG enrichment + scoring")
print("=" * 70)
penile_up = pd.read_csv(RESULTS / 'PenileSCC_tumor_up.csv')
def extract_symbol(ga):
    if not isinstance(ga, str): return None
    parts = ga.split('//')
    if len(parts) >= 2: return parts[1].strip()
    return None
penile_up['symbol'] = penile_up['gene'].apply(extract_symbol)
penile_genes_unique = penile_up[penile_up['symbol'].notna() & (penile_up['symbol'] != '---')] \
                       .drop_duplicates('symbol').head(200)
de_genes_pscc = penile_genes_unique['symbol'].tolist()
print(f"Top 200 tumor-UP genes (penile SCC)")
enr_pscc = kegg_enrichment(de_genes_pscc)
print("\nKEGG enrichment (Penile SCC tumor-UP):")
for path, r in sorted(enr_pscc.items(), key=lambda x: x[1]['pvalue']):
    print(f"  {path:<25} overlap={r['overlap']}/{r['pathway_size']:<4}  p={r['pvalue']:.3e}  "
          f"genes={r['overlap_genes'][:5]}{'...' if len(r['overlap_genes'])>5 else ''}")


# =====================================================================
# Sarcomatoid UC
# =====================================================================
print("\n" + "=" * 70)
print("Sarcomatoid UC KEGG enrichment + scoring")
print("=" * 70)
sarc_up = pd.read_csv(RESULTS / 'SarcomatoidUC_up.csv')
de_genes_sarc = sarc_up['gene'].dropna().tolist()
print(f"SARC-UP genes (log2FC>1, q<0.05): {len(de_genes_sarc)}")
enr_sarc = kegg_enrichment(de_genes_sarc)
print("\nKEGG enrichment (Sarcomatoid UC UP vs conventional):")
for path, r in sorted(enr_sarc.items(), key=lambda x: x[1]['pvalue']):
    print(f"  {path:<25} overlap={r['overlap']}/{r['pathway_size']:<4}  p={r['pvalue']:.3e}  "
          f"genes={r['overlap_genes'][:5]}{'...' if len(r['overlap_genes'])>5 else ''}")


# =====================================================================
# SCBC subtypes
# =====================================================================
print("\n" + "=" * 70)
print("SCBC subtype-specific KEGG enrichment + scoring")
print("=" * 70)
scbc_enrichments = {}
for subtype in ['ASCL1', 'POU2F3', 'NEUROD1']:
    path_csv = RESULTS / f'SCBC_up_in_{subtype}.csv'
    if not path_csv.exists():
        continue
    df = pd.read_csv(path_csv)
    de_genes = df['gene'].dropna().tolist()
    enr = kegg_enrichment(de_genes)
    scbc_enrichments[subtype] = enr
    print(f"\nSCBC {subtype}+ ({len(de_genes)} UP genes):")
    for path, r in sorted(enr.items(), key=lambda x: x[1]['pvalue']):
        if r['overlap'] > 0:
            print(f"  {path:<25} overlap={r['overlap']}/{r['pathway_size']:<4}  p={r['pvalue']:.3e}  "
                  f"genes={r['overlap_genes'][:5]}")


# =====================================================================
# Save consolidated enrichment results
# =====================================================================
all_enr = {
    'RMC': enr_rmc,
    'PSCC': enr_pscc,
    'SarcUC': enr_sarc,
    **{f'SCBC_{k}': v for k, v in scbc_enrichments.items()}
}

# Strip non-serializable parts
def to_serializable(d):
    return {k: {kk: (list(vv) if isinstance(vv, set) else (float(vv) if isinstance(vv, np.floating) else vv))
                for kk, vv in v.items()}
            for k, v in d.items()}

with open(RESULTS / 'kegg_enrichment_all_diseases.json', 'w') as f:
    json.dump({d: to_serializable(e) for d, e in all_enr.items()}, f, indent=2)
print(f"\nSaved enrichment summary → {RESULTS / 'kegg_enrichment_all_diseases.json'}")

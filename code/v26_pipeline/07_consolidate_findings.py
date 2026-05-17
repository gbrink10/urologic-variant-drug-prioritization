"""Consolidate framework-discovery findings across the four rare urologic diseases
and map top differentially-expressed targets to specific FDA-approved + late-Phase
drugs (using the same drug-target landscape framework as the main manuscript).

Each "candidate" entry: (disease, gene/target, log2FC, qvalue, drug-class, specific drugs,
investigational alternatives, novelty status — pending literature check).
"""
import sys, os
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")

# Drug-target → druggable agents map (extended from main manuscript's Table 2 landscape)
DRUG_MAP = {
    # Chemokine axis
    'IL8': ('CXCR1/CXCR2', 'reparixin, navarixin (MK-7123), AZD5069, danirixin, ladarixin'),
    'CXCL1': ('CXCR2', 'reparixin, navarixin, AZD5069'),
    'CXCL2': ('CXCR2', 'reparixin, navarixin, AZD5069'),
    'CXCL8': ('CXCR1/CXCR2', 'reparixin, navarixin, AZD5069'),
    'CXCL10': ('CXCR3 axis', 'eldelumab (anti-IP-10); CXCR3 antagonists preclinical'),
    'HBEGF': ('EGFR ligand → EGFR', 'cetuximab, panitumumab, erlotinib, gefitinib, afatinib, osimertinib'),
    'CEACAM1': ('CEACAM1', 'CM24 (anti-CEACAM1, investigational)'),
    'CEACAM5': ('CEACAM5 (CEA)', 'tusamitamab ravtansine (anti-CEACAM5 ADC; Phase III NSCLC)'),
    'HLA-DRA': ('MHC-II / immune-hot', 'pembrolizumab, nivolumab, durvalumab, atezolizumab + combos'),
    'SERPINB3': ('SCC tumor antigen', 'no direct agent; biomarker for SCC profiling'),
    'SERPINB4': ('SCC tumor antigen', 'no direct agent; biomarker for SCC profiling'),
    'MMP1': ('MMP1 / collagenase', 'andecaliximab (anti-MMP9), batimastat/marimastat (historical)'),
    'DSG1': ('Desmoglein 1', 'no direct drug; squamous differentiation marker'),
    'POSTN': ('Periostin / TGFβ axis', 'anti-TGFβ agents; possibly fresolimumab'),
    # Sarcomatoid UC top hits
    'WHSC1': ('NSD2 (MMSET) HMT', 'KTX-1001 (Phase I), SP-2577 (seclidemstat)'),
    'ATRIP': ('ATR pathway', 'ceralasertib (AZD6738), berzosertib (M6620), elimusertib (BAY-1895344)'),
    'UHRF1': ('UHRF1 epigenetic reader', 'UM-002 (preclinical); some VHL-aligned PROTACs in development'),
    'G6PD': ('Pentose phosphate / G6PD', '6-aminonicotinamide, polydatin (preclinical)'),
    'P4HA2': ('Prolyl-4-hydroxylase (collagen)', 'no clinical agent; FG-4592 / roxadustat targets PHDs (different family)'),
    # SCBC subtype hits
    'SSTR2': ('Somatostatin receptor 2', 'octreotide, lanreotide, pasireotide, 177Lu-DOTATATE (Lutathera)'),
    'POU2F3': ('POU2F3 lineage TF (tuft-cell)', 'no direct agent; lineage marker for FGFR1/IGF1R-vulnerability subtype'),
    'NEUROD1': ('NEUROD1 lineage TF', 'no direct agent; lineage marker for AURKA-vulnerability subtype'),
    'ASCL1': ('ASCL1 lineage TF', 'no direct agent; lineage marker for DLL3-positive subtype (tarlatamab, rovalpituzumab tesirine)'),
    'PTGS1': ('Cyclooxygenase 1', 'aspirin, indomethacin, celecoxib (COX-2-pref)'),
}


def map_drugs(genes_with_l2fc):
    rows = []
    for gene, l2fc, qval, extra in genes_with_l2fc:
        if gene in DRUG_MAP:
            target, drugs = DRUG_MAP[gene]
            rows.append({
                'gene': gene,
                'log2FC': round(l2fc, 2),
                'qvalue': f"{qval:.2e}" if qval else '',
                'target/class': target,
                'drugs': drugs,
                'extra': extra
            })
    return pd.DataFrame(rows)


print("=" * 70)
print("FRAMEWORK DISCOVERY: Cross-disease drug-target candidates")
print("=" * 70)

# ============================================================
# DISEASE 1: RMC (SMARCB1-loss biology)
# ============================================================
print("\n## DISEASE 1: Renal Medullary Carcinoma (RMC) ##")
print("Data: GSE180999 (SMARCB1-rescue vs null in two RMC cell lines)")
print("Comparison: genes UP in SMARCB1-null state = candidate drug targets")
rmc_up = pd.read_csv(RESULTS / 'RMC_up_in_null_state.csv')
print(f"Genes UP in RMC (13 high-confidence cross-line): {list(rmc_up['gene'])}")

# Map to drugs
rmc_candidates = [(g, -float(rmc_up[rmc_up['gene']==g]['mean_l2fc_48h'].iloc[0]),
                   float(rmc_up[rmc_up['gene']==g]['qval_48h_RMC2C'].iloc[0]),
                   'cross-cell-line consistent') for g in rmc_up['gene']]
print("\nDrug-class candidates for RMC:")
rmc_drugs = map_drugs(rmc_candidates)
if not rmc_drugs.empty:
    print(rmc_drugs.to_string(index=False))

# ============================================================
# DISEASE 2: Penile SCC (tumor vs normal penis)
# ============================================================
print("\n\n## DISEASE 2: Penile Squamous Cell Carcinoma ##")
print("Data: GSE196978 (16 cancer vs 6 normal)")
penile_up = pd.read_csv(RESULTS / 'PenileSCC_tumor_up.csv')
# Filter to genes (drop probes without symbol)
penile_genes = penile_up[penile_up['gene'].notna() & (penile_up['gene'] != '')].copy()
# Extract symbol from gene_assignment (format: "NM_xxx // SYMBOL // description // ...")
def extract_symbol(ga):
    if not isinstance(ga, str): return None
    parts = ga.split('//')
    if len(parts) >= 2: return parts[1].strip()
    return None
penile_genes['symbol'] = penile_genes['gene'].apply(extract_symbol)
penile_genes = penile_genes[penile_genes['symbol'].notna() & (penile_genes['symbol'] != '---')]
penile_genes = penile_genes.drop_duplicates('symbol').head(60)
print(f"Top 30 unique tumor-UP genes: {list(penile_genes['symbol'].head(30))}")

penile_candidates = [(row['symbol'], row['log2fc'], row['qvalue'], '')
                     for _, row in penile_genes.iterrows()]
print("\nDrug-class candidates for Penile SCC:")
penile_drugs = map_drugs(penile_candidates)
if not penile_drugs.empty:
    print(penile_drugs.to_string(index=False))

# ============================================================
# DISEASE 3: Sarcomatoid UC (SARC vs conventional UC)
# ============================================================
print("\n\n## DISEASE 3: Sarcomatoid Urothelial Carcinoma ##")
print("Data: GSE128192 (28 SARC vs 84 conventional UC)")
sarc_up = pd.read_csv(RESULTS / 'SarcomatoidUC_up.csv')
print(f"Top 30 SARC-UP genes: {list(sarc_up['gene'].head(30))}")
sarc_candidates = [(row['gene'], row['log2fc'], row['qvalue'], '')
                   for _, row in sarc_up.head(50).iterrows()]
print("\nDrug-class candidates for Sarcomatoid UC:")
sarc_drugs = map_drugs(sarc_candidates)
if not sarc_drugs.empty:
    print(sarc_drugs.to_string(index=False))

# ============================================================
# DISEASE 4: SCBC subtype-stratified
# ============================================================
print("\n\n## DISEASE 4: Small-Cell Bladder Cancer (subtype-stratified) ##")
print("Data: GSE269750 (44 SCBC; lineage TF-defined subtypes)")
for subtype in ['ASCL1', 'POU2F3', 'NEUROD1']:
    path = RESULTS / f'SCBC_up_in_{subtype}.csv'
    if not path.exists(): continue
    df = pd.read_csv(path)
    print(f"\n  Subtype {subtype}+ (top 15 UP):")
    print(f"    Genes: {list(df['gene'].head(15))}")
    sub_cand = [(row['gene'], row['log2fc'], row['qvalue'], '') for _, row in df.head(40).iterrows()]
    sub_drugs = map_drugs(sub_cand)
    if not sub_drugs.empty:
        print(f"\n    Drugged candidates ({len(sub_drugs)}):")
        print(sub_drugs.to_string(index=False))


# ============================================================
# CONSOLIDATED candidate summary
# ============================================================
print("\n\n" + "=" * 70)
print("CONSOLIDATED CANDIDATE DRUGS BY DISEASE (top novel-looking)")
print("=" * 70)
print("""
RMC (SMARCB1-null biology):
  - CXCR1/2 axis inhibition (reparixin, navarixin, AZD5069)  ← IL8+CXCL1+CXCL2 triad
  - EGFR pathway (HBEGF ligand) → cetuximab, erlotinib
  - CEACAM1 (CM24 antibody, investigational)

Penile SCC:
  - Immune checkpoint inhibition (HLA-DRA + CXCL10 = immune-hot)
  - Anti-CEACAM5 ADC (tusamitamab ravtansine) — would need CEACAM5 check
  - Anti-MMP9 (andecaliximab) — MMP1 elevated, MMP-family signaling

Sarcomatoid UC:
  - NSD2 (WHSC1) inhibition — KTX-1001, SP-2577 (epigenetic)
  - ATR inhibition (ceralasertib, berzosertib, elimusertib) — ATRIP elevated
  - UHRF1 epigenetic reader (UM-002 preclinical)
  - G6PD / pentose phosphate (6-aminonicotinamide preclinical)
  - LOSS of TROP2 (TACSTD2 DOWN) → sacituzumab govitecan unlikely effective in SARC variant

SCBC (subtype-stratified):
  - ASCL1+ subtype: CEACAM5-targeted ADC (tusamitamab ravtansine) — analogous to SCLC
  - POU2F3+ subtype: COX-1 inhibition (PTGS1 elevated); FGFR1/IGF1R lineage targeting
  - NEUROD1+ subtype: SSTR2-directed theranostics (octreotide, 177Lu-DOTATATE) — NOVEL angle
  - YAP1+ subtype: no significant DE signature in this dataset
""")

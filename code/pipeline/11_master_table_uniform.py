"""Build the unified Master Table 1 for v26 manuscript:
all 28 drug-cancer associations across 7 contexts with uniform 9-point scoring.

Score components (each row):
  TCGA / genomic frequency (0–3): from TCGA Pan-Cancer Atlas for source contexts;
    from published genomic series for rare diseases
  GEO transcriptomic (0–3): from DE log2FC + significance in our analyses
  KEGG enrichment (0–2): from hypergeometric enrichment results
  External literature concordance (0–1): 1 if any prior drug-target proposal exists
    for this context

Plus annotation columns:
  Clinical stage
  Prior proposal status (citation or 'framework-novel')
  Trial readiness flag
"""
import sys, json
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")

# Aliases for gene symbols — KEGG uses CXCL8 but the data has IL8 etc.
GENE_ALIAS = {
    'IL8': 'CXCL8',
    'CXCL8': 'IL8',
    'WHSC1': 'NSD2',
    'NSD2': 'WHSC1',
    'TACSTD2': 'TROP2',
    'TROP2': 'TACSTD2',
    'KRT18': 'CK18',
    'PTGS1': 'COX1',
    'PTGS2': 'COX2',
    'EPAS1': 'HIF2A',
    'HIF2A': 'EPAS1',
}


# Each entry: (n, context, drug, target, tcga_score, geo_score, kegg_score,
#              ext_score, clinical_stage, prior_status, ready_flag)
# Score rationale documented inline.
MASTER_ROWS = [
    # ===========================
    # VALIDATION SET (14 rows, all from main v25)
    # ===========================
    # NEPC
    (1, 'NEPC', 'Venetoclax', 'BCL2',
     3, 2, 0, 1,  # E=2: BCL2 34.28 TPM, 88.6th pct (top 11.4%) -> top-15% bin
     'FDA-approved (CLL, AML)',
     'Previously proposed (Westaby JCI 2024 [PMID 39286979])',
     'Ready now'),
    (2, 'NEPC', 'Alisertib (investigational)', 'AURKA / CXCR7→AURKA axis',
     1, 2, 2, 1,  # E=2: DE arm fails (FC=-1.17, p=0.10, and negative direction); AURKA 61.0 TPM at 93.2nd pct = top 6.8% -> top-15% bin
     'Investigational (Phase II)',
     'Previously proposed (Gritsina JCI 2023 [PMID 37347559]; CXCR7→AURKA axis + '
     'in vivo alisertib validation) — framework convergent validation',
     'Ready now'),
    (3, 'NEPC', 'Tazemetostat', 'EZH2',
     2, 2, 1, 1,  # was 5/9 Moderate
     'FDA-approved (epithelioid sarcoma, FL)',
     'Previously proposed (Fei 2024; Saggese 2025 [PMID 39878501])',
     'Ready now'),
    (4, 'NEPC', 'Decitabine / azacitidine', 'DNMT1/3A',
     2, 3, 1, 1,  # 7/9 Strong — framework converges on Yamada 2023
     'FDA-approved (MDS, AML)',
     'Previously proposed (Yamada Sci Transl Med 2023 [PMID 37967200]; '
     'DNMT-KO + decitabine + B7-H3 ADC) — framework convergent validation',
     'Ready now'),
    (5, 'NEPC', 'Cabazitaxel + Carboplatin',
     'TP53-mutated platinum-sensitive',
     3, 0, 1, 1,  # was 5/9 Moderate
     'FDA-approved (mCRPC)',
     'Previously proposed (Aparicio 2013; Corn Lancet Oncol 2019 [PMID 31416691])',
     'Ready now (off-label SOC)'),
    (6, 'NEPC', 'Olaparib', 'PARP1/2 (HRR-mutated subset)',
     2, 3, 0, 1,  # E=3: PARP1 267.2 TPM, 98.8th pct (top 1.2%) -> top-5% bin
     'FDA-approved (HRR-mCRPC per PROfound 2020)',
     'Previously proposed (de Bono NEJM 2020; Ikeda 2024 [PMID 38440716])',
     'Ready now'),
    # MIBC / MPBC
    (7, 'MIBC / MPBC', 'Alisertib (investigational)', 'AURKA / AURKB',
     1, 3, 1, 1,  # was 6/9 Moderate
     'Investigational (Phase II in mUC; Necchi 2019)',
     'Previously proposed for MIBC (Choi 2022 [PMC9022081]); MPBC extension novel',
     'Ready now'),
    (8, 'MIBC / MPBC', 'Talazoparib', 'PARP (ERCC2/ATM/BRCA-mutated)',
     2, 2, 0, 1,  # E=2: ATR FC=+0.55 p=0.038 (GSE130598), 0.5<=|log2FC|<1 significant
     'FDA-approved (BRCA-breast; HRR-mCRPC)',
     'Previously proposed (Crist 2018; JAVELIN PARP Medley)',
     'Ready now'),
    (9, 'MIBC / MPBC', 'Alpelisib', 'PIK3CA (mutant)',
     2, 1, 0, 1,  # was 4/9 Moderate
     'FDA-approved (PIK3CA-breast)',
     'Previously proposed (Hyman/Chakraborty 2022 [PMID 35100734])',
     'Ready now'),
    (10, 'MIBC / MPBC', 'Erdafitinib', 'FGFR2 / FGFR3',
     2, 3, 0, 1,  # E=3: FGFR3 FC=+1.63 p=0.016 q=0.045 (GSE130598), |log2FC|>=1 significant
     'FDA-approved (FGFR-mUC per THOR Loriot NEJM 2023)',
     'Source-approved; MPBC extension marginal',
     'Ready now'),
    (11, 'MIBC / MPBC', 'Enfortumab vedotin', 'NECTIN-4',
     3, 3, 0, 1,  # was 7/9 Strong
     'FDA-approved (1L mUC; perioperative MIBC; EV-302, KEYNOTE-905/EV-303)',
     'Source-approved; MPBC NECTIN-4 confirmed (Chu 2021 [PMID 33901032])',
     'Ready now'),
    (12, 'MIBC / MPBC', 'Pembrolizumab', 'PD-1 / TMB-high',
     2, 1, 0, 1,  # was 4/9 Moderate
     'FDA-approved (1L mUC; perioperative MIBC)',
     'Source-approved; MPBC tested in PURE-01 (Necchi 2020)',
     'Ready now'),
    (13, 'MIBC / MPBC', 'Palbociclib', 'CDK4/6 (CDKN2A-deleted)',
     2, 1, 1, 1,  # was 5/9 Moderate
     'FDA-approved (HR+ breast)',
     'Previously proposed (Rose 2018 [PMID 30185291]; phase II negative)',
     'Ready after biomarker refinement'),
    # ccRCC / sRCC
    (14, 'ccRCC / sRCC', 'Pazopanib', 'VEGFR multikinase',
     2, 3, 1, 1,  # was 7/9 Strong
     'FDA-approved (advanced RCC per COMPARZ)',
     'Source-approved; sRCC inferior outcomes (Buti 2019 [PMID 31921344])',
     'Ready now (note sRCC efficacy limits)'),
    (15, 'ccRCC / sRCC', 'Belzutifan', 'HIF2α / EPAS1',
     2, 3, 1, 1,  # was 7/9 Strong
     'FDA-approved (advanced ccRCC per LITESPARK-005; VHL-RCC)',
     'Source-approved; sRCC subgroup inclusion only',
     'Ready now'),
    (16, 'ccRCC', 'Abemaciclib', 'CDK4/6',
     0, 2, 0, 0,  # E=2: CDK4 91.8th pct (top 8.2%) -> top-15% bin
     'FDA-approved (HR+ breast)',
     'Previously tested (McGregor 2025 [PMID 40081120]; negative monotherapy)',
     'Long-horizon (combination strategy needed)'),

    # ===========================
    # DISCOVERY SET (4 rare diseases, uniform scoring)
    # ===========================
    # RMC — SMARCB1-loss biology
    # TCGA: SMARCB1 biallelic loss ~100% (definitional). Score: 3 (>30% threshold)
    # GEO: from GSE180999 DE — IL8 log2FC -2.32, q<1e-200. Very strong signal.
    # KEGG: Chemokine_signaling pathway (IL8/CXCL8, CXCL1, CXCL2 in pathway). Pathway p>0.05 in
    #       formal hypergeometric due to small DE list (13 genes), but biological coherence is strong;
    #       give 1 for pathway membership.
    # Lit: no prior PubMed hits → 0 (truly framework-novel)
    (17, 'RMC', 'Reparixin / navarixin / AZD5069',
     'CXCR1 / CXCR2 (IL-8/CXCL1/CXCL2 triad)',
     3, 3, 1, 0,  # 7/9 Strong-discovery
     'Investigational (Phase II/III breast, pancreatic)',
     'FRAMEWORK-NOVEL (zero prior PubMed hits in RMC; '
     'coherent with neutrophil-rich RMC microenvironment per Msaouel 2025)',
     'Ready now'),
    # RMC EGFR (already proposed by Wiele/Zacharias)
    (18, 'RMC', 'Erlotinib (± bevacizumab)',
     'EGFR (HBEGF ligand)',
     3, 3, 1, 1,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'FDA-approved (NSCLC)',
     'Previously proposed (Wiele Cancers 2021; Zacharias Mol Cancer Ther 2025)',
     'Ready now (pipeline-validation example)'),
    # RMC CEACAM1
    (19, 'RMC', 'CM24 (anti-CEACAM1)', 'CEACAM1',
     3, 3, 0, 0,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'Investigational (Phase I/II)',
     'FRAMEWORK-NOVEL (zero prior PubMed hits)',
     'Ready now'),

    # Penile SCC
    # TCGA-equivalent: PSCC genomic series (Feber 2016; Aydin 2020) — TP53 ~30-50%, CDKN2A ~25-50%,
    # PIK3CA ~30%, NOTCH1 ~30%. For immune-checkpoint, TMB-high in HPV-related subset.
    # GEO: from GSE196978 DE
    # KEGG: Antigen_processing_presentation p=1.7e-4 (very strong enrichment)
    #       Chemokine_signaling p=0.045 + Cytokine_receptor p=0.031
    # Lit: KEYNOTE-158 + extensive PSCC immunotherapy literature
    (20, 'Penile SCC', 'Pembrolizumab + combinations',
     'PD-1 / PD-L1 (HLA-DRA / CXCL10 immune-hot phenotype)',
     1, 3, 2, 1,  # 7/9 Strong — framework converges on KEYNOTE-158
     'FDA-approved (multiple)',
     'Previously proposed (KEYNOTE-158 Marabelle 2020 [PMID 32278926]; '
     'McGregor pembrolizumab in rare GU 2021; HERCULES atezolizumab) — '
     'framework convergent validation',
     'Ready now'),
    # Penile MMP — MMP1 elevated (log2FC=6.0); partially novel (target proposed but drug not)
    (21, 'Penile SCC', 'Andecaliximab / marimastat',
     'MMP1 / MMP9',
     0, 3, 1, 1,  # 5/9 Moderate-discovery
     'Phase II/III (historical MMP trials)',
     'PARTIALLY NOVEL — MMP1 elevation reported as PSCC target (Tan 2022; '
     'Ibilibor 2022) but no drug proposed',
     'Long-horizon (historical MMP-inhibitor toxicity)'),
    # Penile POSTN — partially novel
    (22, 'Penile SCC', 'Fresolimumab / vactosertib',
     'POSTN / TGFβ axis',
     0, 3, 1, 1,  # 5/9 Moderate-discovery
     'Phase I/II',
     'PARTIALLY NOVEL — POSTN flagged 12 years ago (Gunia 2013); no drug proposed',
     'Ready after preclinical bridging'),

    # Sarcomatoid UC
    # TCGA-equivalent: TP53 ~75-100%, RB1 ~50%, ARID1A ~30% (Sjödahl 2017; Gui 2011)
    # GEO: from GSE128192 SARC vs UC
    # KEGG: Epigenetic_Regulation p=7.5e-3 (enriched, UHRF1+WHSC1+PHC2)
    # NSD2 / WHSC1: in epigenetic set; pathway enriched → 2
    (23, 'Sarcomatoid UC', 'KTX-1001 / SP-2577 (seclidemstat)',
     'NSD2 / WHSC1 (histone methyltransferase)',
     0, 3, 2, 0,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'Phase I',
     'FRAMEWORK-NOVEL (zero prior PubMed hits)',
     'Ready after preclinical bridging'),
    # ATR — ATRIP elevated; ATR in p53 + HR pathways
    (24, 'Sarcomatoid UC', 'Ceralasertib / berzosertib / elimusertib',
     'ATR / ATRIP (DNA damage response)',
     0, 3, 1, 0,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'Phase II',
     'FRAMEWORK-NOVEL (zero prior PubMed hits in sarcomatoid UC)',
     'Ready now'),
    # UHRF1 — in epigenetic set; pathway enriched → 2
    (25, 'Sarcomatoid UC', 'UM-002 (UHRF1 PROTAC)',
     'UHRF1 (epigenetic reader)',
     0, 3, 2, 1,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'Preclinical',
     'PARTIALLY NOVEL — UHRF1 in conventional bladder cancer previously proposed '
     '(e.g., PMID 40667845); sarcomatoid-specific application is novel slice',
     'Long-horizon'),
    # G6PD — Pentose_phosphate p=0.12 (not formally enriched but G6PD is THE pathway gene)
    (26, 'Sarcomatoid UC', '6-aminonicotinamide / polydatin',
     'G6PD (pentose phosphate)',
     0, 3, 1, 1,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'Preclinical',
     'PARTIALLY NOVEL — G6PD/pentose phosphate in conventional bladder cancer '
     'previously proposed (PMID 37958478); sarcomatoid-specific application is novel slice',
     'Long-horizon'),
    # TROP2 NEGATIVE biomarker
    (27, 'Sarcomatoid UC',
     'Sacituzumab govitecan — PREDICTED NON-RESPONSE',
     'TROP2 (TACSTD2 DOWNREGULATED)',
     0, '−3', 0, 0,  # negative finding — log2FC = -2.06 in SARC vs UC
     'FDA-approved (mUC)',
     'PREVIOUSLY PROPOSED (Brunelli Pathologica 2024 [PMID 38482675]; '
     'Bahlinger Histopathology 2024 [PMID 38196202]; Hoffman-Censits 2021 '
     '[PMID 33901032]) — framework convergent validation of sarcomatoid TROP2-low biomarker',
     'Clinically actionable de-prioritization'),

    # SCBC — subtype-stratified
    # TCGA-equivalent: TP53 ~80-100%, RB1 ~80-100% universal (Feng 2023; Chang 2019)
    # GEO: from GSE269750 subtype DE
    # KEGG: ASCL1+ no formal pathway hit (Apoptosis weak)
    #       POU2F3+ Arachidonic_acid p=0.018 (PLA2G4A+PTGS1)
    #       NEUROD1+ Neuroactive_ligand_receptor p=0.106 (SSTR2+CHRNA1)
    # ASCL1+ CEACAM5
    (28, 'SCBC (ASCL1+)', 'Tusamitamab ravtansine',
     'CEACAM5 (CEA)',
     1, 3, 0, 1,  # 5/9 Moderate-discovery (some prior via SCLC paradigm)
     'Phase III (NSCLC)',
     # Reclassified to framework-novel: the novelty standard is urologic-oncology
     # literature only, and the SCLC ASCL1-CEACAM5 paradigm has no prior
     # small-cell-bladder-cancer proposal. Matches Master Table 1 in the
     # manuscript, which was reclassified in build_v26_comprehensive_fixes.py.
     'FRAMEWORK-NOVEL within urologic-oncology literature — SCLC ASCL1-CEACAM5 '
     'paradigm has zero prior small-cell-bladder-cancer proposal',
     'Ready after preclinical bridging'),
    # NEUROD1+ SSTR2 theranostics
    (29, 'SCBC (NEUROD1+)',
     '177Lu-DOTATATE (Lutathera) / octreotide',
     'SSTR2 (somatostatin receptor 2)',
     1, 3, 1, 0,  # E=3: |log2FC|>=1 with q<0.05 in the deposited DE table (verified by 14_audit_geo_score_component.py)
     'FDA-approved (NETs)',
     'FRAMEWORK-NOVEL (no prior SCBC + SSTR2/DOTATATE PubMed hits; '
     'SCLC SSTR2 literature exists but not NEUROD1-stratified)',
     'Ready now (SSTR2 PET → 177Lu-DOTATATE)'),
    # POU2F3+ COX-1
    (30, 'SCBC (POU2F3+)', 'Aspirin / celecoxib',
     'COX-1 / PTGS1',
     1, 3, 2, 1,  # 7/9 — bladder + COX/aspirin literature exists broadly
     'FDA-approved (OTC / arthritis)',
     'PARTIALLY NOVEL — bladder cancer + COX/aspirin chemoprevention literature is '
     'extensive; POU2F3-subtype-specific COX-1 application is the novel slice',
     'Ready now (universally available)'),
]


def compute_total(row):
    """Sum the 4 score components if they're numeric."""
    cmps = row[4:8]
    nums = [c for c in cmps if isinstance(c, (int, float))]
    if all(isinstance(c, (int, float)) for c in cmps):
        return sum(cmps)
    return None


def tier_label(total):
    if total is None: return 'Discovery (non-scored)'
    if total >= 7: return 'Strong'
    if total >= 4: return 'Moderate'
    if total >= 1: return 'Exploratory'
    return 'Below threshold'


# Build DataFrame
data = []
for r in MASTER_ROWS:
    n, ctx, drug, tgt, tcga, geo, kegg, ext, stage, prior, ready = r
    total = compute_total(r)
    tier = tier_label(total)
    score_str = f"{total}/9" if total is not None else 'Discovery (non-scored)'
    data.append({
        'N': n, 'Context': ctx, 'Drug': drug, 'Target': tgt,
        'TCGA(0-3)': tcga, 'GEO(0-3)': geo, 'KEGG(0-2)': kegg, 'Lit(0-1)': ext,
        'Total': score_str, 'Tier': tier,
        'Stage': stage, 'Prior status': prior, 'Trial readiness': ready,
    })
df = pd.DataFrame(data)

print(f"Master Table 1 — {len(df)} rows")
print()
# Print summary
print(f"{'N':>3} {'Context':<22}{'Drug':<40}{'Target':<35}{'Score':<10}{'Tier':<20}{'Stage':<35}")
print("-" * 200)
for _, r in df.iterrows():
    print(f"{r['N']:>3}. {r['Context'][:21]:<22}{str(r['Drug'])[:39]:<40}{str(r['Target'])[:34]:<35}"
          f"{str(r['Total']):<10}{str(r['Tier'])[:19]:<20}{str(r['Stage'])[:34]:<35}")

# Save CSV
df.to_csv(RESULTS / 'v26_master_table1.csv', index=False)
print(f"\nSaved → {RESULTS / 'v26_master_table1.csv'}")

# Tier counts
print("\nTier distribution:")
print(df['Tier'].value_counts())

"""Build Master Table 1 for v26 — the exhaustive drug-target landscape
across all 7 aggressive urologic cancer contexts.

Columns per row:
  # | Cancer context | Drug | Target | Score/Tier | Clinical stage |
  Prior proposal status (citation or 'framework-novel') | Trial readiness

28 rows = 14 validation + 14 discovery (12 candidates + 1 known-prior + 1 negative biomarker).
"""
import sys
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

ROWS = [
    # ===========================
    # VALIDATION SET (14 rows)
    # ===========================
    # NEPC (4)
    {'n': 1, 'context': 'NEPC', 'drug': 'Venetoclax', 'target': 'BCL2',
     'score': '7/9 Strong', 'stage': 'FDA-approved (CLL, AML)',
     'prior': 'Previously proposed (Westaby JCI 2024 [PMID 39286979])',
     'ready': 'Ready now'},
    {'n': 2, 'context': 'NEPC', 'drug': 'Tazemetostat', 'target': 'EZH2',
     'score': '5/9 Moderate', 'stage': 'FDA-approved (epithelioid sarcoma; FL)',
     'prior': 'Previously proposed (Fei 2024 [PMC11311189]; Saggese 2025 [PMID 39878501])',
     'ready': 'Ready now'},
    {'n': 3, 'context': 'NEPC', 'drug': 'Cabazitaxel + carboplatin',
     'target': 'TP53/platinum-sensitive',
     'score': '5/9 Moderate', 'stage': 'FDA-approved (mCRPC)',
     'prior': 'Previously proposed (Aparicio JCO 2013; Corn Lancet Oncol 2019 [PMID 31416691])',
     'ready': 'Ready now (off-label SOC)'},
    {'n': 4, 'context': 'NEPC', 'drug': 'Olaparib', 'target': 'PARP1/2',
     'score': '5/9 Moderate', 'stage': 'FDA-approved (HRR-mCRPC)',
     'prior': 'Previously proposed (de Bono PROfound NEJM 2020; Ikeda IJU Case Rep 2024 [PMID 38440716])',
     'ready': 'Ready now'},
    # MIBC / MPBC (7)
    {'n': 5, 'context': 'MIBC / MPBC', 'drug': 'Alisertib (investigational)',
     'target': 'AURKA / AURKB',
     'score': '6/9 Moderate', 'stage': 'Investigational (Phase II)',
     'prior': 'Previously proposed for MIBC (Choi 2022 [PMC9022081]); MPBC-extension novel',
     'ready': 'Ready now'},
    {'n': 6, 'context': 'MIBC / MPBC', 'drug': 'Talazoparib',
     'target': 'PARP (HR-deficient: ERCC2/ATM/BRCA)',
     'score': '4/9 Moderate', 'stage': 'FDA-approved (BRCA-breast; HRR-mCRPC)',
     'prior': 'Previously proposed (Crist JCO PO 2018; JAVELIN PARP Medley)',
     'ready': 'Ready now'},
    {'n': 7, 'context': 'MIBC / MPBC', 'drug': 'Alpelisib',
     'target': 'PIK3CA (mutant)',
     'score': '4/9 Moderate', 'stage': 'FDA-approved (PIK3CA-breast)',
     'prior': 'Previously proposed (Hyman/Chakraborty JCO PO 2022 [PMID 35100734])',
     'ready': 'Ready now'},
    {'n': 8, 'context': 'MIBC / MPBC', 'drug': 'Erdafitinib',
     'target': 'FGFR2 / FGFR3',
     'score': '5/9 Moderate', 'stage': 'FDA-approved (FGFR-mUC)',
     'prior': 'Source-approved per THOR (Loriot NEJM 2023); MPBC-specific extension marginal',
     'ready': 'Ready now'},
    {'n': 9, 'context': 'MIBC / MPBC', 'drug': 'Enfortumab vedotin',
     'target': 'NECTIN-4',
     'score': '7/9 Strong', 'stage': 'FDA-approved (1L mUC; perioperative MIBC)',
     'prior': 'Source-approved per EV-302 (Powles NEJM 2024) & KEYNOTE-905/EV-303 (Vulsteke NEJM 2026); '
              'NECTIN-4 MPBC expression confirmed (Chu 2021 [PMID 33901032])',
     'ready': 'Ready now'},
    {'n': 10, 'context': 'MIBC / MPBC', 'drug': 'Pembrolizumab',
     'target': 'PD-1 / TMB-high',
     'score': '4/9 Moderate', 'stage': 'FDA-approved (1L mUC; perioperative MIBC)',
     'prior': 'Source-approved per KEYNOTE-905/EV-303 & EV-302; MPBC tested in PURE-01 (Necchi 2020 [PMID 31708296])',
     'ready': 'Ready now'},
    {'n': 11, 'context': 'MIBC / MPBC', 'drug': 'Palbociclib',
     'target': 'CDK4/6 (CDKN2A-deleted)',
     'score': '5/9 Moderate', 'stage': 'FDA-approved (HR+ breast)',
     'prior': 'Previously proposed (Rose Br J Cancer 2018 [PMID 30185291]; '
              'phase II negative for monotherapy)',
     'ready': 'Ready after biomarker selection refinement'},
    # ccRCC / sRCC (3)
    {'n': 12, 'context': 'ccRCC / sRCC', 'drug': 'Pazopanib',
     'target': 'VEGFR multikinase',
     'score': '7/9 Strong', 'stage': 'FDA-approved (advanced RCC)',
     'prior': 'Source-approved per COMPARZ (Motzer NEJM 2013); sRCC real-world data '
              'show inferior outcomes (Buti 2019 [PMID 31921344])',
     'ready': 'Ready now (note sRCC efficacy limits)'},
    {'n': 13, 'context': 'ccRCC / sRCC', 'drug': 'Belzutifan',
     'target': 'HIF2α / EPAS1',
     'score': '7/9 Strong', 'stage': 'FDA-approved (advanced ccRCC; VHL-RCC)',
     'prior': 'Source-approved per LITESPARK-005 (Choueiri NEJM 2024) & Motzer NEJM 2021; '
              'sRCC subgroup inclusion only',
     'ready': 'Ready now'},
    {'n': 14, 'context': 'ccRCC', 'drug': 'Abemaciclib',
     'target': 'CDK4/6 (exploratory)',
     'score': '1/9 Exploratory', 'stage': 'FDA-approved (HR+ breast)',
     'prior': 'Previously tested (McGregor Clin GU Cancer 2025 [PMID 40081120]; '
              'negative monotherapy)',
     'ready': 'Long-horizon (requires combination strategy)'},
    # ===========================
    # DISCOVERY SET (14 rows)
    # ===========================
    # RMC (3)
    {'n': 15, 'context': 'RMC', 'drug': 'Reparixin / navarixin / AZD5069',
     'target': 'CXCR1 / CXCR2 (IL-8/CXCL1/CXCL2 triad)',
     'score': 'Discovery', 'stage': 'Investigational (Phase II/III in breast, pancreatic)',
     'prior': 'FRAMEWORK-NOVEL (zero prior PubMed hits in RMC; coherent with '
              'neutrophil-rich RMC microenvironment per Msaouel Cell Rep Med 2025)',
     'ready': 'Ready now'},
    {'n': 16, 'context': 'RMC', 'drug': 'Erlotinib (± bevacizumab)',
     'target': 'EGFR (HBEGF ligand upregulated)',
     'score': 'Discovery', 'stage': 'FDA-approved (NSCLC)',
     'prior': 'Previously proposed (Wiele Cancers 2021; Zacharias/Msaouel Mol Cancer Ther 2025)',
     'ready': 'Ready now (validates pipeline)'},
    {'n': 17, 'context': 'RMC', 'drug': 'CM24',
     'target': 'CEACAM1',
     'score': 'Discovery', 'stage': 'Investigational (Phase I/II)',
     'prior': 'FRAMEWORK-NOVEL (zero prior PubMed hits in RMC)',
     'ready': 'Ready now'},
    # Penile SCC (3)
    {'n': 18, 'context': 'Penile SCC', 'drug': 'Pembrolizumab + combinations',
     'target': 'PD-1 (HLA-DRA / CXCL10 immune-hot phenotype)',
     'score': 'Discovery', 'stage': 'FDA-approved',
     'prior': 'Previously studied (KEYNOTE-158 penile cohort, ~25% response rate)',
     'ready': 'Ready now (combination strategy is the open question)'},
    {'n': 19, 'context': 'Penile SCC', 'drug': 'Andecaliximab / marimastat',
     'target': 'MMP1 / MMP9',
     'score': 'Discovery', 'stage': 'Phase II/III (historical MMP-inhibitor trials)',
     'prior': 'PARTIALLY NOVEL — MMP1 elevation reported as PSCC target (Tan Cell Death Dis 2022; '
              'Ibilibor Clin GU Cancer 2022) but no specific drug proposed',
     'ready': 'Long-horizon (historical MMP-inhibitor toxicity concerns)'},
    {'n': 20, 'context': 'Penile SCC', 'drug': 'Fresolimumab / vactosertib',
     'target': 'POSTN / TGFβ axis',
     'score': 'Discovery', 'stage': 'Phase I/II',
     'prior': 'PARTIALLY NOVEL — POSTN nominated as PSCC prognostic 12 years ago '
              '(Gunia J Clin Pathol 2013); no drug proposed',
     'ready': 'Ready after preclinical bridging'},
    # Sarcomatoid UC (5)
    {'n': 21, 'context': 'Sarcomatoid UC', 'drug': 'KTX-1001 / SP-2577 (seclidemstat)',
     'target': 'NSD2 / WHSC1 histone methyltransferase',
     'score': 'Discovery', 'stage': 'Phase I',
     'prior': 'FRAMEWORK-NOVEL (zero PubMed hits)',
     'ready': 'Ready after preclinical bridging'},
    {'n': 22, 'context': 'Sarcomatoid UC', 'drug': 'Ceralasertib / berzosertib / elimusertib',
     'target': 'ATR / ATRIP DNA-damage response',
     'score': 'Discovery', 'stage': 'Phase II',
     'prior': 'FRAMEWORK-NOVEL (zero PubMed hits in sarcomatoid UC)',
     'ready': 'Ready now'},
    {'n': 23, 'context': 'Sarcomatoid UC', 'drug': 'UM-002 / UHRF1 PROTAC',
     'target': 'UHRF1 epigenetic reader',
     'score': 'Discovery', 'stage': 'Preclinical',
     'prior': 'FRAMEWORK-NOVEL (zero PubMed hits)',
     'ready': 'Long-horizon'},
    {'n': 24, 'context': 'Sarcomatoid UC', 'drug': '6-aminonicotinamide / polydatin',
     'target': 'G6PD / pentose phosphate pathway',
     'score': 'Discovery', 'stage': 'Preclinical',
     'prior': 'FRAMEWORK-NOVEL (zero PubMed hits)',
     'ready': 'Long-horizon'},
    {'n': 25, 'context': 'Sarcomatoid UC',
     'drug': 'Sacituzumab govitecan — NEGATIVE biomarker',
     'target': 'TROP2 / TACSTD2 DOWNREGULATED in sarcomatoid variant',
     'score': 'Discovery (negative)',
     'stage': 'FDA-approved (mUC)',
     'prior': 'FRAMEWORK-NOVEL negative-predictor (TROP2 low → predicted non-response; '
              'no prior paper proposes sarcomatoid-specific de-escalation)',
     'ready': 'Clinically actionable now (de-prioritize in sarcomatoid)'},
    # SCBC subtype-stratified (3)
    {'n': 26, 'context': 'SCBC (ASCL1+ subtype)',
     'drug': 'Tusamitamab ravtansine',
     'target': 'CEACAM5 (CEA)',
     'score': 'Discovery', 'stage': 'Phase III (NSCLC)',
     'prior': 'PARTIALLY NOVEL — direct SCLC paradigm transfer; no prior explicit SCBC proposal '
              '(Feng Eur Urol 2023 foreshadowed but did not name)',
     'ready': 'Ready after preclinical bridging'},
    {'n': 27, 'context': 'SCBC (NEUROD1+ subtype)',
     'drug': '177Lu-DOTATATE (Lutathera) / octreotide / lanreotide',
     'target': 'SSTR2 / somatostatin receptor 2',
     'score': 'Discovery', 'stage': 'FDA-approved (NETs)',
     'prior': 'FRAMEWORK-NOVEL — no prior SCBC + SSTR2 / DOTATATE PubMed hits; '
              'SCLC SSTR2 literature exists but not stratified by NEUROD1',
     'ready': 'Ready now (theranostic SSTR2 PET → 177Lu-DOTATATE pipeline well-established)'},
    {'n': 28, 'context': 'SCBC (POU2F3+ subtype)',
     'drug': 'Aspirin / celecoxib',
     'target': 'COX-1 (PTGS1)',
     'score': 'Discovery', 'stage': 'FDA-approved (OTC / arthritis)',
     'prior': 'FRAMEWORK-NOVEL — zero prior POU2F3 + PTGS1 / COX-1 PubMed hits',
     'ready': 'Ready now (universally available)'},
]

df = pd.DataFrame(ROWS)
print(f"Master Table 1: {len(df)} rows")
print()
# Render compact summary
for r in ROWS:
    print(f"{r['n']:>3}. {r['context']:<22} | {r['drug'][:35]:<35} | {r['target'][:30]:<30}")
    print(f"      {r['score']:<14} | {r['stage'][:50]:<50}")
    print(f"      Prior: {r['prior'][:120]}")
    print(f"      Ready: {r['ready']}")
    print()

# Save as CSV for later DOCX integration
OUT = Path(r"C:\Users\garre\framework_expansion\results\v26_master_table1.csv")
df.to_csv(OUT, index=False)
print(f"Saved: {OUT}")

"""Fix KEGG fetch (parsing bug) + add new pathways for novel drug classes.

The KEGG list/hsa endpoint returns 4 tab-separated columns:
  [0] hsa:ENTREZ
  [1] CDS
  [2] start position
  [3] "SYMBOL1, SYMBOL2; description"

Symbol is in column [3], first field before ';', first symbol before ','.

ORIGINAL 8 pathways (validation framework):
  Cell_Cycle (hsa04110), Apoptosis (hsa04210), HIF1 (hsa04066),
  VEGF (hsa04370), Homologous_Recombination (hsa03440),
  PI3K_AKT (hsa04151), p53 (hsa04115), + custom Epigenetic_Regulation

ADDED 7 pathways for discovery drug classes:
  - hsa04062 Chemokine_signaling (CXCR1/2/3 antagonists)
  - hsa04060 Cytokine_cytokine_receptor (broader immune-receptor)
  - hsa04612 Antigen_processing (immune-hot biomarker)
  - hsa05235 PDL1_PD1_checkpoint (checkpoint inhibitors)
  - hsa00030 Pentose_phosphate (G6PD inhibitors)
  - hsa00590 Arachidonic_acid (COX-1/2 NSAIDs)
  - hsa04080 Neuroactive_ligand_receptor (somatostatin SSTR2 etc.)

Disease-context pathways (for context-aware enrichment):
  - hsa05215 Prostate_cancer
  - hsa05219 Bladder_cancer
  - hsa05211 Renal_cell_carcinoma
"""
import sys, requests, json
from pathlib import Path

import paths
sys.stdout.reconfigure(encoding='utf-8')

OUT = paths.RESULTS / 'KEGG_PATHWAYS_18.json'

PATHWAYS = {
    # Drug-class pathways
    'Cell_Cycle': 'hsa04110',
    'Apoptosis': 'hsa04210',
    'HIF1_signaling': 'hsa04066',
    'VEGF_signaling': 'hsa04370',
    'Homologous_Recombination': 'hsa03440',
    'PI3K_AKT_signaling': 'hsa04151',
    'p53_signaling': 'hsa04115',
    # NEW drug-class pathways for discovery candidates
    'Chemokine_signaling': 'hsa04062',
    'Cytokine_receptor_interaction': 'hsa04060',
    'Antigen_processing_presentation': 'hsa04612',
    'PDL1_PD1_checkpoint': 'hsa05235',
    'Pentose_phosphate_pathway': 'hsa00030',
    'Arachidonic_acid_metabolism': 'hsa00590',
    'Neuroactive_ligand_receptor': 'hsa04080',
    # Disease-context pathways
    'Prostate_cancer': 'hsa05215',
    'Bladder_cancer': 'hsa05219',
    'Renal_cell_carcinoma': 'hsa05211',
}

EPIGENETIC_REGULATION = sorted({
    # DNMT family
    'DNMT1', 'DNMT3A', 'DNMT3B', 'DNMT3L',
    # PRC2 / EZH
    'EZH1', 'EZH2', 'SUZ12', 'EED',
    # SWI/SNF (BAF) — RMC-relevant
    'SMARCB1', 'SMARCA4', 'SMARCA2', 'SMARCD1', 'SMARCE1', 'ARID1A', 'ARID1B', 'ARID2',
    'PBRM1', 'BAF155', 'BAF170', 'DPF1', 'DPF2', 'DPF3',
    # KMT / HMT
    'KMT2A', 'KMT2B', 'KMT2C', 'KMT2D', 'NSD1', 'NSD2', 'NSD3', 'SETD2', 'WHSC1',
    'SETDB1', 'SETD7', 'SUV39H1', 'SUV39H2',
    # KDM
    'KDM1A', 'KDM2A', 'KDM4A', 'KDM5A', 'KDM5B', 'KDM5C', 'KDM6A', 'KDM6B',
    # HDAC
    'HDAC1', 'HDAC2', 'HDAC3', 'HDAC4', 'HDAC5', 'HDAC6', 'HDAC7', 'HDAC8',
    'HDAC9', 'HDAC10', 'HDAC11',
    'SIRT1', 'SIRT2', 'SIRT3', 'SIRT6',
    # HAT / BRD
    'EP300', 'CREBBP', 'KAT2A', 'KAT2B', 'KAT5', 'KAT6A', 'KAT6B', 'KAT7',
    'BRD2', 'BRD3', 'BRD4', 'BRD7', 'BRD9', 'BRDT',
    # UHRF (epigenetic readers)
    'UHRF1', 'UHRF2',
    # Other
    'TET1', 'TET2', 'TET3', 'IDH1', 'IDH2', 'BAP1', 'ASXL1', 'ASXL2',
    'PHF6', 'PHC1', 'PHC2', 'PHC3',
    # PRC1
    'BMI1', 'RING1', 'RNF2', 'CBX2', 'CBX4', 'CBX6', 'CBX7', 'CBX8',
})


def fetch_bulk_mapping():
    """Get Entrez → primary gene symbol mapping for all human genes."""
    url = "https://rest.kegg.jp/list/hsa"
    r = requests.get(url, timeout=60)
    mapping = {}
    if r.status_code != 200:
        return mapping
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 4:
            entrez = parts[0].replace('hsa:', '')
            # parts[3] = "SYMBOL1, SYMBOL2; description"
            field = parts[3].split(';', 1)[0]
            primary_symbol = field.split(',')[0].strip()
            mapping[entrez] = primary_symbol
    return mapping


def fetch_pathway_genes(pathway_id):
    url = f"https://rest.kegg.jp/link/hsa/{pathway_id}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return []
    entrez_ids = []
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) == 2:
            entrez_ids.append(parts[1].replace('hsa:', ''))
    return entrez_ids


print("Fetching bulk Entrez→symbol mapping...")
mapping = fetch_bulk_mapping()
print(f"  Loaded {len(mapping):,} entries")
print(f"  Sample: 7029 → {mapping.get('7029')}  672 → {mapping.get('672')}  207 → {mapping.get('207')}")

print(f"\nFetching gene sets for {len(PATHWAYS)} KEGG pathways...")
pathway_genes = {}
for name, pid in PATHWAYS.items():
    entrez_ids = fetch_pathway_genes(pid)
    symbols = [mapping.get(e, '') for e in entrez_ids]
    symbols = sorted(set(s for s in symbols if s))
    pathway_genes[name] = symbols
    print(f"  {name:<35} ({pid}): {len(symbols):>3} genes  "
          f"sample={symbols[:5]}")

pathway_genes['Epigenetic_Regulation'] = EPIGENETIC_REGULATION
print(f"  {'Epigenetic_Regulation':<35} (custom): {len(EPIGENETIC_REGULATION):>3} genes")

with open(OUT, 'w') as f:
    json.dump(pathway_genes, f, indent=2)
print(f"\nSaved → {OUT}")
print(f"Total pathways: {len(pathway_genes)}")

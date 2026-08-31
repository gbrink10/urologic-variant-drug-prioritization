"""Fetch the 8 pre-specified KEGG pathway gene sets used by the framework.

Pre-specified pathways (matching main manuscript Methods §2.3):
  - hsa04110 — Cell Cycle
  - hsa04210 — Apoptosis
  - hsa04066 — HIF-1 signaling
  - hsa04370 — VEGF signaling
  - hsa03440 — Homologous Recombination
  - hsa04151 — PI3K-AKT signaling
  - hsa04115 — p53 signaling
  - Custom Epigenetic Regulation set (DNMT/EZH2/PRC2/SWI-SNF/HMT/HDAC genes)

Uses KEGG REST API: rest.kegg.jp/link/hsa/pathway:hsa{NNNNN}
"""
import sys, requests, json
from pathlib import Path

import paths
sys.stdout.reconfigure(encoding='utf-8')

OUT = paths.RESULTS / 'KEGG_PATHWAYS_18.json'

PATHWAYS = {
    'Cell_Cycle': 'hsa04110',
    'Apoptosis': 'hsa04210',
    'HIF1': 'hsa04066',
    'VEGF': 'hsa04370',
    'Homologous_Recombination': 'hsa03440',
    'PI3K_AKT': 'hsa04151',
    'p53': 'hsa04115',
}

EPIGENETIC_REGULATION = [
    # DNMT family
    'DNMT1', 'DNMT3A', 'DNMT3B', 'DNMT3L',
    # PRC2 components + EZH
    'EZH1', 'EZH2', 'SUZ12', 'EED', 'EZH2-AS1',
    # SWI/SNF (BAF) components
    'SMARCB1', 'SMARCA4', 'SMARCA2', 'SMARCD1', 'SMARCE1', 'ARID1A', 'ARID1B', 'ARID2',
    'PBRM1', 'BAF155', 'BAF170', 'DPF1', 'DPF2', 'DPF3',
    # KMT / histone methyltransferases
    'KMT2A', 'KMT2B', 'KMT2C', 'KMT2D', 'NSD1', 'NSD2', 'NSD3', 'SETD2', 'WHSC1',
    'SETDB1', 'SETD7', 'SUV39H1', 'SUV39H2',
    # KDM / histone demethylases
    'KDM1A', 'KDM2A', 'KDM4A', 'KDM5A', 'KDM5B', 'KDM5C', 'KDM6A', 'KDM6B',
    # HDAC
    'HDAC1', 'HDAC2', 'HDAC3', 'HDAC4', 'HDAC5', 'HDAC6', 'HDAC7', 'HDAC8',
    'HDAC9', 'HDAC10', 'HDAC11', 'SIRT1', 'SIRT2', 'SIRT3', 'SIRT6',
    # HAT / BRD family
    'EP300', 'CREBBP', 'KAT2A', 'KAT2B', 'KAT5', 'KAT6A', 'KAT6B', 'KAT7',
    'BRD2', 'BRD3', 'BRD4', 'BRD7', 'BRD9', 'BRDT',
    # UHRF
    'UHRF1', 'UHRF2',
    # Other key epigenetic regulators
    'TET1', 'TET2', 'TET3', 'IDH1', 'IDH2', 'BAP1', 'ASXL1', 'ASXL2',
    'PHF6', 'PHC1', 'PHC2', 'PHC3',
    # PRC1
    'BMI1', 'RING1', 'RING2', 'RNF2', 'CBX2', 'CBX4', 'CBX6', 'CBX7', 'CBX8',
]


def fetch_kegg_pathway_genes(pathway_id):
    """Use KEGG REST API to fetch gene IDs in a pathway, then convert to gene symbols."""
    url = f"https://rest.kegg.jp/link/hsa/{pathway_id}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return []
    # Each line: path:hsa04110\thsa:GENE_ENTREZ_ID
    genes = []
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) == 2:
            entrez = parts[1].replace('hsa:', '')
            genes.append(entrez)
    return genes


def entrez_to_symbol(entrez_ids):
    """Convert Entrez IDs to gene symbols using KEGG REST API (list endpoint).
    Note: rate-limited; do in one batch via KEGG conv.
    """
    if not entrez_ids: return {}
    # KEGG conv: rest.kegg.jp/list/hsa returns entrez+symbol mapping
    # Single API call retrieves the full mapping
    url = "https://rest.kegg.jp/list/hsa"
    r = requests.get(url, timeout=60)
    mapping = {}
    if r.status_code == 200:
        for line in r.text.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 2:
                entrez = parts[0].replace('hsa:', '')
                # parts[1] often has multiple symbols separated by commas, plus description
                # Format: "SYMBOL1, SYMBOL2; description"
                first_field = parts[1].split(';')[0]
                primary_symbol = first_field.split(',')[0].strip()
                mapping[entrez] = primary_symbol
    return {e: mapping.get(e, '') for e in entrez_ids}


print("Fetching KEGG pathway gene sets via REST API...")
print(f"Will pre-fetch one bulk Entrez→symbol mapping then look up.")

# Bulk fetch the mapping once
entrez_symbol = entrez_to_symbol(['1'])  # triggers bulk fetch via list/hsa
print(f"Entrez→symbol mapping table: {len(entrez_symbol)} entries pre-loaded")
# Actually the function returns just for the requested IDs; let me refetch properly
url = "https://rest.kegg.jp/list/hsa"
r = requests.get(url, timeout=60)
all_mapping = {}
if r.status_code == 200:
    for line in r.text.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) >= 2:
            entrez = parts[0].replace('hsa:', '')
            first_field = parts[1].split(';')[0]
            primary_symbol = first_field.split(',')[0].strip()
            all_mapping[entrez] = primary_symbol
print(f"Bulk mapping: {len(all_mapping)} Entrez→symbol entries")

pathway_genes = {}
for name, pid in PATHWAYS.items():
    entrez_ids = fetch_kegg_pathway_genes(pid)
    symbols = [all_mapping.get(e, '') for e in entrez_ids if e in all_mapping]
    symbols = [s for s in symbols if s]
    pathway_genes[name] = symbols
    print(f"  {name} ({pid}): {len(symbols)} genes")

# Add custom Epigenetic Regulation set
pathway_genes['Epigenetic_Regulation'] = sorted(set(EPIGENETIC_REGULATION))
print(f"  Epigenetic_Regulation (custom): {len(pathway_genes['Epigenetic_Regulation'])} genes")

with open(OUT, 'w') as f:
    json.dump(pathway_genes, f, indent=2)
print(f"\nSaved → {OUT}")

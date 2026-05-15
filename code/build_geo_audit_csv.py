"""Build GEO_DATASET_AUDIT.csv — Supplementary Data 3.

23-accession curated allowlist with audit status for each.
"""
import csv
from pathlib import Path

OUT = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study\GEO_DATASET_AUDIT.csv")

# (accession, intended_cancer, status, used_in_analysis, notes)
rows = [
    # NEPC accessions (n=15 in allowlist; only some had accessible data)
    ("GSE199274", "NEPC", "Included", "Yes",
     "MDVr NEPC-like cells (LNCaP-MDVr, C4-2B-MDVr) ± shCXCR7; RPKM processed matrix accessible"),
    ("GSE216053", "NEPC", "Included", "Yes",
     "PM154 NEPC patient-derived model ± decitabine (day 14); TPM matrix accessible"),
    ("GSE216052", "NEPC", "Included", "Yes",
     "PM154 ± DNMT1/DNMT3A CRISPR knockout; TPM matrix accessible"),
    ("GSE171306", "NEPC", "Excluded (no processed)", "No",
     "Raw FASTQ only; no processed matrix on GEO at query time"),
    ("GSE185658", "NEPC", "Excluded (no processed)", "No",
     "Raw RAW.tar only; no processed expression matrix"),
    ("GSE201530", "NEPC", "Excluded (no processed)", "No",
     "Raw RAW.tar only"),
    ("GSE216050", "NEPC", "Excluded (no processed)", "No",
     "Companion to GSE216053; raw RAW.tar only"),
    ("GSE239270", "NEPC", "Excluded (no processed)", "No",
     "Raw RAW.tar only"),
    ("GSE287182", "NEPC", "Excluded (ChIP-seq)", "No",
     "ChIP-seq tracks (H3K27ac, H3K27me3, H3K4me3); not RNA-seq"),
    ("GSE152938", "NEPC", "Excluded (no processed)", "No",
     "Raw RAW.tar only"),
    ("GSE178481", "NEPC", "Excluded (no processed)", "No",
     "Raw RAW.tar only"),
    ("GSE193567", "NEPC", "Excluded (off-target)", "No",
     "Hepamut feature counts; off-target dataset"),
    ("GSE166386", "NEPC", "Excluded (off-target)", "No",
     "Off-target processed matrix; not NEPC"),
    ("GSE_NEPC_14", "NEPC", "Excluded (access)", "No",
     "Allowlisted but processed matrix not retrievable at query time"),
    ("GSE_NEPC_15", "NEPC", "Excluded (access)", "No",
     "Allowlisted but processed matrix not retrievable at query time"),

    # MIBC/MPBC accessions (n=3)
    ("GSE130598", "MIBC/MPBC-applicable", "Included", "Yes",
     "24 paired MIBC tumor / adjacent-normal; NanoString nCounter ~522-gene kinome panel"),
    ("GSE_MIBC_2", "MIBC/MPBC-applicable", "Excluded (access)", "No",
     "Allowlisted but processed matrix not retrievable at query time"),
    ("GSE_MIBC_3", "MIBC/MPBC-applicable", "Excluded (access)", "No",
     "Allowlisted but processed matrix not retrievable at query time"),

    # RCC accessions (n=5; 5 sRCC-labeled excluded by audit)
    ("GSE143630", "ccRCC", "Included", "Yes",
     "44 ccRCC samples with stage pT1/pT2 partition; htseq counts"),
    ("GSE157256", "HLRCC + aggressive RCC", "Included", "Yes",
     "VST matrix: 5 normal kidney + 5 primary HLRCC + 16 aggressive/metastatic RCC"),
    ("GSE_RCC_3", "RCC (sRCC-labeled)", "Excluded by audit", "No",
     "Originally allowlisted as sRCC; manual review found non-RCC content"),
    ("GSE_RCC_4", "RCC (sRCC-labeled)", "Excluded by audit", "No",
     "Originally allowlisted as sRCC; manual review found non-RCC content"),
    ("GSE_RCC_5", "RCC (sRCC-labeled)", "Excluded by audit", "No",
     "Originally allowlisted as sRCC; manual review found non-RCC content"),
]

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(["accession", "intended_cancer_context", "audit_status", "used_in_analysis", "notes"])
    for row in rows:
        w.writerow(row)

# Summary
total = len(rows)
included = sum(1 for r in rows if r[3] == "Yes")
excluded_by_audit = sum(1 for r in rows if "audit" in r[2].lower())
excluded_access = sum(1 for r in rows if "access" in r[2].lower() or "no processed" in r[2].lower())
print(f"Total allowlisted: {total}")
print(f"  Included (used in quantitative analysis): {included}")
print(f"  Excluded by manual audit (non-RCC content): {excluded_by_audit}")
print(f"  Excluded (no accessible processed matrix): {excluded_access}")
print(f"  Other exclusions: {total - included - excluded_by_audit - excluded_access}")
print(f"\nSaved: {OUT}")

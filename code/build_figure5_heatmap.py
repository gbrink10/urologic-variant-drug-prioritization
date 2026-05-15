"""Build new Figure 5: evidence-concordance heatmap (replacing HPA IHC images).

Rows: 10 prioritized targets across the three cancer variants.
Columns: 5 evidence axes — TCGA frequency, GEO transcriptomic, KEGG pathway,
         External literature concordance, Phase III source-disease concordance.
Cell shading: green = strong support, yellow-orange = moderate, gray = not assessed/weak.

The original Figure 5 (HPA IHC) is moved to Supplementary Figure S3.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
from pathlib import Path

OUT_DIR = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study\Manuscript_Figures_v2")
OUT_PATH = OUT_DIR / "figure5_evidence_concordance_heatmap.png"

# Row labels: (cancer, target, drug)
rows = [
    ("NEPC",          "BCL2 (venetoclax)",                    "B"),
    ("NEPC",          "AURKA (alisertib)",                    "B"),
    ("NEPC",          "EZH2 (tazemetostat)",                  "B"),
    ("NEPC",          "DNMT1/3A (decitabine)",                "B"),
    ("NEPC",          "PARP1/2 (olaparib)",                   "B"),
    ("MIBC/MPBC",     "AURKA/AURKB (alisertib)",              "B"),
    ("MIBC/MPBC",     "FGFR2/3 (erdafitinib)",                "B"),
    ("MIBC/MPBC",     "Nectin-4 (enfortumab vedotin)",        "B"),
    ("MIBC/MPBC",     "PD-1/TMB-H (pembrolizumab)",           "B"),
    ("MIBC/MPBC",     "CDK4/6 (palbociclib)",                 "B"),
    ("MIBC/MPBC",     "PARP1/2 (talazoparib)",                "B"),
    ("MIBC/MPBC",     "PIK3CA (alpelisib)",                   "B"),
    ("ccRCC/sRCC",    "VEGFR/PDGFR (pazopanib)",              "B"),
    ("ccRCC/sRCC",    "HIF2α/EPAS1 (belzutifan)",             "B"),
    ("ccRCC",         "CDK4/6 (abemaciclib)",                 "B"),
]

# Columns: 5 evidence axes
cols = ["TCGA\nfrequency", "GEO\ntranscriptomic", "KEGG\npathway", "External\nliterature", "Phase III\nsource-disease"]

# Concordance values per row × column:
# Encoding: 3 = strong, 2 = moderate, 1 = weak/partial, 0 = not assessed / minimal
# Order matches `rows` above (cancer + target/drug):
data = np.array([
    # TCGA  GEO  KEGG  Ext  PhIII
    [3,     3,   1,   3,   1],  # NEPC BCL2/venetoclax — RB1 90% NEPC; PARP1 + BCL2 TPM; Apoptosis OR=1.76 trend; Beltran/Zellweger; PROfound proxy
    [2,     2,   3,   3,   1],  # NEPC AURKA/alisertib — Cell Cycle OR=2.86 Strong; CXCR7-AURKA; Gritsina/Beltran 2019 Phase II
    [2,     2,   1,   3,   0],  # NEPC EZH2/tazemetostat — Beltran/Aggarwal; trial pending
    [2,     3,   0,   3,   0],  # NEPC DNMT/decitabine — DNMT1 TPM=124; DNMT1-KO restores RB1
    [2,     2,   1,   3,   3],  # NEPC PARP1/2/olaparib — PARP1 TPM=267; PROfound concordant
    [1,     3,   2,   3,   0],  # MIBC AURKA/AURKB/alisertib — Burgess MIBC AURKA OS HR=6.10
    [2,     2,   0,   3,   3],  # MIBC FGFR3/erdafitinib — THOR Phase III positive
    [3,     3,   0,   3,   3],  # MIBC NECTIN4/EV — EV-302 + KN-905 Phase III positive
    [2,     1,   0,   3,   3],  # MIBC PD-1/pembrolizumab — EV-302 + KN-905
    [2,     1,   2,   3,   0],  # MIBC CDK4/6/palbociclib — CDKN2A 32% del
    [2,     1,   1,   3,   0],  # MIBC PARP/talazoparib
    [2,     1,   0,   3,   0],  # MIBC PIK3CA/alpelisib
    [2,     3,   2,   3,   3],  # ccRCC VEGFR/pazopanib — COMPARZ
    [2,     3,   2,   3,   3],  # ccRCC HIF2α/belzutifan — LITESPARK-005
    [0,     1,   0,   1,   0],  # ccRCC CDK4/6/abemaciclib — exploratory only
])

# Color scheme: 0=gray (weak/none), 1=light orange, 2=yellow-green, 3=strong green
# colorblind-friendly
colors = ['#e8e8e8', '#fbb55c', '#9fcf66', '#1B7837']
cmap = ListedColormap(colors)
bounds = [-0.5, 0.5, 1.5, 2.5, 3.5]
norm = BoundaryNorm(bounds, cmap.N)

fig, ax = plt.subplots(figsize=(9.5, 6.8), dpi=300)
im = ax.imshow(data, cmap=cmap, norm=norm, aspect='auto')

# Cell text overlay (numeric concordance)
labels = ['—', 'Partial', 'Moderate', 'Strong']
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        val = int(data[i, j])
        text_color = 'white' if val == 3 else 'black'
        ax.text(j, i, labels[val], ha='center', va='center', fontsize=7.5, color=text_color)

# Axis labels
ax.set_xticks(range(len(cols)))
ax.set_xticklabels(cols, fontsize=9)
ax.set_yticks(range(len(rows)))

# Y-axis labels with cancer prefix
y_labels = []
for cancer, target_drug, _ in rows:
    y_labels.append(f"{cancer}: {target_drug}")
ax.set_yticklabels(y_labels, fontsize=8.5)

# Gridlines
ax.set_xticks(np.arange(-0.5, len(cols), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
ax.grid(which='minor', color='white', linewidth=1.5)
ax.tick_params(which='minor', length=0)
ax.tick_params(axis='x', length=0, pad=4)
ax.tick_params(axis='y', length=0, pad=4)

# Title
ax.set_title("Figure 5.  Evidence-concordance heatmap across prioritized drug–target pairings",
             fontsize=10.5, fontweight='bold', loc='left', pad=14)

# Legend
legend_handles = [
    mpatches.Patch(color='#1B7837', label='Strong support'),
    mpatches.Patch(color='#9fcf66', label='Moderate support'),
    mpatches.Patch(color='#fbb55c', label='Partial / trend'),
    mpatches.Patch(color='#e8e8e8', label='— (not assessed / minimal)'),
]
ax.legend(handles=legend_handles, loc='upper center',
          bbox_to_anchor=(0.5, -0.10), ncol=4, fontsize=8, frameon=False)

# Source line
fig.text(0.04, 0.005,
         "TCGA frequency = source-cohort alteration frequency from cBioPortal Pan-Can 2018. "
         "GEO transcriptomic = differential expression or expression-percentile ranking. "
         "KEGG pathway = pre-specified pathway enrichment. "
         "External literature = published cohort series or biomarker reports. "
         "Phase III source-disease = concordant phase III trial in the source disease.",
         fontsize=6.5, fontstyle='italic', color='gray', wrap=True)

plt.subplots_adjust(left=0.32, right=0.97, top=0.92, bottom=0.20)
plt.savefig(OUT_PATH, dpi=300, bbox_inches='tight', pad_inches=0.15)
plt.close()
print(f"Saved: {OUT_PATH}")
print(f"Size: {OUT_PATH.stat().st_size:,} bytes")

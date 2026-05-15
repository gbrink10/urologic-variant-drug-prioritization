"""Build Supplementary Figure S1: KEGG pathway enrichment heatmap across cancer contexts."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from pathlib import Path

VAL = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")
OUT = VAL / "Manuscript_Figures_v2" / "Supplementary_Figure_S1_KEGG_heatmap.png"

# Pathway × cancer context heatmap based on findings reported in the manuscript
# OR values from §3.2/§3.3/§3.6 and the KEGG_ENRICHMENT.csv

pathways = [
    "Cell Cycle (hsa04110)",
    "p53 Signaling (hsa04115)",
    "Apoptosis/BCL2 (hsa04210)",
    "Homologous Recombination (hsa03440)",
    "PI3K-AKT (hsa04151)",
    "HIF-1 (hsa04066)",
    "VEGF (hsa04370)",
    "Epigenetic Regulation (custom)",
]

contexts = [
    "NEPC\n(MDVr CXCR7 KD;\nGSE199274)",
    "NEPC\n(PM154 decitabine;\nGSE216053)",
    "MIBC\n(panel-restricted;\nGSE130598)",
    "ccRCC\n(stage partition;\nGSE143630)",
    "HLRCC vs normal\n(GSE157256)",
]

# Odds ratios per pathway × context (NaN = not assessed / not applicable for that panel)
# Values from the manuscript text and KEGG_ENRICHMENT.csv
or_vals = np.array([
    # NEPC-MDVr  NEPC-dec  MIBC    ccRCC   HLRCC
    [ 2.86,      np.nan,   1.63,   np.nan, np.nan],  # Cell Cycle
    [ 2.28,      np.nan,   np.nan, np.nan, np.nan],  # p53
    [ 1.76,      np.nan,   np.nan, np.nan, np.nan],  # Apoptosis (NEPC; trend ns)
    [ 1.62,      np.nan,   1.62,   np.nan, np.nan],  # HR
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],  # PI3K-AKT (panel-restricted; not enriched)
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],  # HIF-1 (constitutive in ccRCC; not DE)
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],  # VEGF (constitutive)
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],  # Epigenetic (custom set; descriptive)
])

# p-values per pathway × context for marker overlay
p_vals = np.array([
    [ 0.0002,    np.nan,   0.028,  np.nan, np.nan],
    [ 0.021,     np.nan,   np.nan, np.nan, np.nan],
    [ 0.12,      np.nan,   np.nan, np.nan, np.nan],
    [ 0.16,      np.nan,   0.16,   np.nan, np.nan],
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],
    [ np.nan,    np.nan,   np.nan, np.nan, np.nan],
])

# Convert OR to log2(OR) for color mapping; nan stays nan
log2_or = np.log2(or_vals)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

cmap = LinearSegmentedColormap.from_list("orblues", ["#cccccc", "#a8d4e6", "#1f78b4", "#1b6c44"], N=256)
cmap.set_bad('#ffffff', alpha=1)

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
fig.subplots_adjust(left=0.30, right=0.92, top=0.85, bottom=0.18)

# Plot
masked = np.ma.masked_invalid(log2_or)
im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=2, aspect='auto')

# Cell overlays — OR value + significance marker
for i in range(or_vals.shape[0]):
    for j in range(or_vals.shape[1]):
        v = or_vals[i, j]
        p = p_vals[i, j]
        if np.isnan(v):
            ax.text(j, i, "—", ha='center', va='center', fontsize=8, color='#999')
        else:
            marker = ""
            if not np.isnan(p):
                if p < 0.001: marker = "***"
                elif p < 0.01: marker = "**"
                elif p < 0.05: marker = "*"
                elif p < 0.20: marker = "(trend)"
            text_color = 'white' if v > 2.0 else 'black'
            ax.text(j, i, f"OR={v:.2f}\n{marker}", ha='center', va='center',
                    fontsize=7.5, color=text_color)

# Axes
ax.set_xticks(range(len(contexts)))
ax.set_xticklabels(contexts, fontsize=8.5)
ax.set_yticks(range(len(pathways)))
ax.set_yticklabels(pathways, fontsize=9)
ax.set_xticks(np.arange(-0.5, len(contexts), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(pathways), 1), minor=True)
ax.grid(which='minor', color='white', linewidth=1.5)
ax.tick_params(which='minor', length=0)
ax.tick_params(axis='x', length=0)
ax.tick_params(axis='y', length=0)
ax.set_title("Supplementary Figure S1.  KEGG pathway enrichment across cancer-variant DE comparisons",
             fontsize=10.5, fontweight='bold', loc='left', pad=12)

# Colorbar
cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
cbar.set_label('log₂(OR)', fontsize=9)

# Caption / source note
fig.text(0.02, 0.025,
         "Cells show OR values for each KEGG pathway × DE-comparison combination. "
         "Significance markers: *p<0.05, **p<0.01, ***p<0.001, (trend) 0.05<p<0.20. "
         "Dashes denote pathways not assessed (panel-restricted in MIBC) or not differentially active "
         "(HIF/VEGF axis in ccRCC is constitutively expressed; signal is captured via expression "
         "ranking rather than DE testing). Background gene sets matched each dataset's profiling scope.",
         fontsize=7, color='#444', wrap=True)

plt.savefig(OUT, dpi=300, bbox_inches='tight', pad_inches=0.15)
plt.close()
print(f"Saved: {OUT}  ({OUT.stat().st_size:,} bytes)")

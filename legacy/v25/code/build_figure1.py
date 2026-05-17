"""Regenerate Figure 1 with cBioPortal-verified TCGA PanCancer Atlas 2018 alteration frequencies.

Three panels: A) BLCA n=411, B) KIRC n=512, C) PRAD n=494 with NEPC context overlay.
Output: 2780x1424 PNG (matches original dimensions) at 300 DPI.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# cBioPortal PanCancer Atlas 2018 — verified 2026-05-13 via REST API
# Combined alteration % = unique union of (non-silent mutation) U (CNA deep del/amp) U (SV/fusion)

BLCA = {
    "TP53 mutation":          49,
    "CDKN2A deep del":        32,
    "PIK3CA mutation":        22,
    "FGFR3 alteration":       19,
    "ATM mutation":           13,
    "ERCC2 mutation":          9,
    "ERBB2 amplification":     5,
}
BLCA_ACTIONABLE = {"FGFR3 alteration", "ERBB2 amplification", "PIK3CA mutation"}

KIRC = {
    "VHL alteration":         34,   # mut + CNA; >=50% with hypermethylation per TCGA-KIRC 2013
    "PBRM1 alteration":       31,
    "SETD2 alteration":       12,
    "BAP1 alteration":        10,
    "MTOR alteration":         6,
    "CDKN2A deep del":         3,
}
KIRC_ACTIONABLE = {"VHL alteration", "MTOR alteration"}

# Panel C: Primary PRAD vs treatment-emergent NEPC contrast
PRAD_PRIMARY = {
    "PTEN alteration":        21,
    "TP53 mutation":          12,
    "RB1 deep deletion":       9,
}
NEPC_OVERLAY = {
    "RB1 loss (NEPC)":        88,   # midpoint of 85-92% per refs 13, 14
    "TP53 alteration (NEPC)": 67,   # ~67% per Beltran 2016 / Aggarwal 2018
}

# ---- styling ----
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

DPI = 300
W_IN, H_IN = 2780 / DPI, 1424 / DPI  # = 9.267 x 4.747 in
fig, axes = plt.subplots(1, 3, figsize=(W_IN, H_IN), dpi=DPI,
                         gridspec_kw={"width_ratios": [1.0, 1.05, 1.4], "wspace": 1.05})
fig.subplots_adjust(left=0.085, right=0.985, top=0.90, bottom=0.13)

def horiz_bars(ax, data, actionable, color_default, color_actionable, title, max_x=55):
    labels = list(data.keys())
    values = list(data.values())
    y = np.arange(len(labels))[::-1]  # top-to-bottom = highest first
    colors = [color_actionable if l in actionable else color_default for l in labels]
    ax.barh(y, values, color=colors, edgecolor="black", linewidth=0.4, height=0.7)
    for yi, v in zip(y, values):
        ax.text(v + 0.7, yi, f"{v}%", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0, max_x)
    ax.set_xlabel("Altered samples (%)", fontsize=9)
    ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", pad=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", alpha=0.25, linestyle=":", linewidth=0.5)
    ax.set_axisbelow(True)

# Panel A: BLCA
horiz_bars(axes[0], BLCA, BLCA_ACTIONABLE,
           color_default="#7BAFD4", color_actionable="#D95F02",
           title="A   BLCA  (n = 411)", max_x=55)

# Panel B: KIRC — annotate VHL hypermethylation extension
horiz_bars(axes[1], KIRC, KIRC_ACTIONABLE,
           color_default="#9CB89A", color_actionable="#1B7837",
           title="B   KIRC  (n = 512)", max_x=60)
# Add hypermethylation indicator on VHL bar (top bar)
ax = axes[1]
vhl_pos = len(KIRC) - 1  # top bar y-index after reversal
# Find y for VHL alteration
labels_kirc = list(KIRC.keys())
vhl_y = np.arange(len(labels_kirc))[::-1][labels_kirc.index("VHL alteration")]
ax.barh([vhl_y], [52 - 34], left=34, color="#1B7837",
        alpha=0.35, edgecolor="black", linewidth=0.4, height=0.7,
        hatch="///")
ax.text(52 - 0.5, vhl_y - 0.42, "52% w/ methylation",
        va="top", ha="right", fontsize=7, fontstyle="italic", color="#1B7837")

# Panel C: PRAD primary vs NEPC contrast
ax = axes[2]
all_labels = list(PRAD_PRIMARY.keys()) + list(NEPC_OVERLAY.keys())
all_values = list(PRAD_PRIMARY.values()) + list(NEPC_OVERLAY.values())
group     = ["primary"]*len(PRAD_PRIMARY) + ["NEPC"]*len(NEPC_OVERLAY)
y = np.arange(len(all_labels))[::-1]
colors = ["#C497B2" if g == "primary" else "#8A0F47" for g in group]
ax.barh(y, all_values, color=colors, edgecolor="black", linewidth=0.4, height=0.7)
for yi, v in zip(y, all_values):
    ax.text(v + 1.0, yi, f"{v}%", va="center", fontsize=8.5)
ax.set_yticks(y)
ax.set_yticklabels(all_labels, fontsize=8.5)
ax.set_xlim(0, 105)
ax.set_xlabel("Altered samples (%)", fontsize=9)
ax.set_title("C   PRAD primary (n = 494) vs treatment-emergent NEPC",
             fontsize=10.5, fontweight="bold", loc="left", pad=8)
ax.grid(axis="x", alpha=0.25, linestyle=":", linewidth=0.5)
ax.set_axisbelow(True)

# Legend for panel C
ax.legend(
    handles=[
        mpatches.Patch(color="#C497B2", label="Primary PRAD (TCGA n=494)"),
        mpatches.Patch(color="#8A0F47", label="Treatment-emergent NEPC (published)"),
    ],
    loc="upper center", fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, -0.16),
    ncol=1,
)

# Source line
fig.text(0.005, 0.005,
         "Data source: cBioPortal PanCancer Atlas 2018 (BLCA, KIRC, PRAD; queried 2026-05-13). "
         "NEPC RB1/TP53 frequencies: Beltran et al. 2016; Aggarwal et al. 2018.",
         fontsize=6.5, fontstyle="italic", color="gray")

OUT = r"C:\Users\garre\figure1_TCGAfixed.png"
# Use bbox_inches='tight' to ensure all labels fit; then resize back to exact 2780x1424
plt.savefig(OUT, dpi=DPI, bbox_inches="tight", pad_inches=0.10, format="png")
# Resize to exact target dimensions for in-place swap
from PIL import Image as _Img
_img = _Img.open(OUT)
_img = _img.resize((2780, 1424), _Img.LANCZOS)
_img.save(OUT)
print(f"Saved: {OUT}")

# Verify dimensions
from PIL import Image
img = Image.open(OUT)
print(f"Generated size: {img.size}")
print(f"Target size:    (2780, 1424)")

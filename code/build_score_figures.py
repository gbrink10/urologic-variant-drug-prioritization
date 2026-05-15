"""Build three drug-evidence-score figure panels for v13:
  - figure2E_NEPC_drug_scores.png
  - figure3E_MIBC_drug_scores.png
  - figure4E_sRCC_drug_scores.png

Stacked horizontal bar charts: each bar = one drug-cancer association;
segments = 5 evidence components (TCGA, GEO, KEGG, External lit, Phase III).
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

VAL = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")
OUT = VAL / "Manuscript_Figures_v2"
OUT.mkdir(exist_ok=True)

# Load scores from CSV
scores = []
with open(VAL / "DRUG_EVIDENCE_SCORES_v12.csv", encoding='utf-8') as f:
    for row in csv.DictReader(f):
        scores.append(row)

# Color palette for components (colorblind-safe sequential)
COMP_COLORS = {
    'TCGA':    '#1B7837',  # green
    'GEO':     '#7BAFD4',  # blue
    'KEGG':    '#D95F02',  # orange
    'External':'#9CB89A',  # light green
    'PhIII':   '#8A0F47',  # dark red
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

def build_panel(cancer_filter, title, out_path, w_in=7.2, h_per_row=0.55):
    rows = [r for r in scores if cancer_filter(r['cancer'])]
    n = len(rows)
    h_in = max(3.0, h_per_row * n + 1.8)
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=300)
    fig.subplots_adjust(left=0.30, right=0.96, top=0.88, bottom=0.22)

    # Drop "(NEW)" suffix from drug names — olaparib is now Table 1 row 6
    labels = [r['drug'].replace(' (NEW)', '') for r in rows]
    components = [
        ('TCGA',     'tcga_score',    3),
        ('GEO',      'geo_score',     3),
        ('KEGG',     'kegg_score',    2),
        ('External', 'ext_score',     1),
        ('PhIII',    'phase3_score',  1),
    ]
    y = np.arange(n)[::-1]
    left = np.zeros(n)
    for comp_name, key, _max in components:
        vals = [int(r[key]) for r in rows]
        bars = ax.barh(y, vals, left=left, color=COMP_COLORS[comp_name],
                       edgecolor='black', linewidth=0.4, height=0.7, label=comp_name)
        left = left + np.array(vals)

    # Total score label at end of each bar
    for yi, r in zip(y, rows):
        total = int(r['total'])
        tier = r['tier']
        ax.text(total + 0.18, yi, f"{total}/10  ({tier})",
                va='center', fontsize=8.5, fontweight='bold')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 11.5)
    ax.set_xlabel("Composite evidence score (0–10)", fontsize=9)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_title(title, fontsize=10.5, fontweight='bold', loc='left', pad=10)
    ax.grid(axis='x', alpha=0.25, linestyle=':', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend — below x-axis label with clear separation
    handles = [mpatches.Patch(color=COMP_COLORS[name], label=f"{name} (0–{mx})")
               for name, _, mx in components]
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.22),
              ncol=5, fontsize=7.5, frameon=False)

    # Source line
    fig.text(0.02, 0.005,
             f"Source: DRUG_EVIDENCE_SCORES_v12.csv. Composite = TCGA (0–3) + GEO (0–3) "
             "+ KEGG (0–2) + External lit (0–1) + Phase III (0–1).",
             fontsize=6.5, fontstyle='italic', color='gray')
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"  Wrote: {out_path}  ({out_path.stat().st_size:,} bytes)")
    return out_path

# Figure 2E — NEPC drug scores
build_panel(
    cancer_filter=lambda c: c == 'NEPC',
    title="Figure 2E.  NEPC — Drug Evidence Scores",
    out_path=OUT / "figure2E_NEPC_drug_scores.png",
)

# Figure 3E — MIBC drug scores
build_panel(
    cancer_filter=lambda c: c == 'MIBC',
    title="Figure 3E.  MIBC (MPBC-applicable) — Drug Evidence Scores",
    out_path=OUT / "figure3E_MIBC_drug_scores.png",
)

# Figure 4E — ccRCC/sRCC drug scores
build_panel(
    cancer_filter=lambda c: 'ccRCC' in c,
    title="Figure 4E.  ccRCC/sRCC — Drug Evidence Scores",
    out_path=OUT / "figure4E_sRCC_drug_scores.png",
)

print("\nAll three score-panel figures generated.")

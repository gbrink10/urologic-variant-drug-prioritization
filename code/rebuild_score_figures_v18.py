"""Rebuild Figure 2E/3E/4E using 9-point molecular score (Phase III separated as flag)."""
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

VAL = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")
OUT = VAL / "Manuscript_Figures_v2"

scores = []
with open(VAL / "DRUG_EVIDENCE_SCORES_v18.csv", encoding='utf-8') as f:
    for row in csv.DictReader(f):
        scores.append(row)

COMP_COLORS = {
    'TCGA':    '#1B7837',
    'GEO':     '#7BAFD4',
    'KEGG':    '#D95F02',
    'External':'#9CB89A',
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

def build_panel(cancer_filter, title, out_path, w_in=7.4, h_per_row=0.6):
    rows = [r for r in scores if cancer_filter(r['cancer'])]
    n = len(rows)
    h_in = max(3.2, h_per_row * n + 1.8)
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=300)
    fig.subplots_adjust(left=0.27, right=0.96, top=0.88, bottom=0.22)

    labels = [r['drug'] for r in rows]
    components = [
        ('TCGA',     'tcga_score',    3),
        ('GEO',      'geo_score',     3),
        ('KEGG',     'kegg_score',    2),
        ('External', 'ext_score',     1),
    ]
    y = np.arange(n)[::-1]
    left = np.zeros(n)
    for comp_name, key, _ in components:
        vals = [int(r[key]) for r in rows]
        ax.barh(y, vals, left=left, color=COMP_COLORS[comp_name],
                edgecolor='black', linewidth=0.4, height=0.7, label=comp_name)
        left = left + np.array(vals)

    # Total score + tier label + Phase III concordance marker
    for yi, r in zip(y, rows):
        score = int(r['score'])
        tier = r['tier']
        ph3 = bool(r['phase3_concordance'])
        ph3_mark = "  ◆ Ph III" if ph3 else ""
        ax.text(score + 0.18, yi, f"{score}/9  ({tier}){ph3_mark}",
                va='center', fontsize=8.5, fontweight='bold',
                color='#8A0F47' if ph3 else 'black')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 12)
    ax.set_xlabel("Molecular prioritization score (0–9)", fontsize=9)
    ax.set_xticks([0, 2, 4, 6, 8])
    ax.set_title(title, fontsize=10.5, fontweight='bold', loc='left', pad=10)
    ax.grid(axis='x', alpha=0.25, linestyle=':', linewidth=0.5)
    ax.set_axisbelow(True)

    handles = [mpatches.Patch(color=COMP_COLORS[name], label=f"{name} (0–{mx})")
               for name, _, mx in components]
    handles.append(mpatches.Patch(color='none', label='  ◆ Phase III concordance'))
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.22),
              ncol=5, fontsize=7.5, frameon=False)

    fig.text(0.02, 0.005,
             "Score = TCGA (0–3) + GEO (0–3) + KEGG (0–2) + External lit (0–1). "
             "Phase III source-disease concordance reported separately (◆).",
             fontsize=6.5, fontstyle='italic', color='gray')
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"  Wrote: {out_path.name}")

build_panel(lambda c: c == 'NEPC', "Figure 2E.  NEPC — Molecular Prioritization Scores",
            OUT / "figure2E_NEPC_drug_scores.png")
build_panel(lambda c: c == 'MIBC', "Figure 3E.  MIBC (MPBC-applicable) — Molecular Prioritization Scores",
            OUT / "figure3E_MIBC_drug_scores.png")
build_panel(lambda c: 'ccRCC' in c, "Figure 4E.  ccRCC/sRCC — Molecular Prioritization Scores",
            OUT / "figure4E_sRCC_drug_scores.png")
print("Done")

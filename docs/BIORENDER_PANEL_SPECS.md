# BioRender rebuild specs for the three mechanism schematics

The mechanism panels in Figures 2C, 3C and Supplementary Figure S1C are
AI-generated images. ASCO's policy covers AI-generated *text* and research use
but is silent on AI-generated *images*, and AACR prohibited them outright as
recently as 2024. Rebuilding them in BioRender removes that exposure, because
the output is assembled from a curated scientific icon library rather than
produced by a general image model.

Each spec below works two ways: paste the prompt block into BioRender's
**Generate Custom Figure**, or use the element list to assemble the panel by
hand from the icon library. Assembling by hand is the stronger option for this
manuscript — see *Provenance* at the end.

---

## Before you start

**Licensing.** A paid individual or institutional subscription with publication
rights is required to publish a BioRender figure in a journal. Free-tier
exports are licensed CC BY-NC-ND and carry a watermark; using them in a
peer-reviewed manuscript violates BioRender's terms and most journals will not
accept the license. Check whether Tulane holds an institutional license before
buying an individual one.

**Attribution.** Published figures must carry "Created with BioRender.com" in
the caption or acknowledgments. Add it to each of the three legends.

**Canvas.** Match what the current panels occupy so the composite figures do
not need relayout:

| Panel | Role in its figure | Aspect | Export |
|---|---|---|---|
| Figure 2C | rightmost of three, widest | ~1.45 : 1.0 landscape | PNG 300 dpi + editable source |
| Figure 3C | rightmost of three, widest | ~1.5 : 1.0 landscape | PNG 300 dpi + editable source |
| Supplementary Figure S1C | rightmost of three | ~1.0 : 1.0 | PNG 300 dpi + editable source |

Export at 300 dpi minimum, and keep the editable `.bioR` source in the Zenodo
deposit alongside the figure-generation code.

---

## Figure 2C — renal medullary carcinoma, CXCR1/CXCR2 blockade

### Prompt

> A cross-sectional schematic of a tumor microenvironment. On the left, a
> single SMARCB1-deficient renal medullary carcinoma tumor cell secreting four
> labelled chemokine ligands: CXCL8, CXCL1, CXCL2 and CXCL3, drawn as small
> coloured dots leaving the cell surface. On the right, a neutrophil with a
> multi-lobed nucleus displaying two labelled G-protein-coupled receptors in
> its plasma membrane: CXCR1 and CXCR2. Draw an arrow from CXCL8 to both CXCR1
> and CXCR2. Draw arrows from CXCL1, CXCL2 and CXCL3 to CXCR2 only. Label the
> space between the two cells "myeloid recruitment". Below the neutrophil,
> show a small-molecule antagonist blocking both receptors with inhibition bars
> (blunt-ended lines, not arrows).

### Elements to search in the icon library

- `renal cell carcinoma cell` or generic `cancer cell` — label *RMC tumor cell,
  SMARCB1-deficient*
- `neutrophil` (multi-lobed nucleus)
- `GPCR` or `7-transmembrane receptor` ×2, in the neutrophil membrane
- `cytokine` / `chemokine` dot clusters ×4, one colour per ligand
- `inhibitor` blunt-end connector ×2

### Labels, verbatim

- Tumor cell: **RMC tumor cell** / *SMARCB1 loss*
- Ligands: **CXCL8**, **CXCL1**, **CXCL2**, **CXCL3**
- Receptors: **CXCR1**, **CXCR2**
- Neutrophil: **Neutrophil**
- Process arrow: *myeloid recruitment*
- Drug box: **CXCR2-directed antagonists, including agents with additional
  CXCR1 activity: AZD5069, navarixin, reparixin, danirixin**
- Footnote inside the panel: *CXCL8 binds both receptors; CXCL1/2/3 are
  CXCR2-selective.*

### Accuracy points that must survive the rebuild

1. **The receptors sit on the neutrophil, not on the tumor cell.** This is the
   whole reason the dependency and compound screens cannot test this candidate,
   which the Results state explicitly. If BioRender's draft puts CXCR1/CXCR2 on
   the tumor cell, that is a substantive error, not a cosmetic one.
2. **CXCL8 → both receptors. CXCL1, CXCL2, CXCL3 → CXCR2 only.** Do not
   simplify to four arrows into one receptor.
3. Inhibition is drawn with blunt-ended bars, never arrowheads.
4. Neither receptor was measured in the source series. The panel is a *proposed*
   mechanism and the legend already says so — keep the word "Proposed" in the
   panel title.

---

## Figure 3C — small-cell bladder cancer, three lineage subtypes

### Prompt

> Three tumor cells side by side, each labelled with a lineage transcription
> factor. Left cell, labelled ASCL1+: a membrane antigen CEACAM5 bound by an
> antibody-drug conjugate, with an arrow showing internalisation into an
> endosome and payload release inside the cell. Middle cell, labelled NEUROD1+:
> a seven-transmembrane receptor SSTR2 in the membrane bound by a
> radiolabelled peptide, lutetium-177 DOTATATE, drawn with a radioactivity
> symbol. Right cell, labelled POU2F3+: inside the cytoplasm, an enzyme
> PTGS1/COX-1 on the endoplasmic reticulum converting arachidonic acid to
> prostaglandins, with aspirin shown inhibiting it. Keep the three cells
> visually distinct by colour.

### Elements to search in the icon library

- `cancer cell` ×3, three distinct fills
- `antibody-drug conjugate` or `monoclonal antibody` + `payload`
- `endosome` / `receptor-mediated endocytosis` arrow
- `GPCR` for SSTR2, plus `radioactive` symbol
- `endoplasmic reticulum`, `enzyme` for COX-1
- `inhibitor` blunt-end connector

### Labels, verbatim

- Cells: **ASCL1+**, **NEUROD1+**, **POU2F3+**
- Left: **CEACAM5**, *ADC binding and internalization*
- Middle: **SSTR2**, **lutetium-177 DOTATATE**
- Right: **PTGS1 / COX-1**, *arachidonic acid*, *prostaglandins*, **aspirin
  (non-selective COX inhibitor)**
- Red banner beneath the middle cell: **NEUROD1 branch not supported by this
  cohort (q = 0.363)**
- Caption line under the panel: *POU2F3 panel: COX-1 perturbation axis —
  therapeutic direction unresolved; aspirin shown as an available non-selective
  inhibitor.*

### Accuracy points that must survive the rebuild

1. **The NEUROD1/SSTR2 branch is negative.** The red banner is load-bearing —
   the Results say this association is not supported (q = 0.363). Do not let a
   generated draft drop it or soften it.
2. **Aspirin, not celecoxib** (see the note below). Celecoxib is COX-2
   selective and spares COX-1 at therapeutic doses, so it must not be drawn
   inhibiting PTGS1.
3. The COX-1 arrow direction is deliberately unresolved: the paper says the
   therapeutic direction requires functional testing, because prostaglandin
   signaling has been reported to *restrain* tumorigenesis in tuft cells. Do not
   draw COX-1 as unambiguously pro-tumor.
4. Use US spelling — the current AI panel says "internalisation".

---

## Supplementary Figure S1C — sarcomatoid urothelial carcinoma

### Prompt

> A single tumor cell cross-section labelled "sarcomatoid urothelial carcinoma
> cell", with nucleus and cytoplasm both visible. In the nucleus: a histone
> methyltransferase NSD2 acting on histone tails marked H3K36me2; a chromatin
> reader UHRF1 on a nucleosome; and ATR with ATRIP at a replication fork
> showing replication stress and DNA damage. In the cytoplasm: G6PD converting
> glucose-6-phosphate to ribose-5-phosphate with NADPH produced, labelled
> pentose phosphate pathway. On the plasma membrane at the right edge, show
> TROP2 (TACSTD2) as sparse and faded to indicate reduced expression. Draw four
> labelled drug boxes on the left, each connected to its target with an
> inhibition bar.

### Labels, verbatim

- Cell: **Sarcomatoid urothelial carcinoma cell**; compartments **NUCLEUS**,
  **CYTOPLASM**
- Targets: **NSD2** *(histone methyltransferase)*, **H3K36me2**, **UHRF1**
  *(chromatin reader)*, **ATR** + **ATRIP**, **G6PD**, **TROP2 (TACSTD2)**
- Metabolites: *Glucose-6-phosphate*, *Ribose-5-phosphate*, *NADPH*, *Pentose
  phosphate pathway*
- Drug boxes: **KTX-1001** → NSD2; **UM-002 PROTAC** → UHRF1; **ceralasertib /
  berzosertib / elimusertib** → ATR; **6-aminonicotinamide / polydatin** → G6PD
- TROP2 side note: *Descriptive TROP2-low signal; may indicate reduced target
  availability. Predictive value unestablished.*
- Red banner: **Descriptive only: histology is confounded with array chip**

### Accuracy points that must survive the rebuild

1. **The banner must say "confounded", not "aliased".** "Aliased" was purged
   from the manuscript as coined shorthand and survives only inside this
   AI-generated image.
2. TROP2 is a **loss** marker here — drawn sparse and faded, never as an
   abundant target with a drug pointed at it.
3. ATR is drawn at a replication fork, not as a membrane or cytoplasmic target.

---

## Provenance, and what to change in the manuscript

BioRender's **Generate Custom Figure** is itself an AI tool. It draws on a
curated, scientifically reviewed icon library rather than a general image
model, which is a real improvement in provenance — but if you use it, the
figures are still AI-drafted and the disclosure should say so.

The cleanest position, and the one that closes the question entirely:

- Use BioRender AI to get a first draft if it saves time, then **rebuild the
  final panel from library icons** so every element is one you placed.
- Verify each of the accuracy points listed above against the panel you export.

Then update the AI Usage Disclosure. It currently reads:

> ...and generating the mechanism schematics shown as panel C of Figures 2 and
> 3 and of Supplementary Figure S1.

If the panels are rebuilt from the icon library, that clause should be removed
and replaced with a line stating the schematics were assembled in BioRender
from its icon library, plus "Created with BioRender.com" in each legend. If you
keep an AI-drafted layout, say that instead — drafted with BioRender AI and
checked element by element by the authors.

ASCO's AI policy asks for tool, version, date accessed and manufacturer.
The current disclosure names the tools and makers only, so add version and
access date for whichever tools remain disclosed.

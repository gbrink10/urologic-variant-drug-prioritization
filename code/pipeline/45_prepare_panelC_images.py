"""Stage the mechanism schematics used as Panel C, with corrections applied.

The three panels were generated from prompts written against the deposited
scoring data, then checked molecule by molecule against the analysis. One defect
was found and is corrected here rather than left in the figure:

  sarcomatoid panel  the right-hand "NUCLEUS" leader line points into the
                     cytoplasm. The compartments are already labelled in place
                     inside the diagram, so the three redundant leader labels
                     are removed rather than re-lettered.

Everything else was verified as drawn: CXCR1/CXCR2 on the neutrophil rather
than the tumour cell; NSD2, UHRF1 and ATR-ATRIP nuclear with H3K36me2 as the
NSD2 mark; G6PD cytoplasmic; TROP2 sparse at the membrane; PTGS1/COX-1 on the
endoplasmic reticulum and inhibited by aspirin, not by the COX-2-selective
celecoxib.

Writes: figures/panelC/<name>.png
"""
import shutil
import sys
from pathlib import Path

import paths

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
SRC = paths.OUTPUT
OUT = paths.PANEL_C
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    'RMC': 'ChatGPT Image Aug 30, 2026, 06_24_33 PM.png',
    'SarcUC': 'ChatGPT Image Aug 30, 2026, 06_28_51 PM.png',
    'SCBC': 'ChatGPT Image Aug 30, 2026, 06_30_09 PM.png',
}

for key, name in SOURCES.items():
    src = SRC / name
    if not src.exists():
        print(f"  MISSING {name}")
        continue
    im = Image.open(src).convert('RGB')
    w, h = im.size

    if key == 'SarcUC':
        # Remove the three redundant compartment leader labels on the right, one
        # of which ("NUCLEUS") points at the cytoplasm rather than the nucleus.
        # The cell body is found as the largest connected non-white component,
        # and only material lying outside it in the lower-right quadrant is
        # blanked, so neither the cell nor the pathway labels inside it are
        # touched.
        import numpy as np
        from scipy import ndimage

        a = np.array(im).astype(int)
        ink = a.sum(axis=2) < 735
        filled = ndimage.binary_fill_holes(
            ndimage.binary_closing(ink, structure=np.ones((5, 5))))
        lab, n = ndimage.label(filled)
        if n:
            sizes = ndimage.sum(filled, lab, range(1, n + 1))
            cell = (lab == (int(np.argmax(sizes)) + 1))
            cell = ndimage.binary_dilation(cell, iterations=3)
            y0, y1 = int(h * 0.60), int(h * 0.90)
            x0 = int(w * 0.70)
            target = np.zeros_like(cell)
            target[y0:y1, x0:] = True
            blank = target & ~cell
            a[blank] = 255
            im = Image.fromarray(a.astype('uint8'))
            print(f"  {key}: blanked {int(blank.sum()):,} px outside the cell "
                  f"in the lower-right quadrant")
            # the leader stubs touch the membrane, so they survive the
            # connected-component test; the cell never extends beyond x=1199 in
            # this quadrant, so clear the remainder of each stub line
            a2 = np.array(im).astype(int)
            a2[int(h * 0.60):int(h * 0.87), 1205:] = 255
            im = Image.fromarray(a2.astype('uint8'))

    dest = OUT / f'PanelC_{key}.png'
    im.save(dest)
    print(f"  saved {dest.name}  {im.size}  ({dest.stat().st_size:,} bytes)")

# keep the provenance of the originals alongside the corrected versions
raw = OUT / 'originals'
raw.mkdir(exist_ok=True)
for key, name in SOURCES.items():
    if (SRC / name).exists():
        shutil.copy2(SRC / name, raw / f'original_{key}.png')
print(f"  originals copied to {raw}")

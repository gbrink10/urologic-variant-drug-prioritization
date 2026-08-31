"""Stage the mechanism schematics used as Panel C, with corrections applied.

The three panels were generated from prompts written against the deposited
scoring data, then checked molecule by molecule against the analysis. One defect
was found and is corrected here rather than left in the figure:

  sarcomatoid panel  (a) the right-hand "NUCLEUS" leader line points into the
                     cytoplasm. The compartments are already labelled in place
                     inside the diagram, so the three redundant leader labels
                     are removed rather than re-lettered.
                     (b) the TROP2 annotation read "loss predicts non-response
                     to sacituzumab govitecan". No treated patients were
                     analysed anywhere in this work, so that is a predictive
                     claim the data cannot carry. It is replaced in place with
                     a descriptive statement.

Everything else was verified as drawn: CXCR1/CXCR2 on the neutrophil rather
than the tumour cell; NSD2, UHRF1 and ATR-ATRIP nuclear with H3K36me2 as the
NSD2 mark; G6PD cytoplasmic; TROP2 sparse at the membrane; PTGS1/COX-1 on the
endoplasmic reticulum and inhibited by aspirin, not by the COX-2-selective
celecoxib.

Writes: figures/panelC/<name>.png
"""
import os
import shutil
import sys
from pathlib import Path

import paths

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
# generated schematics are dropped here by the author before staging;
# override with UVDP_SCHEMATIC_SRC if they live elsewhere
SRC = Path(os.environ.get('UVDP_SCHEMATIC_SRC',
                          Path.home() / 'Downloads'))
OUT = paths.PANEL_C
OUT.mkdir(parents=True, exist_ok=True)

def _retext_trop2(im):
    """Blank the predictive TROP2 annotation and write a descriptive one.

    The generated panel states that TROP2 loss "predicts non-response to
    sacituzumab govitecan". No treated patients were analysed in this work, so
    the panel is edited to say what the data actually support. The block is
    located by its own ink rather than by hard-coded pixels: it is the text
    lying to the right of the cell, below the TROP2/(TACSTD2) label and above
    the arrowhead.
    """
    import numpy as np
    from PIL import ImageFont

    a = np.array(im)
    h, w = a.shape[:2]
    x0, x1 = int(w * 0.845), w
    y0, y1 = int(h * 0.255), int(h * 0.435)
    a[y0:y1, x0:x1] = 255
    im = Image.fromarray(a)

    text = ('Descriptive TROP2-low signal; may indicate reduced target '
            'availability. Predictive value unestablished.')
    avail = (w - x0) - int(w * 0.018)
    font = size = None
    for pt in range(int(h * 0.028), 11, -1):
        for cand in ('arial.ttf', 'DejaVuSans.ttf', 'segoeui.ttf'):
            try:
                font = ImageFont.truetype(cand, pt)
                break
            except OSError:
                font = None
        if font is None:
            font = ImageFont.load_default()
        # greedy wrap, then keep the largest size whose block still fits
        lines, cur = [], ''
        for word in text.split():
            trial = (cur + ' ' + word).strip()
            if font.getlength(trial) <= avail:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        size = pt
        if (max(font.getlength(ln) for ln in lines) <= avail
                and len(lines) * pt * 1.30 <= (y1 - y0) - int(h * 0.02)):
            break

    d = ImageDraw.Draw(im)
    y = y0 + int(h * 0.012)
    for ln in lines:
        d.text((x0 + int(w * 0.008), y), ln, fill=(60, 60, 60), font=font)
        y += int(size * 1.30)
    return im


SOURCES = {
    # regenerated 31 Aug after the ligand-receptor mapping was corrected:
    # CXCL8 binds both receptors, CXCL1/2/3 are CXCR2-selective
    'RMC': 'ChatGPT Image Aug 31, 2026, 06_18_41 AM.png',
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

        # replace the predictive TROP2 annotation with a descriptive one
        im = _retext_trop2(im)

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

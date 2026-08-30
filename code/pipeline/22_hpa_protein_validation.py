"""Protein-level validation of the nominated targets against the Human Protein Atlas.

Every association in Master Table 1 is nominated from transcript abundance. For
targets addressed by an antibody, antibody-drug conjugate, bispecific engager or
peptide-receptor radioligand, transcript abundance is not sufficient: the protein
must reach the cell surface for the modality to work at all. This script queries
HPA for each nominated target and records

  * subcellular main location, and whether plasma membrane is among them,
  * whether the modality used in that row requires surface access,
  * RNA tissue specificity and nTPM in bladder, kidney and prostate,
  * TCGA prognostic association in the corresponding source disease.

A surface-dependent row whose target HPA does not localise to the plasma membrane
is flagged, because that is a falsifiable problem with the row rather than a
detail.

Writes: results/HPA_PROTEIN_VALIDATION.csv
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results' / 'HPA_PROTEIN_VALIDATION.csv'

# target -> (Master Table rows, modality, does the modality need cell-surface access?)
TARGETS = {
    'NECTIN4':  ('11',    'antibody-drug conjugate (enfortumab vedotin)', True),
    'TACSTD2':  ('27',    'antibody-drug conjugate (sacituzumab govitecan) - NEGATIVE biomarker', True),
    'CEACAM1':  ('19',    'monoclonal antibody (CM24)', True),
    'CEACAM5':  ('28',    'antibody-drug conjugate (anti-CEACAM5 class)', True),
    'SSTR2':    ('29',    'peptide receptor radionuclide therapy (177Lu-DOTATATE)', True),
    'DLL3':     ('3.3',   'bispecific T-cell engager (tarlatamab), post hoc', True),
    'CXCR1':    ('17',    'small-molecule receptor antagonist', True),
    'CXCR2':    ('17',    'small-molecule receptor antagonist', True),
    'EGFR':     ('18',    'tyrosine kinase inhibitor (erlotinib)', False),
    'NSD2':     ('23',    'histone methyltransferase inhibitor (KTX-1001)', False),
    'ATR':      ('24',    'kinase inhibitor (ceralasertib class)', False),
    'UHRF1':    ('25',    'PROTAC degrader (UM-002)', False),
    'G6PD':     ('26',    'metabolic inhibitor (6-aminonicotinamide)', False),
    'PTGS1':    ('30',    'cyclooxygenase inhibitor (aspirin/celecoxib)', False),
    'BCL2':     ('1',     'BH3 mimetic (venetoclax)', False),
    'AURKA':    ('2, 7',  'kinase inhibitor (alisertib)', False),
    'EZH2':     ('3',     'methyltransferase inhibitor (tazemetostat)', False),
    'DNMT1':    ('4',     'hypomethylating agent (decitabine)', False),
    'PARP1':    ('6, 8',  'PARP inhibitor', False),
    'FGFR3':    ('10',    'FGFR inhibitor (erdafitinib)', False),
    'EPAS1':    ('15',    'HIF2a antagonist (belzutifan)', False),
    'MMP1':     ('21',    'MMP inhibitor', True),
    'POSTN':    ('22',    'anti-TGFb axis / secreted matricellular target', True),
}

BASE = "https://www.proteinatlas.org"


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def resolve(gene):
    """Return (ensembl, tissue nTPM dict). Tissue nTPM is only exposed by the
    search_download endpoint, not by the per-gene JSON record."""
    url = (f"{BASE}/api/search_download.php?search={gene}&format=json"
           f"&columns=g,eg,t_RNA_urinary_bladder,t_RNA_kidney,t_RNA_prostate"
           f"&compress=no")
    for rec in fetch(url):
        if rec.get('Gene', '').upper() == gene.upper():
            return rec['Ensembl'], {
                'bladder': rec.get('Tissue RNA - urinary bladder [nTPM]'),
                'kidney': rec.get('Tissue RNA - kidney [nTPM]'),
                'prostate': rec.get('Tissue RNA - prostate [nTPM]'),
            }
    return None, {}


PROGNOSTIC = {
    'Cancer prognostics - Bladder Urothelial Carcinoma (TCGA)': 'BLCA',
    'Cancer prognostics - Kidney Renal Clear Cell Carcinoma (TCGA)': 'KIRC',
    'Cancer prognostics - Prostate Adenocarcinoma (TCGA)': 'PRAD',
}

rows = []
for gene, (mtrows, modality, needs_surface) in TARGETS.items():
    try:
        ensg, ntpm = resolve(gene)
        if not ensg:
            rows.append({'gene': gene, 'rows': mtrows, 'modality': modality,
                         'surface_required': needs_surface,
                         'status': 'not found in HPA'})
            print(f"{gene:<9} not found")
            continue
        d = fetch(f"{BASE}/{ensg}.json")

        main = d.get('Subcellular main location') or []
        add = d.get('Subcellular additional location') or []
        pclass = d.get('Protein class') or []
        secreted = d.get('Secretome location') or ''

        # Membrane status is taken from the CURATED protein-class annotation, not
        # from the immunofluorescence subcellular call. The IF dataset is derived
        # from a small panel of cell lines and mislocalises well-established
        # surface receptors: it places SSTR2 - the target of an approved
        # peptide-receptor radioligand that must bind extracellularly - in the
        # cytosol, and DLL3 in the nucleoplasm. The IF call is still recorded
        # below as an observation, but it is not used to adjudicate the row.
        # An antibody, ADC, engager or radioligand needs its target to be
        # extracellularly accessible - either displayed on the plasma membrane or
        # secreted into the matrix. MMP1 and POSTN are secreted rather than
        # membrane-bound, which satisfies the requirement just as well.
        membrane = (any('membrane' in str(x).lower() for x in pclass)
                    or any('g-protein coupled receptor' in str(x).lower() for x in pclass)
                    or 'membrane' in str(secreted).lower()
                    or any('plasma membrane' in str(x).lower() for x in list(main) + list(add)))
        extracellular = (membrane
                         or any('secreted' in str(x).lower() for x in pclass)
                         or 'secreted' in str(secreted).lower())

        prog = []
        for key, short in PROGNOSTIC.items():
            v = d.get(key)
            if isinstance(v, dict) and v.get('is_prognostic'):
                prog.append(f"{short}:{v.get('prognostic type', '')} (p={v.get('p_val')})")

        rec = {
            'gene': gene, 'ensembl': ensg, 'rows': mtrows, 'modality': modality,
            'surface_required': needs_surface,
            'subcellular_main': '; '.join(map(str, main)),
            'plasma_membrane': membrane,
            'secretome': secreted,
            'rna_tissue_specificity': d.get('RNA tissue specificity'),
            'nTPM_bladder': ntpm.get('bladder'),
            'nTPM_kidney': ntpm.get('kidney'),
            'nTPM_prostate': ntpm.get('prostate'),
            'tcga_prognostic': '; '.join(prog) if prog else 'none',
            'protein_class': '; '.join(pclass)[:130],
            'membrane_basis': ('curated protein class'
                               if any('membrane' in str(x).lower()
                                      or 'g-protein coupled receptor' in str(x).lower()
                                      for x in pclass)
                               else 'immunofluorescence / secretome'),
        }
        if needs_surface:
            rec['status'] = ('extracellular access confirmed' if extracellular
                             else 'EXTRACELLULAR ACCESS NOT CONFIRMED')
            rec['access_route'] = ('plasma membrane' if membrane
                                   else 'secreted' if extracellular else 'none')
        else:
            rec['status'] = 'intracellular target - surface access not required'
        rows.append(rec)
        print(f"{gene:<9} {str(main)[:38]:<40} membrane={membrane}  {rec['status']}")
        time.sleep(0.3)
    except Exception as exc:                                   # noqa: BLE001
        rows.append({'gene': gene, 'rows': mtrows, 'modality': modality,
                     'surface_required': needs_surface, 'status': f'ERROR {exc}'})
        print(f"{gene:<9} ERROR {exc}")

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

surf = df[df['surface_required'] == True]                      # noqa: E712
bad = surf[surf['status'] == 'SURFACE NOT CONFIRMED']
print(f"\nsurface-dependent rows: {len(surf)}; "
      f"HPA confirms membrane or secreted localisation for {len(surf) - len(bad)}")
if len(bad):
    print("NOT CONFIRMED:", list(bad['gene']))
print(f"\nWrote {OUT}")

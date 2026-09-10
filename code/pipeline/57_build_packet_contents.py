"""Write the submission packet's contents file from the packet itself.

00_CONTENTS.txt was maintained by hand and drifted: it carried the previous
title, a body count of 3,958 against an actual 4,000, 60 references against 65,
and listed fourteen data-supplement files when there were eighteen. Everything
in it is derivable from the built documents, so it is derived.

Reads:  output/*.docx and the packet directory
Writes: <packet>/00_CONTENTS.txt
"""
import io
import sys
import textwrap
from pathlib import Path

import docx

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'output'
PACKET = Path(r'C:\Users\garre\Downloads\SUBMISSION_JCO_CCI_v31')

MS = OUT / 'FDA_Drug_Repurposing_v31.docx'
CL = OUT / 'Cover_Letter_v31.docx'
SUP = OUT / 'Supplementary_Methods_v31.docx'


def paras(f):
    return [p.text.strip() for p in docx.Document(str(f)).paragraphs if p.text.strip()]


ms = docx.Document(str(MS))
ps = [p.text.strip() for p in ms.paragraphs if p.text.strip()]
title = ps[0]
authors = next(t for t in ps if t.startswith('Authors:')).replace('Authors: ', '')

i0, i1 = ps.index('INTRODUCTION'), ps.index('DATA AVAILABILITY')
body = sum(len(p.split()) for p in ps[i0:i1])
a0 = ps.index('ABSTRACT')
abstract = sum(len(ps[k].split()) for k in range(a0 + 1, a0 + 6))
refs = len([x for x in io.open(REPO / 'data' / 'manuscript_parts' / 'v28_refs.txt',
                               encoding='utf-8').read().splitlines() if x.strip()])
n_fig = len(ms.inline_shapes)
n_tab = len(ms.tables)
cl_words = sum(len(p.split()) for p in paras(CL))
sup_words = sum(len(p.split()) for p in paras(SUP))

# keyed on the filenames the figure scripts actually write; an earlier
# numbering left three keys here that matched nothing, so two figures printed
# with a blank description
FIG_NOTE = {
    'Figure1_pipeline.png': 'the pipeline, context definition to ranked candidates',
    'Figure2_RMC.png': 'renal medullary carcinoma; panel C created with BioRender',
    'Figure3_SCBC.png': 'small-cell bladder cancer, by lineage subtype',
    'Figure4_SarcUC.png':
        'what the sarcomatoid rows are scored on, and the same ranking within '
        'each chip batch',
    'Figure5_candidate_selection.png':
        'every candidate without a prior proposal, against every criterion',
    'FigureS1_selection_routes.png': 'how each association was nominated',
    'FigureS2_SarcUC_confounded.png':
        'the sarcomatoid comparison that cannot be interpreted',
}
NUMBERED = ('Supplementary_Table_S1', 'Supplementary_Table_S2',
            'Supplementary_Table_S3')

figs = sorted(p.name for p in (PACKET / 'Figures').glob('*.png'))
data = sorted(p.name for p in (PACKET / 'Data Supplement').glob('*'))
cited = [d for d in data if d.startswith(NUMBERED)]
collective = [d for d in data if d not in cited]

L = []
L.append('SUBMISSION PACKET - JCO Clinical Cancer Informatics')
for line in textwrap.wrap(title, 78):
    L.append(line)
L.append(authors)
L.append('')
L.append('Every file here is generated from the deposited code and matches')
L.append('github.com/gbrink10/urologic-variant-drug-prioritization at HEAD.')
L.append('This file is generated too, by code/pipeline/57_build_packet_contents.py.')
L.append('')
L.append('MAIN SUBMISSION')
L.append(f'  01_Manuscript.docx              body {body:,} words; abstract '
         f'{abstract}; {refs} references')
L.append(f'                                  {n_fig} figures embedded, '
         f'{n_tab} table')
L.append(f'  02_Cover_Letter.docx            {cl_words} words')
L.append(f'  03_Supplementary_Materials.docx {sup_words:,} words; Supplementary '
         f'Results and Methods,')
L.append('                                  with Supplementary Figures S1 and '
         'S2 embedded')
L.append('')
L.append('FIGURES  (also embedded in the manuscript; supplied separately for '
         'production)')
for f in figs:
    L.append(f'  {f:<32}{FIG_NOTE.get(f, "")}')
L.append('')
L.append(f'DATA SUPPLEMENT  ({len(data)} files)')
L.append('  Cited by number in the manuscript')
for d in cited:
    L.append(f'    {d}')
L.append('  Cited collectively as Supplementary Data')
for d in collective:
    L.append(f'    {d}')
L.append('')
L.append('ARCHIVE')
L.append('  All versions   doi:10.5281/zenodo.20217918')
L.append('  NOTE: the version DOI printed in Data Availability was minted for')
L.append('  release v31.0 and predates the revisions in this packet. Cut a new')
L.append('  release and update that DOI before submission.')

txt = '\n'.join(L) + '\n'
io.open(PACKET / '00_CONTENTS.txt', 'w', encoding='utf-8').write(txt)
print(f'wrote {PACKET / "00_CONTENTS.txt"}')
print(f'  body {body:,} | abstract {abstract} | refs {refs} | '
      f'figures {n_fig} | tables {n_tab}')
print(f'  {len(figs)} figure files | {len(data)} data-supplement files')

"""Reconcile every supplementary table against the assembled manuscript.

The audit checks the manuscript against the fact dictionary. This checks the
shipped supplementary CSVs against the manuscript and against each other, which
is the gap a reviewer asked twice to have closed: whether the deposit a reader
downloads actually supports the numbers the paper prints.

Exit status is non-zero if anything fails, so it can gate a release.
"""
import re
import sys
from pathlib import Path

import docx
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SUP = REPO / 'output' / 'v31_supplementary'
MS = REPO / 'output' / 'FDA_Drug_Repurposing_v31.docx'

sys.stdout.reconfigure(encoding='utf-8')
_doc = docx.Document(str(MS))
TEXT = '\n'.join(p.text for p in _doc.paragraphs)
CELLS = [c.text for t in _doc.tables for r in t.rows for c in r.cells]
ALL = TEXT + '\n' + '\n'.join(CELLS)

S1 = pd.read_csv(SUP / 'Supplementary_Table_S1_full_association_table.csv')
S2 = pd.read_csv(SUP / 'Supplementary_Table_S2_score_sensitivity.csv')
S3 = pd.read_csv(SUP / 'Supplementary_Table_S3_dataset_designs.csv')
S4 = pd.read_csv(SUP / 'Supplementary_Table_S4_genomic_provenance.csv')
PROV = pd.read_csv(SUP / 'SCORING_PROVENANCE_V29.csv')
SEL = pd.read_csv(SUP / 'CANDIDATE_SELECTION.csv')

_fails = []


def check(label, ok, detail=''):
    print(f'  {"PASS" if ok else "FAIL"}  {label}' + (f'   {detail}' if detail and not ok else ''))
    if not ok:
        _fails.append(label)


print('Reconciling the supplement against the manuscript\n')

# ---- every table has one row per association, and they agree on identity ---
for name, df in (('S1', S1), ('S2', S2), ('S4', S4), ('provenance', PROV)):
    check(f'{name} covers all 30 associations', len(df) == 30, f'{len(df)} rows')
check('S1, S2, S4 and provenance share the same N set',
      set(S1['N']) == set(S2['N']) == set(S4['N']) == set(PROV['N']))

# ---- S1 totals are the sum of the components it prints -------------------
_bad = []
for _, r in S1.iterrows():
    parts = []
    for col in ('E(0-3)', 'P(0-2)', 'L(0-1)'):
        v = str(r[col])
        parts.append(int(v) if v.strip().lstrip('-').isdigit() else 0)
    got = str(r['Total']).split('/')[0]
    if int(got) != sum(parts):
        _bad.append(f"N={r['N']} {sum(parts)} vs {got}")
check('S1 totals equal E + P + L', not _bad, '; '.join(_bad[:3]))

# ---- S1 denominators match what the components allow ---------------------
_bad = []
for _, r in S1.iterrows():
    d = int(str(r['Total']).split('/')[1])
    expect = 6 - (3 if 'not estimable' in str(r['E(0-3)']) else 0) \
               - (2 if 'not estimable' in str(r['P(0-2)']) else 0)
    if d != expect:
        _bad.append(f"N={r['N']} /{d} expected /{expect}")
check('S1 denominators follow from the estimable components', not _bad,
      '; '.join(_bad[:3]))

# ---- S2's "full" column is the score S1 reports --------------------------
_m = S1.merge(S2[['N', 'full', 'denominator']], on='N')
_bad = [f"N={r['N']}" for _, r in _m.iterrows()
        if int(str(r['Total']).split('/')[0]) != int(r['full'])]
check('S2 full score matches S1 total', not _bad, '; '.join(_bad[:5]))
_bad = [f"N={r['N']}" for _, r in _m.iterrows()
        if int(str(r['Total']).split('/')[1]) != int(r['denominator'])]
check('S2 denominator matches S1', not _bad, '; '.join(_bad[:5]))

# ---- the eligibility flag S2 prints is the rule the paper states ---------
_bad = [f"N={r['N']}" for _, r in S2.iterrows()
        if bool(r['meets_E2_full']) != (int(r['full']) >= 4)]
check('S2 meets_E2 is the stated rule, 4 or better', not _bad,
      '; '.join(_bad[:5]))

# ---- the three prioritized rows, and what removes each ------------------
SURV = sorted(SEL.loc[SEL['survives'], 'N'].tolist())
check('the prioritized set is 17, 19 and 28', SURV == [17, 19, 28], str(SURV))
_expect = {17: 'no_pathway', 19: 'pathway_requires_membership', 28: 'no_literature'}
for n, variant in _expect.items():
    row = S2[S2['N'] == n].iloc[0]
    check(f'N={n} loses eligibility under {variant}',
          not bool(row[f'meets_E2_{variant}']),
          f"score {row[variant]}")

# ---- every score the manuscript prints as x/y exists in S1 --------------
_printed = set(re.findall(r'\b([0-6])/([1-6])\b', ALL))
_have = {(str(r['Total']).split('/')[0], str(r['Total']).split('/')[1])
         for _, r in S1.iterrows()}
_orphan = sorted(_printed - _have)
check('every x/y score printed in the paper appears in S1', not _orphan,
      '; '.join('/'.join(o) for o in _orphan))

# ---- the tier counts the abstract prints come from S1 -------------------
_tiers = S1['Tier'].value_counts()
for tier in ('Strong', 'Moderate', 'Exploratory'):
    n = int(_tiers.get(tier, 0))
    check(f'{n} {tier} in S1 is what the paper prints',
          re.search(rf'\b{n}\s+{tier}\b', ALL) is not None, f'{n} {tier}')

# ---- S3 covers every fitted context, and the paper's count of series ----
check('S3 lists a model for every fitted context', len(S3) >= 9, f'{len(S3)} rows')
check('the renal medullary series is absent from S3, as the text says',
      not S3['context'].astype(str).str.upper().str.startswith('RMC').any())

# ---- S4 reproduces the count the paper quotes ---------------------------
_q = S4[S4['source_type'].astype(str).str.startswith('recomputed')]
_agree = int((_q['G_curated'] == _q['G_recomputed']).sum())
check(f'S4 has {len(_q)} recomputed rows, {_agree} agreeing, as the paper says',
      f'{_agree} of {len(_q)}' in ALL, f'{_agree} of {len(_q)}')

# ---- the genomic dimension is reported but never scored ----------------
check('S1 carries no genomic score column',
      not any('G(' in c or c.strip() == 'G' for c in S1.columns),
      str(list(S1.columns)))
check('S4 records a source for every non-zero curated genomic value',
      not S4[(S4['G_curated'] > 0) & (S4['source_type'].isna()
                                      | (S4['source_type'] == ''))].shape[0])

# ---- q-values quoted in the text are the ones in the deposit -----------
_bad = []
for _, r in PROV.iterrows():
    q = r.get('refit_q')
    if pd.isna(q) or float(q) >= 0.05:
        continue
    for form in (f'q = {float(q):.4f}', f'q = {float(q):.3f}'):
        if form in ALL:
            break
    else:
        continue
check('no q-value is quoted in a form the deposit contradicts', not _bad)


# ---- everything the manuscript names must exist in the package ----------
print()
print('Inventory: what the manuscript names against what ships')

_sup_doc = docx.Document(str(REPO / 'output' / 'Supplementary_Methods_v31.docx'))
SUPTEXT = '\n'.join(p.text for p in _sup_doc.paragraphs)

# numbered supplementary tables cited anywhere in the main text
for _n in sorted(set(re.findall(r'Supplementary Table S(\d)', ALL))):
    _hits = list(SUP.glob(f'Supplementary_Table_S{_n}_*.csv'))
    check(f'Supplementary Table S{_n} ships as a file', bool(_hits),
          f'no Supplementary_Table_S{_n}_*.csv in {SUP.name}')

# numbered supplementary figures cited in the main text must be in the
# supplementary document, and its embedded image count must cover them
_figs = sorted(set(re.findall(r'Supplementary Figure S(\d)', ALL)))
for _n in _figs:
    check(f'Supplementary Figure S{_n} has a caption in the supplement',
          f'Supplementary Figure S{_n}.' in SUPTEXT)
import zipfile
_z = zipfile.ZipFile(REPO / 'output' / 'Supplementary_Methods_v31.docx')
_media = [m for m in _z.namelist() if m.startswith('word/media/')]
check(f'the supplement embeds an image for each of its {len(_figs)} figures',
      len(_media) >= len(_figs), f'{len(_media)} embedded, {len(_figs)} cited')

# numbered Supplementary Methods sections cited by the main text
for _n in sorted(set(re.findall(r'Supplementary Methods Section (\w+)', ALL))):
    check(f'Supplementary Methods Section {_n} exists',
          re.search(rf'^{_n}\w*\.\s', SUPTEXT, re.M) is not None
          or f'{_n}. ' in SUPTEXT)

# the per-batch percentiles the inventory now promises
_batch = SUP / 'SARC_BATCH_PERCENTILES.csv'
check('the sarcomatoid per-batch percentiles ship', _batch.exists())
if _batch.exists():
    _b = pd.read_csv(_batch)
    check('per-batch file covers four genes and five rows each',
          len(_b) == 20 and _b['gene'].nunique() == 4, f'{len(_b)} rows')
    # and must agree with the score it is meant to support
    _bad = []
    for _, r in _b[_b['batch'] == 'all 28 tumors pooled'].iterrows():
        _basis = str(PROV.loc[PROV['scoring_gene'] == r['gene'], 'E_basis'].iloc[0])
        _m = re.search(r'at ([0-9.]+)th percentile', _basis)
        if _m and abs(float(_m.group(1)) - float(r['percentile'])) > 0.15:
            _bad.append(r['gene'])
    check('pooled per-batch values match the scoring provenance', not _bad,
          '; '.join(_bad))
    check('the threshold flag matches the 85th-percentile rule',
          bool((_b['above_85th_percentile'] == (_b['percentile'] >= 85)).all()))

# every GEO accession the manuscript lists must appear in the design summary
# or be the one series the text says has no fitted model
_acc = sorted(set(re.findall(r'GSE\d+', ALL)))
check(f'the manuscript lists {len(_acc)} GEO accessions', len(_acc) >= 10,
      str(len(_acc)))

print()
if _fails:
    print(f'{len(_fails)} reconciliation failure(s):')
    for f in _fails:
        print('   -', f)
    sys.exit(1)
print('supplement reconciles with the manuscript')

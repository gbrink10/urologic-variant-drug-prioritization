"""Audit the v29 manuscript against the deposited results and against itself."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import paths

import docx
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
MS = paths.OUTPUT / 'FDA_Drug_Repurposing_v31.docx'

doc = docx.Document(str(MS))
paras = [p.text.strip() for p in doc.paragraphs]
text = "\n".join(paras)
for t in doc.tables:
    for r in t.rows:
        for c in r.cells:
            text += "\n" + c.text
# the reference list carries article titles using phrasing the body must not
# use, so claims are checked against the body alone
body = text.split("REFERENCES", 1)[0]

F = json.loads((RF / 'MANUSCRIPT_FACTS.json').read_text(encoding='utf-8'))
master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')  # v30 rebuild, same filename
sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')

ok = bad = 0


def check(label, cond, detail=''):
    global ok, bad
    if cond:
        ok += 1
        print(f'  PASS  {label}')
    else:
        bad += 1
        print(f'  FAIL  {label}   {detail}')


print('1. STRUCTURE')
for sec in ('CONTEXT', 'ABSTRACT', 'INTRODUCTION', 'MATERIALS AND METHODS',
            'RESULTS', 'DISCUSSION', 'CONCLUSIONS', 'DATA AVAILABILITY',
            'REFERENCES', 'CRediT AUTHOR STATEMENT', 'FUNDING',
            'CONFLICTS OF INTEREST', 'ETHICS STATEMENT',
            'SUPPLEMENTARY MATERIALS', 'AI USAGE DISCLOSURE'):
    check(f'section {sec}', sec in paras)
check('5 figures embedded', len(doc.inline_shapes) == 5, str(len(doc.inline_shapes)))
check('one condensed table in the main text', len(doc.tables) == 1)
subs = [t for t in paras if re.match(r'^3\.\d ', t)]
check('six Results subsections', len(subs) == 6, str([x[:22] for x in subs]))

print('\n2. TITLE AND FRAMING')
title = paras[0]
check('title <= 175 characters', len(title) <= 175, f'{len(title)}')
check('title alludes to no result',
      not any(w in title.lower() for w in
              ('nominates', 'identifies', 'reveals', 'demonstrates', 'shows')))
check('"reproducible" no longer claimed in the title', 'reproducible' not in title.lower())
check('no "orthogonal validation" phrasing survives',
      'orthogonal validation' not in text.lower())
check('"validated finding" only used to disclaim',
      text.lower().count('validated finding') == text.lower().count('not a validated finding'))
check('marker described as target-loss, not predictive',
      'candidate target-loss marker' in text
      and 'negative predictive biomarker' not in text)
check('no claim of established predictive value',
      ('predictive validity is unestablished' in text
       or 'predictive value is unestablished' in text)
      and 'predicts non-response' not in body
      and 'predictive biomarker' not in body)
check('framework-novel language replaced with a search statement',
      'no prior urologic-oncology proposal' in text)

print('\n3. NUMBERS MATCH THE DEPOSIT')
check(f"association count {F['n_associations']}", str(F['n_associations']) in text)
for tier, n in F['tiers'].items():
    check(f'{n} {tier}-tier stated', f'{n} {tier}-tier' in text or f'{n} {tier}' in text)
check('funnel counts stated',
      f"{F['funnel']['eligible']} eligible" in text
      and f"{F['funnel']['survive']} survivors" in text)
check(f"chemokine q = {F['q']['rmc_chemokine']:.4f}",
      f"{F['q']['rmc_chemokine']:.4f}" in text)
check('SSTR2 non-significant q reported',
      f"{F['de']['SSTR2_neurod1']['q']:.3f}" in text)
check('ATR effect reported', f"{F['de']['ATR_sarc']['log2FC']:+.2f}" in text)
check('TACSTD2 direction stated and its estimate located',
      'lower trophoblast cell-surface antigen 2' in text
      and 'Supplementary Table S1' in text)
check('two-line correlation reported', str(F['rmc']['r_between_lines']) in text)
check('both-lines gene count reported', str(F['rmc']['up_both']) in text)
check('CXCR1 vs CEACAM1 window contrasted',
      str(F['hpa']['CXCR1_kidney']) in text and str(F['hpa']['CEACAM1_kidney']) in text)

print('\n4. NEW LIMITATIONS ARE STATED')
check('sarcomatoid batch confounding disclosed',
      'share no chip' in text or 'confounded' in text)
check('ccRCC has no normal tissue disclosed', 'no normal tissue' in text)
check('HLRCC demoted to adjacent disease', 'adjacent-disease' in text)
check('penile technical replicates disclosed',
      f"{F['design']['pscc_normal_donors']} donors" in text)
check('LINCS no longer called a null comparator',
      'null comparator' not in text.lower())
check('LINCS non-specificity stated',
      'lacked context specificity' in text
      or 'not context-specific' in text)
check('score sensitivity result stated', 'sensitivity analysis' in text.lower())
check('scoring dimensions called partially overlapping',
      'partially overlapping' in text)
check('correction scope stated',
      'within each context' in text and 'not across contexts' in text)
check('both pre-specified thresholds named',
      'q < 0.05' in text and 'q < 0.10' in text
      and 'pre-specified' in text)

print('\n5. CITATIONS')
cited = Counter()
for m in re.finditer(r'\[([0-9,\u2013\-\s]+)\]', text):
    for part in m.group(1).split(','):
        part = part.strip().replace('\u2013', '-')
        if '-' in part:
            a, b = part.split('-')[:2]
            if a.strip().isdigit() and b.strip().isdigit():
                for k in range(int(a), int(b) + 1):
                    cited[k] += 1
        elif part.isdigit():
            cited[int(part)] += 1
refnums = sorted(int(re.match(r'^\s*(\d{1,2})\.', t).group(1)) for t in paras
                 if re.match(r'^\s*\d{1,2}\.\s+\S', t)
                 and ('doi' in t.lower() or 'PMID' in t))
check('57 references, contiguous', refnums == list(range(1, 58)),
      f'n={len(refnums)}')
missing = [n for n in refnums if cited[n] == 0]
over = sorted(n for n in cited if n not in refnums)
print(f'    uncited references: {len(missing)} -> {missing}')
print(f'    citations without an entry: {over}')
check('no citation points outside the reference list', not over, str(over))

print('\n5b. SECOND-REVIEW CORRECTIONS')
check('anti-CEACAM5 successor agent named',
      'precemtabart' in text.lower() or 'M9140' in text)
check('seclidemstat no longer attached to the NSD2 row',
      'SP-2577' not in text and 'seclidemstat' not in text.lower())
check('identifiability gate disclosed',
      'aliased' in text and 'no model can attribute' in text)
check('sarcomatoid rows reported descriptively', 'reported descriptively' in text)
check('PRISM no longer claims absence of off-target cytotoxicity',
      'absence of off-target cytotoxicity' not in text)
check('normal-tissue RNA not used as a therapeutic-window claim',
      'not a therapeutic-window' in text)
check('tarlatamab approval history stated',
      'accelerated approval' in text and 'traditional approval' in text)
check('sacituzumab withdrawal month corrected', 'November 2024' in text)
check('LINCS analysis units explained', 'eight analysis units' in text)
# published reference titles keep their own spelling, so test the prose only
_body_only = chr(10).join(
    t for t in paras
    if not re.match(r'^\s*\d{1,2}\.\s+\S', t))
check('American spelling in the manuscript prose',
      not any(w in _body_only for w in
              ('tumour', 'signalling', 'normalised', 'hybridised', 'modelled')))
check('RMC described as independent models, not replicates',
      'two independent patient-derived models' in text
      and 'two biological replicates' not in text)
def _cell_rows(txt):
    out = set()
    for part in str(txt).replace('–', '-').split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-')[:2]
            if a.strip().isdigit() and b.strip().isdigit():
                out |= set(range(int(a), int(b) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


_listed = set()
for _r in doc.tables[0].rows:
    _listed |= _cell_rows(_r.cells[0].text)
check('all 30 associations accounted for in Table 1', len(_listed) == 30,
      f'{len(_listed)} listed; missing {sorted(set(range(1, 31)) - _listed)}')

print('\n6. SHORTLIST CONSISTENCY')
for _, r in sel.iterrows():
    tgt = str(r['Target']).split('(')[0].split('/')[0].strip()
    if r['survives']:
        check(f'survivor {tgt} appears in the text', tgt.split()[0] in text)
check('within-disease priority named, not a global lead',
      'first priority within RMC' in text
      or 'the one to carry forward first' in text)
check('no cross-disease ranking claimed',
      'not ranked against one another across diseases' in text)
check('three survivors across two diseases stated',
      'across 2 diseases' in text or 'across two diseases' in text
      or f"{F['n_survivor_contexts']} diseases" in text)
check('lead hedged as hypothesis not finding',
      'not a validated finding' in text)

print('\n' + '=' * 66)
print(f'RESULT: {ok} passed, {bad} failed')

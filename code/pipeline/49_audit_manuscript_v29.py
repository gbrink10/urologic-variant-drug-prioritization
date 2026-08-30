"""Audit the v29 manuscript against the deposited results and against itself."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import docx
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
MS = Path(r"C:\Users\garre\Downloads\FDA_Drug_Repurposing_v29.docx")

doc = docx.Document(str(MS))
paras = [p.text.strip() for p in doc.paragraphs]
text = "\n".join(paras)
for t in doc.tables:
    for r in t.rows:
        for c in r.cells:
            text += "\n" + c.text

F = json.loads((RF / 'MANUSCRIPT_FACTS.json').read_text(encoding='utf-8'))
master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')
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
check('negative biomarker described as candidate/hypothesised',
      'candidate negative predictive biomarker' in text)
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
check('TACSTD2 effect reported', f"{F['de']['TACSTD2_sarc']['log2FC']:+.2f}" in text)
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
check('LINCS non-specificity stated', 'not context-specific' in text
      or 'Neither is context-specific' in text)
check('score sensitivity result stated', 'sensitivity analysis' in text.lower())
check('scoring dimensions called partially overlapping',
      'partially overlapping' in text)
check('correction scope stated',
      'within each context' in text and 'not across contexts' in text)
check('10% threshold pre-specified and named',
      '10%' in text and 'pre-specified' in text)

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

print('\n6. SHORTLIST CONSISTENCY')
for _, r in sel.iterrows():
    tgt = str(r['Target']).split('(')[0].split('/')[0].strip()
    if r['survives']:
        check(f'survivor {tgt} appears in the text', tgt.split()[0] in text)
check('lead named as CXCR1/CXCR2', 'CXCR1/CXCR2 blockade is the lead candidate' in text)
check('lead hedged as hypothesis not finding',
      'not a validated finding' in text)

print('\n' + '=' * 66)
print(f'RESULT: {ok} passed, {bad} failed')

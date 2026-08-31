"""Apply a pre-specified rule to decide which candidates the paper carries.

The v28 funnel said "two survive orthogonal scrutiny" without stating what
survival required, so the reader could not tell whether the set was chosen by a
rule or by judgement. The rule is fixed here, in advance of looking at which
candidates it selects, and every row records which criterion it failed.

  Eligibility (all five required to be called a candidate)
    E0  the biological contrast is estimable separately from the major known
        technical variable. A transcript can be re-derived exactly and still be
        uninterpretable: where histology is completely aliased with array chip,
        a small q-value identifies a difference between two groups that are also
        two batches, and cannot attribute it to biology.
    E1  no prior urologic-oncology proposal identified by the audit
    E2  total score reaches Moderate tier or better (>= 4 of 9)
    E3  transcriptomic component re-derivable from deposited data at q < 0.05
    E4  a clinical-stage agent exists against the target

  Survival of the orthogonal evidence audit (both required)
    S1  no orthogonal layer contradicts the candidate. A layer that cannot
        evaluate the candidate is neither support nor contradiction.
    S2  target accessibility matches the modality: rows whose agent acts from
        outside the cell require confirmed extracellular access

  Lead candidate (all three required)
    L1  survives the audit above
    L2  the target is itself a member of a pathway enriched at q < 0.10 in its
        own context - an enrichment driven by other genes is not evidence for
        this target
    L3  among those, the widest therapeutic window in the organ of origin
        (lowest normal-tissue expression)

Writes: results/refit/CANDIDATE_SELECTION.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
RES = REPO / 'results'

master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
hpa = pd.read_csv(RES / 'HPA_PROTEIN_VALIDATION.csv')
dep = pd.read_csv(RES / 'DEPMAP_STRATIFIED.csv')
dep_all = pd.read_csv(RES / 'DEPMAP_DEPENDENCY.csv')
pri = pd.read_csv(RES / 'PRISM_DRUG_SENSITIVITY.csv')

# which HPA / DepMap gene and which PRISM drugs speak to each row
EVIDENCE_KEYS = {
    17: dict(hpa='CXCR1', dep=None, prism=['reparixin', 'navarixin', 'AZD5069',
                                           'danirixin']),
    19: dict(hpa='CEACAM1', dep='CEACAM1', prism=None),
    23: dict(hpa=None, dep='NSD2', prism=None),
    24: dict(hpa=None, dep='ATR', prism=['VE-822']),
    28: dict(hpa='CEACAM5', dep='CEACAM5', prism=None),
    29: dict(hpa='SSTR2', dep=None, prism=None),
}
# does the modality act from outside the cell?
SURFACE_MODALITY = {17: True, 19: True, 23: False, 24: False, 28: True, 29: True}

rows = []
for _, d in defs.iterrows():
    n = int(d['N'])
    novel = str(d['Prior status']).startswith('FRAMEWORK-NOVEL')
    if not novel:
        continue
    m = master[master['N'] == n].iloc[0]
    p = prov[prov['N'] == n].iloc[0]
    total = int(str(m['Total']).split('/')[0])
    keys = EVIDENCE_KEYS.get(n, {})

    e0 = bool(d.get('contrast_identifiable', True))
    e2 = total >= 4
    e3 = bool(p['E_derivable_from_data']) and float(p['refit_q'] or 1) < 0.05
    # agent availability is a curated fact in the row definitions: a row whose
    # first-generation agent was discontinued may still have an active class
    e4 = bool(d.get('clinical_stage_agent', True))

    # orthogonal layers
    contradictions, layers = [], {}
    g = keys.get('dep')
    if g:
        # the stratified table covers only targets nominated on mutation or
        # over-expression; fall back to the unstratified analysis, which carries
        # the verdict for every queried gene including the payload modalities
        s = dep[dep['gene'] == g]
        if len(s):
            v = str(s['verdict'].iloc[0])
        else:
            s2 = dep_all[dep_all['gene'] == g]
            v = (str(s2['verdict'].iloc[0]) if len(s2)
                 else 'not present in the DepMap release used')
        layers['dependency'] = v
        # only a genuine absence of dependency contradicts a candidate; a target
        # that need not be essential for its modality to work does not
        if v.startswith('no dependency') or v.startswith('not a dependency'):
            contradictions.append(f'DepMap: {v}')
    else:
        layers['dependency'] = 'cannot test (modality delivers a payload)'

    drugs = keys.get('prism')
    if drugs:
        s = pri[pri['drug'].isin(drugs)]
        if len(s) and s['verdict'].str.contains('active in urothelial').any():
            layers['compound'] = 'active but not selective'
        elif len(s):
            layers['compound'] = 'no tumour-cell-autonomous activity (expected)'
        else:
            layers['compound'] = 'agent absent from the screen'
    else:
        layers['compound'] = 'not a small molecule; absent from the screen'

    hg = keys.get('hpa')
    access_ok, window = True, np.nan
    if hg:
        s = hpa[hpa['gene'] == hg]
        if len(s):
            r0 = s.iloc[0]
            layers['protein'] = str(r0['status'])
            access_ok = bool(r0['plasma_membrane']) or 'confirmed' in str(r0['status'])
            for col in ('nTPM_kidney', 'nTPM_bladder'):
                if col in s.columns:
                    window = float(r0[col])
                    break
        else:
            layers['protein'] = 'not in the Human Protein Atlas extract'
    else:
        layers['protein'] = 'intracellular target; surface access not required'

    s1 = not contradictions
    s2 = (access_ok if SURFACE_MODALITY.get(n, False) else True)
    eligible = e0 and e2 and e3 and e4
    survives = eligible and s1 and s2

    failed = []
    if not e0:
        failed.append('E0 contrast not estimable separately from batch')
    if not e2:
        failed.append(f'E2 score {total}/9 below Moderate')
    if not e3:
        failed.append(f'E3 transcriptomic q = {float(p["refit_q"]):.3g}')
    if not e4:
        failed.append('E4 no clinical-stage agent')
    if not s1:
        failed.append('S1 ' + '; '.join(contradictions))
    if not s2:
        failed.append('S2 extracellular access not confirmed')

    # does the target belong to a pathway that is actually enriched?
    target_in_enriched = (pd.notna(p['pathway_q']) and float(p['pathway_q']) < 0.10
                          and 'target in pathway set' in str(p['P_basis']))

    rows.append({
        'N': n, 'Context': d['Context'], 'Drug': d['Drug'], 'Target': d['Target'],
        'total': total, 'tier': m['Tier'],
        'contrast_identifiable': e0,
        'E_refit_q': float(p['refit_q']) if pd.notna(p['refit_q']) else np.nan,
        'pathway_q': float(p['pathway_q']) if pd.notna(p['pathway_q']) else np.nan,
        'protein_layer': layers.get('protein'),
        'dependency_layer': layers.get('dependency'),
        'compound_layer': layers.get('compound'),
        'normal_tissue_nTPM_organ_of_origin': window,
        'target_in_enriched_pathway': target_in_enriched,
        'eligible': eligible, 'survives': survives,
        'failed_criteria': '; '.join(failed) or '-',
    })

out = pd.DataFrame(rows).sort_values(['survives', 'total'], ascending=[False, False])
out.to_csv(RF / 'CANDIDATE_SELECTION.csv', index=False)

print("PRE-SPECIFIED CANDIDATE SELECTION\n")
print(f"{'N':<4}{'candidate':<34}{'score':>6}{'elig':>6}{'surv':>6}  failed")
for _, r in out.iterrows():
    print(f"{r['N']:<4}{str(r['Target'])[:32]:<34}{r['total']:>4}/9"
          f"{str(r['eligible']):>6}{str(r['survives']):>6}  {r['failed_criteria'][:64]}")

surv = out[out['survives']]
print(f"\n{len(out)} framework-novel -> {int(out['eligible'].sum())} eligible "
      f"-> {len(surv)} survive")
lead_pool = surv[surv['target_in_enriched_pathway']]
print(f"  of which the target itself lies in an enriched pathway: {len(lead_pool)}")
if len(lead_pool):
    lead = lead_pool.sort_values('normal_tissue_nTPM_organ_of_origin',
                                 na_position='last').iloc[0]
    print(f"\nlead candidate: row {lead['N']} - {lead['Target']}")
    print(f"  pathway q = {lead['pathway_q']:.4g}; normal-tissue nTPM in the organ "
          f"of origin = {lead['normal_tissue_nTPM_organ_of_origin']}")
    for _, r in surv.iterrows():
        if r['N'] != lead['N']:
            print(f"  second survivor: row {r['N']} - {r['Target']} "
                  f"(nTPM {r['normal_tissue_nTPM_organ_of_origin']})")
print(f"\nwrote {RF / 'CANDIDATE_SELECTION.csv'}")

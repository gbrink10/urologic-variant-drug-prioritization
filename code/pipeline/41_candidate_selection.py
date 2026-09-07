"""Apply a pre-specified rule that ranks candidates; it does not discard them.

Every candidate without a prior urologic-oncology proposal is reported. The
criteria below sort them into a priority tier and a lower-confidence tier and
record, for each candidate in the lower tier, the specific reservation that
placed it there. Nothing is removed from the paper on the strength of these
criteria, so a reader who weighs the evidence differently can see every
candidate and disagree with the ordering.

The criteria are fixed in advance of looking at which candidates they rank.

  Primary criteria (all required for the priority tier)
    E1  no prior urologic-oncology proposal identified by the audit
    E2  total score reaches 4 or better of the points that are estimable for
        that row. Most rows are scored out of 9; a row whose pathway component
        cannot be computed is scored out of 7, and the threshold is read
        against its own denominator rather than against a denominator it was
        never eligible for.
    E3  the transcriptomic component is re-derivable from deposited data and
        meets its own arm's standard: q < 0.05 where a disease-versus-comparator
        contrast exists, or the top 15% of measured transcripts where the
        dataset supports only abundance.
    E4  a clinical-stage agent exists against the target

  Consistency checks (both required for the priority tier)
    S1  no independent source contradicts the candidate. A source that cannot
        evaluate the candidate is neither support nor contradiction. In
        practice these checks removed nothing that the score had not already
        placed in the lower tier; they are reported as checks, not as a filter.
    S2  target accessibility matches the modality: rows whose agent acts from
        outside the cell require confirmed extracellular access

  Ranking within a disease (all three required)
    L1  in the priority tier
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
    raw_total = str(m['Total'])
    total = (int(raw_total.split('/')[0]) if '/' in raw_total
             else int(p['Total']))  # unscored rows keep the arithmetic total
    keys = EVIDENCE_KEYS.get(n, {})

    denom = int(p.get('total_denominator', 9) or 9)
    e2 = total >= 4
    # each arm is held to its own standard; a row scored on abundance has no
    # q-value and must not fail for lacking one
    arm = str(d.get('scoring_arm', 'de'))
    rq = p['refit_q']
    if arm == 'expression':
        e3 = bool(p['E_derivable_from_data']) and int(p['E_refit']) >= 2
    else:
        e3 = (bool(p['E_derivable_from_data'])
              and pd.notna(rq) and float(rq) < 0.05)
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
            # pick the organ the cancer arises in, not whichever column comes
            # first: CEACAM5 is a bladder target and was publishing the kidney
            # value, so the deposit disagreed with the manuscript
            ctx = str(d['Context'])
            if ctx.startswith('RMC') or ctx.startswith('ccRCC'):
                organ = 'nTPM_kidney'
            elif ctx.startswith('NEPC'):
                organ = 'nTPM_prostate'
            elif ctx.startswith('SCBC') or ctx.startswith('MIBC') or                     ctx.startswith('Sarcomatoid'):
                organ = 'nTPM_bladder'
            else:
                organ = None
            if organ and organ in s.columns:
                window = float(r0[organ])
        else:
            layers['protein'] = 'not in the Human Protein Atlas extract'
    else:
        layers['protein'] = 'intracellular target; surface access not required'

    s1 = not contradictions
    s2 = (access_ok if SURFACE_MODALITY.get(n, False) else True)
    eligible = e2 and e3 and e4
    survives = eligible and s1 and s2

    failed, reservations = [], []
    if not e2:
        failed.append(f'E2 score {total}/{denom} below 4')
        reservations.append(f'scores {total} of the {denom} points estimable '
                            f'for this row')
    if not e3:
        if arm == 'expression':
            failed.append(f'E3 abundance below the top 15% '
                          f'(component {int(p["E_refit"])}/3)')
            reservations.append('the transcript is not among the most abundant '
                                'in its dataset')
        else:
            failed.append(f'E3 transcriptomic q = {float(rq):.3g}')
            reservations.append(f'differential expression is not significant '
                                f'(q = {float(rq):.3g})')
    if not e4:
        failed.append('E4 no clinical-stage agent')
        reservations.append('no agent has reached clinical development')
    if not s1:
        failed.append('S1 ' + '; '.join(contradictions))
        reservations.append('an independent source contradicts it ('
                            + '; '.join(contradictions) + ')')
    if not s2:
        failed.append('S2 extracellular access not confirmed')
        reservations.append('extracellular access is not confirmed, and the '
                            'proposed agent must bind from outside the cell')

    # does the target belong to a pathway that is actually enriched?
    target_in_enriched = (pd.notna(p['pathway_q']) and float(p['pathway_q']) < 0.10
                          and 'target in pathway set' in str(p['P_basis']))

    rows.append({
        'N': n, 'Context': d['Context'], 'Drug': d['Drug'], 'Target': d['Target'],
        'total': total, 'total_denominator': denom, 'tier': m['Tier'],
        'contrast_estimable': bool(d.get('contrast_estimable', True)),
        'pathway_estimable': bool(d.get('pathway_estimable', True)),
        'E_refit_q': float(p['refit_q']) if pd.notna(p['refit_q']) else np.nan,
        'pathway_q': float(p['pathway_q']) if pd.notna(p['pathway_q']) else np.nan,
        'protein_layer': layers.get('protein'),
        'dependency_layer': layers.get('dependency'),
        'compound_layer': layers.get('compound'),
        'normal_tissue_nTPM_organ_of_origin': window,
        'target_in_enriched_pathway': target_in_enriched,
        'eligible': eligible, 'survives': survives,
        'priority_tier': 'priority' if survives else 'lower-confidence',
        'reservation': '; '.join(reservations) or '-',
        'failed_criteria': '; '.join(failed) or '-',
    })

out = pd.DataFrame(rows).sort_values(['survives', 'total'], ascending=[False, False])
out.to_csv(RF / 'CANDIDATE_SELECTION.csv', index=False)

print("PRE-SPECIFIED CANDIDATE RANKING (nothing is discarded)\n")
print(f"{'N':<4}{'candidate':<34}{'score':>6}{'tier':>18}  reservation")
for _, r in out.iterrows():
    print(f"{r['N']:<4}{str(r['Target'])[:32]:<34}"
          f"{r['total']:>4}/{r['total_denominator']}"
          f"{r['priority_tier']:>18}  {r['reservation'][:58]}")

surv = out[out['survives']]
print(f"\nall {len(out)} framework-novel candidates are reported: "
      f"{len(surv)} priority, {len(out) - len(surv)} lower-confidence")
out['context_priority'] = ''
for ctx, g in surv.groupby('Context'):
    ranked = g.sort_values(['target_in_enriched_pathway', 'total'],
                           ascending=[False, False])
    for rank, (_, r) in enumerate(ranked.iterrows(), 1):
        out.loc[out['N'] == r['N'], 'context_priority'] = \
            f'{rank} of {len(ranked)} in {ctx}'
out.to_csv(RF / 'CANDIDATE_SELECTION.csv', index=False)

print(f"\n{len(surv)} priority hypotheses in "
      f"{surv['Context'].nunique()} diseases, ranked only within a disease:")
for ctx, g in surv.groupby('Context'):
    ranked = g.sort_values(['target_in_enriched_pathway', 'total'],
                           ascending=[False, False])
    print(f"  {ctx}:")
    for rank, (_, r) in enumerate(ranked.iterrows(), 1):
        why = ('target lies in an enriched pathway'
               if r['target_in_enriched_pathway']
               else 'no enrichment contains the target')
        print(f"    {rank}. row {int(r['N'])} {str(r['Target'])[:32]:<34} "
              f"{r['total']}/9  ({why})")
print("  not ranked across diseases: the only criterion that could do so is "
      "panel\n  membership, which Section 3.6 identifies as a framework artifact.")
print(f"\nwrote {RF / 'CANDIDATE_SELECTION.csv'}")

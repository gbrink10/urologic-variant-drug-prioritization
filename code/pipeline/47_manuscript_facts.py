"""Assemble every number the manuscript states, from the deposited results.

The v26-v28 manuscript and its deposited CSV drifted apart in 42 fields because
the prose was typed and the table was generated separately. Here the facts are
computed once, written to JSON, and the manuscript builder interpolates them, so
a number can only be wrong if the analysis is wrong.

Writes: results/refit/MANUSCRIPT_FACTS.json
"""
import json
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
sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')
enr = pd.read_csv(RF / 'KEGG_ENRICHMENT_REFIT.csv')
enr = enr[enr['rule'] == 'q<0.05 & logFC>0.5']
rmc_enr = pd.read_csv(RF / 'RMC_ENRICHMENT.csv')
rmc = pd.read_csv(RF / 'RMC_REANALYSIS.csv', index_col=0)
summary = pd.read_csv(RF / 'REFIT_SUMMARY.csv')
hpa = pd.read_csv(RES / 'HPA_PROTEIN_VALIDATION.csv')
dep = pd.read_csv(RES / 'DEPMAP_DEPENDENCY.csv')
deps = pd.read_csv(RES / 'DEPMAP_STRATIFIED.csv')
pri = pd.read_csv(RES / 'PRISM_DRUG_SENSITIVITY.csv')
lincs = pd.read_csv(RF / 'LINCS_CONNECTIVITY_V29.csv')
manifest = pd.read_csv(REPO / 'data' / 'prepared' / 'PREPARED_MANIFEST.csv')

F = {}


def q_of(ctx, pathway):
    h = enr[(enr['context'] == ctx) & (enr['pathway'] == pathway)]
    return float(h['qvalue_BH'].iloc[0]) if len(h) else None


def de_of(n):
    r = prov[prov['N'] == n].iloc[0]
    return {'log2FC': None if pd.isna(r['refit_log2FC']) else float(r['refit_log2FC']),
            'q': None if pd.isna(r['refit_q']) else float(r['refit_q'])}


# ---- counts --------------------------------------------------------------
NOT_SCORED = 'Not scored (confounded cohort)'
scoreable = master[master['Tier'] != NOT_SCORED]
tiers = scoreable['Tier'].value_counts().to_dict()
ps = defs['Prior status'].astype(str)
F['n_associations'] = int(len(master))
F['n_scoreable'] = int(len(scoreable))
F['n_not_scored'] = int(len(master) - len(scoreable))
F['tiers'] = {k: int(v) for k, v in tiers.items()}
F['n_framework_novel'] = int(ps.str.startswith('FRAMEWORK-NOVEL').sum())
F['n_partially_novel'] = int(ps.str.startswith('PARTIALLY NOVEL').sum())
F['n_previously_proposed'] = int(F['n_associations'] - F['n_framework_novel']
                                 - F['n_partially_novel'] - 1)
F['per_context'] = defs['Context'].value_counts().to_dict()

# ---- funnel --------------------------------------------------------------
F['funnel'] = {'framework_novel': int(len(sel)),
               'eligible': int(sel['eligible'].sum()),
               'survive': int(sel['survives'].sum())}
F['n_survivor_contexts'] = int(sel[sel['survives']]['Context'].nunique())
F['survivors'] = [{'N': int(r['N']), 'target': r['Target'], 'drug': r['Drug'],
                   'total': int(r['total']), 'context': r['Context'],
                   'target_in_enriched': bool(r['target_in_enriched_pathway']),
                   'nTPM': None if pd.isna(r['normal_tissue_nTPM_organ_of_origin'])
                   else float(r['normal_tissue_nTPM_organ_of_origin'])}
                  for _, r in sel[sel['survives']].iterrows()]
F['excluded'] = [{'N': int(r['N']), 'target': r['Target'],
                  'reason': r['failed_criteria']}
                 for _, r in sel[~sel['survives']].iterrows()]

# ---- enrichment ----------------------------------------------------------
F['q'] = {
    'rmc_chemokine': float(rmc_enr[(rmc_enr['analysis'] == 'both lines')
                                   & (rmc_enr['pathway'] == 'Chemokine_signaling')
                                   ]['qvalue_BH'].iloc[0]),
    'rmc_cytokine': float(rmc_enr[(rmc_enr['analysis'] == 'both lines')
                                  & (rmc_enr['pathway'] == 'Cytokine_receptor_interaction')
                                  ]['qvalue_BH'].iloc[0]),
    'pscc_antigen': q_of('PSCC', 'Antigen_processing_presentation'),
    'sarc_epigenetic': q_of('SarcUC', 'Epigenetic_Regulation'),
    'sarc_cellcycle': q_of('SarcUC', 'Cell_Cycle'),
    'pou2f3_arachidonic': q_of('SCBC_POU2F3', 'Arachidonic_acid_metabolism'),
    'neurod1_neuroactive': q_of('SCBC_NEUROD1', 'Neuroactive_ligand_receptor'),
    'mibc_cellcycle': q_of('MIBC', 'Cell_Cycle'),
}
rmc_both = rmc_enr[rmc_enr['analysis'] == 'both lines']
F['rmc_top_pathway'] = str(rmc_both.nsmallest(1, 'pvalue')['pathway'].iloc[0])
F['rmc_top_q'] = float(rmc_both.nsmallest(1, 'pvalue')['qvalue_BH'].iloc[0])
F['n_pathways_surviving'] = {
    c: int((g['qvalue_BH'] < 0.10).sum()) for c, g in enr.groupby('context')}

# ---- key differential expression ----------------------------------------
F['de'] = {'CXCL8_rmc': de_of(17), 'CEACAM1_rmc': de_of(19),
           'HLA_DRA_pscc': de_of(20), 'NSD2_sarc': de_of(23),
           'ATR_sarc': de_of(24), 'TACSTD2_sarc': de_of(27),
           'CEACAM5_ascl1': de_of(28), 'SSTR2_neurod1': de_of(29),
           'PTGS1_pou2f3': de_of(30)}

# ---- renal medullary carcinoma reanalysis --------------------------------
x = rmc['l2fc_disease_48h_2C'].values
y = rmc['l2fc_disease_48h_219'].values
ok = np.isfinite(x) & np.isfinite(y)
F['rmc'] = {
    'genes_measured_both': int(len(rmc)),
    'r_between_lines': round(float(np.corrcoef(x[ok], y[ok])[0, 1]), 3),
    'up_both': int(rmc['up_both'].fillna(False).sum()),
    'up_2C': int(rmc['up_RMC2C'].fillna(False).sum()),
    'up_219': int(rmc['up_RMC219'].fillna(False).sum()),
    'chemokine_genes': [g for g in ('CXCL8', 'CXCL1', 'CXCL2', 'CXCL3')
                        if g in rmc.index],
}
for g in F['rmc']['chemokine_genes'] + ['CEACAM1']:
    if g in rmc.index:
        F['rmc'][g] = {'RMC2C': round(float(rmc.loc[g, 'l2fc_disease_48h_2C']), 2),
                       'RMC219': round(float(rmc.loc[g, 'l2fc_disease_48h_219']), 2),
                       'mean': round(float(rmc.loc[g, 'mean_l2fc_disease_48h']), 2)}

# ---- design limitations found --------------------------------------------
sarc_meta = pd.read_csv(REPO / 'data' / 'prepared' / 'SarcUC_meta.csv')
ct = pd.crosstab(sarc_meta['chip'], sarc_meta['group'])
pscc_meta = pd.read_csv(REPO / 'data' / 'prepared' / 'PSCC_meta.csv')
F['design'] = {
    'sarc_chips_total': int(len(ct)),
    'sarc_chips_sarc_only': int(((ct['SARC'] > 0) & (ct['UC'] == 0)).sum()),
    'sarc_chips_uc_only': int(((ct['UC'] > 0) & (ct['SARC'] == 0)).sum()),
    'sarc_chips_mixed': int(((ct > 0).sum(axis=1) > 1).sum()),
    'pscc_normal_arrays': int((pscc_meta['group'] == 'Normal').sum()),
    'pscc_normal_donors': int(pscc_meta.loc[pscc_meta['group'] == 'Normal',
                                            'donor'].nunique()),
    'ccrcc_samples': int(manifest.loc[manifest['context'] == 'ccRCC_METS',
                                      'samples'].iloc[0]),
    'ccrcc_q05_genes': int(summary.loc[summary['context'] == 'ccRCC_METS',
                                       'n_q05'].iloc[0]),
}

# ---- orthogonal layers ---------------------------------------------------
surface = hpa[hpa['surface_required'] == True]              # noqa: E712
F['hpa'] = {
    'n_surface_required': int(len(surface)),
    'n_confirmed': int((surface['status'] == 'extracellular access confirmed').sum()),
    'nTPM': {g: float(hpa.loc[hpa['gene'] == g, 'nTPM_bladder'].iloc[0])
             for g in ('DLL3', 'SSTR2', 'TACSTD2', 'CEACAM5') if (hpa['gene'] == g).any()},
    'CXCR1_kidney': float(hpa.loc[hpa['gene'] == 'CXCR1', 'nTPM_kidney'].iloc[0]),
    'CEACAM1_kidney': float(hpa.loc[hpa['gene'] == 'CEACAM1', 'nTPM_kidney'].iloc[0]),
}
F['depmap'] = {
    'n_urothelial_lines': int(dep['n_urothelial_lines'].max()),
    'NSD2_verdict': str(dep.loc[dep['gene'] == 'NSD2', 'verdict'].iloc[0]),
    'ATR_verdict': str(dep.loc[dep['gene'] == 'ATR', 'verdict'].iloc[0]),
    'CEACAM1_verdict': str(dep.loc[dep['gene'] == 'CEACAM1', 'verdict'].iloc[0]),
    'RPL5': float(dep.loc[dep['gene'] == 'RPL5', 'mean_gene_effect_urothelial'].iloc[0]),
    'PIK3CA_mut': float(deps.loc[deps['gene'] == 'PIK3CA', 'mean_effect_positive'].iloc[0]),
    'PIK3CA_wt': float(deps.loc[deps['gene'] == 'PIK3CA', 'mean_effect_negative'].iloc[0]),
    'NSD2_high': float(deps.loc[deps['gene'] == 'NSD2', 'mean_effect_positive'].iloc[0]),
    'G6PD_high': float(deps.loc[deps['gene'] == 'G6PD', 'mean_effect_positive'].iloc[0]),
}
F['prism'] = {
    'n_lines': 578,
    'bortezomib': float(pri.loc[pri['drug'] == 'bortezomib', 'mean_lfc_all_lines'].iloc[0]),
    'erlotinib_uro': float(pri.loc[pri['drug'] == 'erlotinib', 'mean_lfc_urothelial'].iloc[0]),
    'erlotinib_nonuro': float(pri.loc[pri['drug'] == 'erlotinib',
                                      'mean_lfc_nonurothelial'].iloc[0]),
    'erlotinib_q': float(pri.loc[pri['drug'] == 'erlotinib',
                                 'q_urothelial_vs_nonurothelial'].iloc[0]),
    've822_q': float(pri.loc[pri['drug'] == 'VE-822',
                             'q_urothelial_vs_nonurothelial'].iloc[0]),
    'polydatin_q': float(pri.loc[pri['drug'] == 'polydatin',
                                 'q_urothelial_vs_nonurothelial'].iloc[0]),
    'cxcr_quartet': {d: float(pri.loc[pri['drug'] == d, 'mean_lfc_urothelial'].iloc[0])
                     for d in ('reparixin', 'navarixin', 'AZD5069', 'danirixin')
                     if (pri['drug'] == d).any()},
}
rev = lincs[lincs['direction'] == 'reversal'].copy()
rev['qvalue'] = pd.to_numeric(rev['qvalue'], errors='coerce')
nom = rev[rev['is_nominated_agent'].fillna(False)]
F['lincs'] = {
    'n_contexts': int(lincs['context'].nunique()),
    'n_sig_reversal': int((rev['qvalue'] < 0.05).sum()),
    'n_terms': int(len(rev)),
    'best_nominated_rank': int(nom['rank'].min()) if len(nom) else None,
    'nominated_contexts': sorted(set(nom['context'])) if len(nom) else [],
    'any_rank1_nominated': bool(((rev['rank'] == 1)
                                 & rev['is_nominated_agent'].fillna(False)).any()),
}

# ---- refit method summary ------------------------------------------------
F['refit'] = {
    'n_contexts': int(len(summary)),
    'methods': sorted(set(summary['method'])),
    'pscc_dupcor': str(summary.loc[summary['context'] == 'PSCC', 'notes'].iloc[0]),
}

(RF / 'MANUSCRIPT_FACTS.json').write_text(json.dumps(F, indent=1), encoding='utf-8')
print(json.dumps(F, indent=1)[:4000])
print(f"\nwrote {RF / 'MANUSCRIPT_FACTS.json'}")

"""Give the genomic dimension a source for every non-zero value.

The genomic score was curated per row and the query behind each value was not
retained, so the number could not be checked against anything. This script
recomputes it where a public cohort exists and records the citation where one
does not, and writes GENOMIC_PROVENANCE.csv with one row per association.

For the three positive controls the frequency is recomputed from the TCGA
PanCancer Atlas 2018 through the cBioPortal API: the altered fraction is the
number of profiled samples carrying a mutation, a structural variant or a
GISTIC amplification or deep deletion in any queried gene, over the number of
samples profiled for those alteration types. That is the same quantity
cBioPortal's own OncoPrint reports.

The four rare cancers have no cohort in The Cancer Genome Atlas, so their
values stay curated from the disease-specific series already cited in the
manuscript, and this file records which series and which reported figure.

Binning, unchanged from Supplementary Methods: 3 above 30%, 2 from 15% to 30%
inclusive, 1 from 5% up to but not including 15%, 0 below 5% or not assessed.
"""
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parents[2]
API = 'https://www.cbioportal.org/api'
OUT = REPO / 'output' / 'v31_supplementary' / 'GENOMIC_PROVENANCE.csv'

# What each non-zero genomic value is a frequency OF. Where a row's value
# describes a biomarker-defined subset rather than one gene, every gene that
# defines the subset is queried and the union is the altered fraction.
PRAD = 'prad_tcga_pan_can_atlas_2018'
BLCA = 'blca_tcga_pan_can_atlas_2018'
KIRC = 'kirc_tcga_pan_can_atlas_2018'

QUERY = {
    1:  (PRAD, ['BCL2'], 'BCL2 altered in prostate adenocarcinoma'),
    2:  (PRAD, ['AURKA'], 'AURKA altered in prostate adenocarcinoma'),
    3:  (PRAD, ['EZH2'], 'EZH2 altered in prostate adenocarcinoma'),
    4:  (PRAD, ['DNMT1', 'DNMT3A'], 'DNMT1 or DNMT3A altered'),
    5:  (PRAD, ['TP53'], 'TP53 altered, the platinum-sensitive anchor'),
    6:  (PRAD, ['BRCA1', 'BRCA2', 'ATM', 'CHEK2', 'PALB2', 'RAD51B',
                'RAD51C', 'RAD51D', 'BARD1', 'BRIP1', 'CDK12', 'FANCL'],
         'homologous-recombination repair gene altered (PROfound panel)'),
    7:  (BLCA, ['AURKA', 'AURKB'], 'AURKA or AURKB altered'),
    8:  (BLCA, ['ERCC2', 'ATM', 'BRCA1', 'BRCA2', 'RB1', 'FANCC'],
         'DNA-damage-response gene altered'),
    9:  (BLCA, ['PIK3CA'], 'PIK3CA altered'),
    10: (BLCA, ['FGFR2', 'FGFR3'], 'FGFR2 or FGFR3 altered'),
    11: (BLCA, ['NECTIN4'], 'NECTIN4 altered'),
    13: (BLCA, ['CDKN2A'], 'CDKN2A altered, the CDK4/6 anchor'),
    14: (KIRC, ['VHL'], 'VHL altered, the anchor for VEGFR-directed therapy'),
    15: (KIRC, ['EPAS1', 'VHL'], 'EPAS1 or VHL altered, the HIF2a anchor'),
    16: (KIRC, ['CDK4', 'CDK6', 'CCND1'], 'CDK4, CDK6 or CCND1 altered'),
}

# Rows with no cohort in The Cancer Genome Atlas. Each value stays as curated
# and is recorded here against the series the manuscript already cites.
CURATED = {
    12: ('No single-gene frequency; tumor mutational burden is a continuous '
         'measure, not an alteration count', 'TCGA BLCA (Nature 2014) [1]'),
    17: ('SMARCB1 loss defines renal medullary carcinoma and is the disease '
         'anchor, not an alteration of CXCR1 or CXCR2',
         'Msaouel Cancer Cell 2020 [9]'),
    18: ('SMARCB1 loss, disease anchor, not an alteration of EGFR',
         'Msaouel Cancer Cell 2020 [9]'),
    19: ('SMARCB1 loss, disease anchor, not an alteration of CEACAM1',
         'Msaouel Cancer Cell 2020 [9]'),
    20: ('Human papillomavirus-associated immune context, not a recurrent '
         'alteration of PDCD1 or CD274',
         'Chahoud Clin Cancer Res 2021 [10]; Aydin Nat Rev Urol 2020 [11]'),
    28: ('TP53 and RB1 co-alteration defines small-cell bladder cancer and is '
         'the disease anchor, not an alteration of CEACAM5',
         'Chang Clin Cancer Res 2018 [13]'),
    29: ('TP53 and RB1 co-alteration, disease anchor, not an alteration of '
         'SSTR2', 'Chang Clin Cancer Res 2018 [13]'),
    30: ('TP53 and RB1 co-alteration, disease anchor, not an alteration of '
         'PTGS1', 'Chang Clin Cancer Res 2018 [13]'),
}


def bin_of(pct):
    """Supplementary Methods binning; boundaries take the higher bin."""
    if pct is None:
        return None
    if pct > 30:
        return 3
    if pct >= 15:
        return 2
    if pct >= 5:
        return 1
    return 0


def _get(path, **kw):
    for attempt in range(4):
        try:
            r = requests.get(f'{API}{path}', timeout=45, **kw)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _post(path, payload, **kw):
    for attempt in range(4):
        try:
            r = requests.post(f'{API}{path}', json=payload, timeout=90, **kw)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


_ENTREZ = {}


def entrez(symbols):
    """Resolve HGNC symbols to Entrez ids, which the API keys everything on."""
    need = [s for s in symbols if s not in _ENTREZ]
    if need:
        got = _post('/genes/fetch?geneIdType=HUGO_GENE_SYMBOL', need)
        for g in (got or []):
            _ENTREZ[g['hugoGeneSymbol']] = g['entrezGeneId']
    return [_ENTREZ[s] for s in symbols if s in _ENTREZ]


_PROFILES, _LISTS = {}, {}


def profiles(study):
    if study not in _PROFILES:
        got = _get(f'/studies/{study}/molecular-profiles') or []
        _PROFILES[study] = {p['molecularProfileId']: p for p in got}
        _LISTS[study] = {s['sampleListId']: s
                         for s in (_get(f'/studies/{study}/sample-lists',
                                        params={'projection': 'DETAILED'}) or [])}
    return _PROFILES[study], _LISTS[study]


def altered_fraction(study, symbols):
    """Samples altered in any queried gene, over samples profiled for those
    alteration types. Mirrors what the cBioPortal OncoPrint reports."""
    prof, lists = profiles(study)
    ids = entrez(symbols)
    if not ids:
        return None, None, 'gene symbols did not resolve'
    mut = f'{study}_mutations'
    cna = f'{study}_gistic'
    sv = f'{study}_structural_variants'
    altered, denom, denom_list = set(), set(), ''

    seq_list = f'{study}_sequenced'
    cna_list = f'{study}_cna'
    # the denominator is the samples profiled for BOTH mutation and copy
    # number, which is the list cBioPortal itself uses when a query spans the
    # two; falling back to the sequenced list where a study has no such list
    for lid in (f'{study}_cnaseq', seq_list, f'{study}_all'):
        if lid in lists and (lists[lid].get('sampleIds') or []):
            denom = set(lists[lid]['sampleIds'])
            denom_list = lid
            break

    if mut in prof:
        got = _post(f'/molecular-profiles/{mut}/mutations/fetch',
                    {'entrezGeneIds': ids, 'sampleListId': seq_list},
                    params={'projection': 'ID'}) or []
        altered |= {m['sampleId'] for m in got}
    if sv in prof:
        got = _post('/structural-variant/fetch',
                    {'entrezGeneIds': ids,
                     'molecularProfileIds': [sv]}) or []
        altered |= {m['sampleId'] for m in got if m.get('sampleId')}
    if cna in prof:
        got = _post(f'/molecular-profiles/{cna}/discrete-copy-number/fetch',
                    {'entrezGeneIds': ids, 'sampleListId': cna_list},
                    params={'discreteCopyNumberEventType': 'ALL',
                            'projection': 'ID'}) or []
        # GISTIC -2 is a deep deletion and +2 an amplification; -1 and +1 are
        # shallow and are not counted as alterations, as in the OncoPrint
        altered |= {c['sampleId'] for c in got
                    if c.get('alteration') in (-2, 2)}

    if not denom:
        return None, None, 'no sample list'
    pct = 100.0 * len(altered & denom) / len(denom)
    return round(pct, 1), len(denom), denom_list


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
    rows = []
    for _, r in defs.iterrows():
        n = int(r['N'])
        curated = int(r['genomic_score_curated'])
        rec = {'N': n, 'Context': r['Context'], 'Target': r['Target'],
               'G_curated': curated}
        if n in QUERY:
            study, genes, what = QUERY[n]
            pct, denom, err = altered_fraction(study, genes)
            rec.update({
                'source_type': 'recomputed from cBioPortal',
                'cohort': study,
                'cohort_n': denom,
                'genes_queried': ' '.join(genes),
                'what_the_value_counts': what,
                'frequency_pct': pct,
                'G_recomputed': bin_of(pct),
                'denominator_sample_list': err if err and err.startswith('no') else err,
            })
            print(f'{n:>3} {study.split("_")[0]:5s} {" ".join(genes)[:38]:40s}'
                  f' {"" if pct is None else f"{pct:5.1f}%"} '
                  f' curated={curated} recomputed={bin_of(pct)}')
        elif n in CURATED:
            what, cite = CURATED[n]
            rec.update({
                'source_type': 'curated from a published series; no TCGA cohort',
                'cohort': cite, 'cohort_n': None, 'genes_queried': '',
                'what_the_value_counts': what, 'frequency_pct': None,
                'G_recomputed': None, 'note': ''})
            print(f'{n:>3} curated  {what[:52]:54s} curated={curated}')
        else:
            rec.update({
                'source_type': 'not scored; the nominated gene is not '
                               'recurrently altered in this disease',
                'cohort': '', 'cohort_n': None, 'genes_queried': '',
                'what_the_value_counts': '', 'frequency_pct': None,
                'G_recomputed': 0, 'note': ''})
        rows.append(rec)

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)

    q = out[out['source_type'].str.startswith('recomputed')]
    ok = q[q['G_curated'] == q['G_recomputed']]
    print(f'\nrecomputed {len(q)} rows from cBioPortal; '
          f'{len(ok)} reproduce the curated bin, {len(q) - len(ok)} do not')
    for _, r in q[q['G_curated'] != q['G_recomputed']].iterrows():
        print(f'  N={int(r["N"]):>3} {str(r["Target"])[:30]:32s} '
              f'curated {r["G_curated"]} -> recomputed {r["G_recomputed"]} '
              f'({r["frequency_pct"]}%)')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()

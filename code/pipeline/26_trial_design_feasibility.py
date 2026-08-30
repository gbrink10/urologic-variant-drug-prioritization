"""Design-feasibility simulation for the two surviving framework-novel candidates.

The manuscript asserts that dedicated biomarker-stratified registration trials are
infeasible in these diseases. This replaces the assertion with numbers: for each
candidate it computes the exact single-arm phase II design a conventional protocol
would require, then converts the required sample size into calendar years of
accrual using published incidence.

EVERY INCIDENCE FIGURE IS DERIVED FROM A CITED SOURCE. No value is assumed.

  Renal medullary carcinoma
    Haupt EC, Akinyemi O, Raju S, et al. Renal medullary carcinoma: a
    Surveillance, Epidemiology, and End Results (SEER) analysis. J Surg Res.
    2023;292:1-6. PMID 37567029.
      -> 100 patients identified in SEER 18 registries over 1996-2018 (23 years)
         = 4.35 cases/year observed. SEER 18 covers ~27.8% of the US population
         (NCI SEER program documentation), giving ~15.6 US cases/year.
      Note: SEER almost certainly under-ascertains RMC, since the diagnosis
      requires SMARCB1 loss and is historically misclassified as collecting-duct
      or urothelial carcinoma. This figure is therefore treated as a LOWER bound
      and a 2x sensitivity arm is run alongside it.

  Small-cell carcinoma of the urinary bladder
    Dores GM, Qubaiah O, Mody A, Ghabach B. A population-based study of incidence
    and patient survival of small cell carcinoma in the United States, 1992-2010.
    BMC Cancer. 2015;15:185. PMID 25885914.
      -> age-adjusted incidence rate for small cell carcinoma of the urinary
         bladder = 0.7-0.8 per million person-years.
      Applied to a US population of 335 million (US Census Bureau 2024 estimate)
      this gives 235-268 cases/year.

  NEUROD1-positive fraction of small-cell bladder cancer
    10 of 44 samples (22.7%) in GSE269750, as classified in this study.

Response-rate assumptions (p0, p1) are DESIGN PARAMETERS, not measured quantities:
p0 is the response rate below which the agent would not be worth pursuing and p1
the rate the trial is powered to detect. Because these are investigator choices
rather than literature values, the analysis is run across a grid of plausible
pairs rather than asserting one.

Designs implemented exactly:
  * A'Hern single-stage exact binomial design
  * Simon two-stage optimal (minimises E[N] under H0) and minimax (minimises max N)
Validated against the published Simon design for p0=0.05, p1=0.25, alpha=0.05,
beta=0.20 (n1=9, r1=0, n=17, r=2).

Writes: results/TRIAL_DESIGN_FEASIBILITY.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results' / 'TRIAL_DESIGN_FEASIBILITY.csv'

ALPHA, POWER, NMAX = 0.05, 0.80, 110

# ---- cited epidemiology ----------------------------------------------------
SEER18_COVERAGE = 0.278          # NCI SEER 18 share of the US population
US_POP_MILLIONS = 335            # US Census Bureau 2024 estimate

RMC_SEER_CASES, RMC_SEER_YEARS = 100, 23          # Haupt 2023, PMID 37567029
RMC_US_PER_YEAR = (RMC_SEER_CASES / RMC_SEER_YEARS) / SEER18_COVERAGE

SCBC_IR_LOW, SCBC_IR_HIGH = 0.7, 0.8              # Dores 2015, PMID 25885914
SCBC_US_LOW = SCBC_IR_LOW * US_POP_MILLIONS
SCBC_US_HIGH = SCBC_IR_HIGH * US_POP_MILLIONS
NEUROD1_FRACTION = 10 / 44                        # this study, GSE269750


def ahern(p0, p1, alpha=ALPHA, power=POWER, nmax=NMAX):
    for n in range(5, nmax + 1):
        r = int(binom.isf(alpha, n, p0)) + 1
        if r > n:
            continue
        if binom.sf(r - 1, n, p0) <= alpha and binom.sf(r - 1, n, p1) >= power:
            return {'n': n, 'r': r,
                    'alpha': float(binom.sf(r - 1, n, p0)),
                    'power': float(binom.sf(r - 1, n, p1))}
    return None


def simon(p0, p1, alpha=ALPHA, power=POWER, nmax=NMAX):
    """Exhaustive but bounded search; r is capped well above any plausible value."""
    best_opt, best_mm, mm_n = None, None, None
    for n in range(5, nmax + 1):
        if mm_n is not None and n > mm_n + 30:
            break
        rmax = min(n, int(n * max(p0, p1)) + 12)
        for n1 in range(1, n):
            n2 = n - n1
            pmf1_0 = binom.pmf(np.arange(n1 + 1), n1, p0)
            pmf1_1 = binom.pmf(np.arange(n1 + 1), n1, p1)
            for r1 in range(0, min(n1, rmax)):
                pet0 = binom.cdf(r1, n1, p0)
                if 1 - binom.cdf(r1, n1, p1) < power:
                    break                      # stage 1 alone cannot reach power
                for r in range(r1 + 1, rmax + 1):
                    x1 = np.arange(r1 + 1, n1 + 1)
                    if x1.size == 0:
                        continue
                    sf2_0 = binom.sf(r - x1, n2, p0)
                    a = float(np.dot(pmf1_0[x1], sf2_0))
                    if a > alpha:
                        continue
                    sf2_1 = binom.sf(r - x1, n2, p1)
                    b = float(np.dot(pmf1_1[x1], sf2_1))
                    if b < power:
                        continue
                    en0 = n1 + (1 - pet0) * n2
                    cand = {'n1': n1, 'r1': r1, 'n': n, 'r': r,
                            'EN_p0': round(en0, 1), 'PET_p0': round(float(pet0), 3),
                            'alpha': round(a, 4), 'power': round(b, 3)}
                    if best_opt is None or en0 < best_opt['EN_p0']:
                        best_opt = cand
                    if best_mm is None or n < best_mm['n']:
                        best_mm, mm_n = cand, n
    return best_opt, best_mm


opt, mm = simon(0.05, 0.25)
match = (opt['n1'], opt['r1'], opt['n'], opt['r']) == (9, 0, 17, 2)
print("validation vs published Simon optimal design (p0=0.05, p1=0.25):")
print(f"  computed n1={opt['n1']} r1={opt['r1']} n={opt['n']} r={opt['r']} "
      f"EN={opt['EN_p0']}  ->  {'MATCH' if match else 'CHECK'}")

# ---- scenarios -------------------------------------------------------------
SCENARIOS = [
    {'candidate': 'CXCR1/CXCR2 antagonist',
     'disease': 'renal medullary carcinoma',
     'incidence_arms': {
         'SEER-derived (Haupt 2023)': RMC_US_PER_YEAR,
         'SEER-derived x2 (under-ascertainment)': RMC_US_PER_YEAR * 2},
     'subtype_fraction': 1.0},
    {'candidate': '177Lu-DOTATATE',
     'disease': 'NEUROD1+ small-cell bladder cancer',
     'incidence_arms': {
         'IR 0.7/million (Dores 2015)': SCBC_US_LOW,
         'IR 0.8/million (Dores 2015)': SCBC_US_HIGH},
     'subtype_fraction': NEUROD1_FRACTION},
]
PAIRS = [(0.05, 0.25), (0.10, 0.30), (0.15, 0.35)]
ELIGIBLE = 0.50          # share with advanced disease and fit to enrol; stated assumption
CAPTURE = [0.05, 0.10, 0.25]

print(f"\nRMC:  {RMC_SEER_CASES} SEER cases / {RMC_SEER_YEARS} y / {SEER18_COVERAGE} "
      f"coverage = {RMC_US_PER_YEAR:.1f} US cases/year")
print(f"SCBC: {SCBC_IR_LOW}-{SCBC_IR_HIGH}/million x {US_POP_MILLIONS}M = "
      f"{SCBC_US_LOW:.0f}-{SCBC_US_HIGH:.0f}/year; NEUROD1+ fraction {NEUROD1_FRACTION:.3f} "
      f"= {SCBC_US_LOW*NEUROD1_FRACTION:.0f}-{SCBC_US_HIGH*NEUROD1_FRACTION:.0f}/year")

rows = []
for sc in SCENARIOS:
    print(f"\n=== {sc['candidate']} in {sc['disease']}")
    for p0, p1 in PAIRS:
        a = ahern(p0, p1)
        o, m = simon(p0, p1)
        print(f"  H0 {p0:.0%} vs H1 {p1:.0%}: A'Hern n={a['n']} (>= {a['r']} resp) | "
              f"Simon minimax n={m['n']} | Simon optimal n={o['n']} (stage1 {o['n1']}, "
              f"E[N|H0] {o['EN_p0']})")
        for arm, inc in sc['incidence_arms'].items():
            pool = inc * sc['subtype_fraction'] * ELIGIBLE
            for cap in CAPTURE:
                per_year = pool * cap
                for design, n in [("A'Hern", a['n']), ('Simon minimax', m['n']),
                                  ('Simon optimal', o['n'])]:
                    rows.append({
                        'candidate': sc['candidate'], 'disease': sc['disease'],
                        'p0': p0, 'p1': p1, 'design': design, 'required_n': n,
                        'incidence_arm': arm,
                        'us_cases_per_year': round(inc, 1),
                        'trial_eligible_per_year': round(pool, 1),
                        'capture_fraction': cap,
                        'accrued_per_year': round(per_year, 2),
                        'years_to_accrue': round(n / per_year, 1) if per_year else np.inf,
                    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print("\n" + "=" * 76)
print("YEARS TO ACCRUE - Simon optimal design, H0 5% vs H1 25% (RMC) / 10% vs 30% (SCBC)")
print("=" * 76)
for sc in SCENARIOS:
    p0 = 0.05 if 'CXCR' in sc['candidate'] else 0.10
    sub = df[(df['candidate'] == sc['candidate']) & (df['design'] == 'Simon optimal')
             & (df['p0'] == p0)]
    print(f"\n{sc['disease']}  (required n = {sub['required_n'].iloc[0]})")
    piv = sub.pivot_table(index='incidence_arm', columns='capture_fraction',
                          values='years_to_accrue')
    piv.columns = [f'{int(c*100)}% capture' for c in piv.columns]
    print(piv.to_string())
print(f"\nWrote {OUT}")

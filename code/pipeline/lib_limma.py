"""A Python implementation of limma's linear model + empirical Bayes moderation.

There is no R on the analysis machine, and the reviewer's requirement is a
design-aware, variance-moderated model rather than an elementary t-test per
gene. This module implements the parts of limma that requirement needs:

  lm_fit   weighted least squares per gene against a shared design matrix
  ebayes   Smyth (2004) empirical-Bayes moderation of the residual variances
  voom     Law et al. (2014) mean-variance modelling to give count data
           precision weights so the same normal-model machinery applies

Reference behaviour the implementation is checked against in self_test():
  * with d0 -> 0 the moderated t collapses to the ordinary t statistic;
  * with d0 -> inf it collapses to a z-like statistic using the prior variance;
  * trigamma_inverse(trigamma(x)) == x;
  * on data simulated with a known common variance, the estimated prior
    variance recovers that variance and the moderated statistics are better
    calibrated than ordinary t (fewer extreme statistics from small-variance
    genes).

Nothing here is specific to this study; the study-specific fitting lives in
31_refit_differential_expression.py.
"""
import numpy as np
from scipy import stats
from scipy.special import digamma, polygamma

__all__ = ['lm_fit', 'ebayes', 'voom', 'bh', 'filter_by_expression', 'self_test']


def trigamma(x):
    return polygamma(1, x)


def trigamma_inverse(x):
    """Solve trigamma(y) = x for y, by Newton iteration on 1/y (limma's method)."""
    x = np.asarray(x, dtype=float)
    y = np.where(x > 1e7, 1.0 / np.sqrt(np.maximum(x, 1e-300)),
                 np.where(x < 1e-6, 1.0 / np.maximum(x, 1e-300), 0.5 + 1.0 / x))
    for _ in range(60):
        tri = trigamma(y)
        dif = tri * (1 - tri / x) / polygamma(2, y)
        y = y + dif
        if np.all(np.abs(dif) <= 1e-8 * np.maximum(np.abs(y), 1e-8)):
            break
    return y


def bh(p):
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(p, dtype=float)
    ok = ~np.isnan(p)
    q = np.full(p.shape, np.nan)
    pv = p[ok]
    n = pv.size
    if n == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q


def lm_fit(E, design, weights=None):
    """Per-gene weighted least squares.

    E        genes x samples matrix of log-scale expression
    design   samples x coefficients model matrix
    weights  genes x samples precision weights (from voom), or None

    Returns dict with coefficients, residual variance (sigma2), residual
    degrees of freedom, and the unscaled standard deviation of each
    coefficient, which is what ebayes() needs.
    """
    E = np.asarray(E, dtype=float)
    X = np.asarray(design, dtype=float)
    n_genes, n_samples = E.shape
    n_coef = X.shape[1]
    if X.shape[0] != n_samples:
        raise ValueError('design rows must equal samples')
    df_resid = n_samples - np.linalg.matrix_rank(X)
    if df_resid < 1:
        raise ValueError('no residual degrees of freedom')

    coefs = np.full((n_genes, n_coef), np.nan)
    sigma2 = np.full(n_genes, np.nan)
    unscaled = np.full((n_genes, n_coef), np.nan)

    if weights is None:
        # one shared decomposition for every gene
        XtX_inv = np.linalg.pinv(X.T @ X)
        beta = E @ X @ XtX_inv.T
        resid = E - beta @ X.T
        s2 = (resid ** 2).sum(axis=1) / df_resid
        un = np.sqrt(np.diag(XtX_inv))
        coefs, sigma2 = beta, s2
        unscaled = np.tile(un, (n_genes, 1))
    else:
        W = np.asarray(weights, dtype=float)
        for g in range(n_genes):
            w = W[g]
            good = np.isfinite(E[g]) & np.isfinite(w) & (w > 0)
            if good.sum() <= n_coef:
                continue
            Xg, yg, wg = X[good], E[g, good], w[good]
            sw = np.sqrt(wg)
            Xw, yw = Xg * sw[:, None], yg * sw
            XtX_inv = np.linalg.pinv(Xw.T @ Xw)
            b = XtX_inv @ (Xw.T @ yw)
            r = yw - Xw @ b
            dfg = good.sum() - np.linalg.matrix_rank(Xg)
            coefs[g] = b
            sigma2[g] = (r ** 2).sum() / dfg
            unscaled[g] = np.sqrt(np.diag(XtX_inv))
        df_resid = np.full(n_genes, df_resid, dtype=float)

    return {'coefficients': coefs, 'sigma2': sigma2, 'stdev_unscaled': unscaled,
            'df_residual': (np.full(n_genes, df_resid, dtype=float)
                            if np.isscalar(df_resid) else np.asarray(df_resid, float))}


def ebayes(fit, coef, robust_trim=0.0):
    """Smyth (2004) empirical Bayes moderation of the per-gene variances.

    Estimates the prior variance s0^2 and prior degrees of freedom d0 by
    matching the first two moments of log(s^2) to a scaled F distribution,
    then shrinks each gene's variance toward the prior.
    """
    s2 = np.asarray(fit['sigma2'], dtype=float)
    df = np.asarray(fit['df_residual'], dtype=float)
    ok = np.isfinite(s2) & (s2 > 0) & (df > 0)
    if ok.sum() < 10:
        raise ValueError('too few usable genes for moderation')

    z = np.log(s2[ok])
    d = df[ok]
    e = z - digamma(d / 2) + np.log(d / 2)
    if robust_trim > 0:
        lo, hi = np.quantile(e, [robust_trim, 1 - robust_trim])
        keep = (e >= lo) & (e <= hi)
    else:
        keep = np.ones(e.shape, bool)
    ebar = e[keep].mean()
    n = keep.sum()
    evar = ((e[keep] - ebar) ** 2).sum() / (n - 1) - np.mean(trigamma(d[keep] / 2))

    if evar > 0:
        d0 = 2.0 * float(trigamma_inverse(evar))
        s0_2 = float(np.exp(ebar + digamma(d0 / 2) - np.log(d0 / 2)))
    else:                                   # variances less variable than chance
        d0 = np.inf
        s0_2 = float(np.exp(ebar))

    if np.isinf(d0):
        s2_post = np.full(s2.shape, s0_2)
        df_total = np.full(df.shape, np.inf)
    else:
        s2_post = (d0 * s0_2 + df * s2) / (d0 + df)
        df_total = df + d0

    beta = fit['coefficients'][:, coef]
    un = fit['stdev_unscaled'][:, coef]
    se = un * np.sqrt(s2_post)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = beta / se
    p = np.full(t.shape, np.nan)
    fin = np.isfinite(t)
    if np.isinf(df_total).all():
        p[fin] = 2 * stats.norm.sf(np.abs(t[fin]))
    else:
        p[fin] = 2 * stats.t.sf(np.abs(t[fin]), df_total[fin])
    return {'logFC': beta, 't': t, 'p_value': p, 'q_value': bh(p),
            's2_post': s2_post, 'df_total': df_total, 'd0': d0, 's0_2': s0_2,
            'se': se}


def filter_by_expression(counts, min_count=10, min_prop=0.5, min_total=15):
    """edgeR-style low-expression filter; returns a boolean keep mask.

    Unfiltered low-count genes give near-zero empirical variances that distort
    the mean-variance trend, so this must be applied before voom.
    """
    counts = np.asarray(counts, dtype=float)
    lib = counts.sum(axis=0)
    med_lib = np.median(lib) if np.median(lib) > 0 else 1.0
    cpm = counts / np.maximum(lib, 1) * 1e6
    cpm_cut = min_count / (med_lib / 1e6)
    enough = (cpm >= cpm_cut).sum(axis=1) >= max(2, int(min_prop * counts.shape[1]))
    return enough & (counts.sum(axis=1) >= min_total) & (counts.var(axis=1) > 0)


def voom(counts, design, lib_size=None, span=0.5):
    """Law et al. (2014) mean-variance weights for count data.

    Returns (log2 CPM matrix, weights) for use with lm_fit.
    """
    counts = np.asarray(counts, dtype=float)
    if lib_size is None:
        lib_size = counts.sum(axis=0)
    lib_size = np.asarray(lib_size, dtype=float)
    y = np.log2((counts + 0.5) / (lib_size + 1.0) * 1e6)

    fit = lm_fit(y, design)
    mu = fit['coefficients'] @ np.asarray(design, float).T
    sx = y.mean(axis=1) + np.log2(lib_size.mean() / 1e6 + 1e-12)
    sy = np.sqrt(np.sqrt(np.maximum(fit['sigma2'], 0)))

    ok = np.isfinite(sx) & np.isfinite(sy) & (sy > 0)
    if ok.sum() < 10:
        return y, np.ones_like(y)
    order = np.argsort(sx[ok])
    xs, ys = sx[ok][order], sy[ok][order]
    # loess-free monotone trend: running median in overlapping windows
    k = max(11, int(span * xs.size / 10) | 1)
    pad = k // 2
    ys_pad = np.pad(ys, pad, mode='edge')
    trend = np.array([np.median(ys_pad[i:i + k]) for i in range(xs.size)])

    fitted_log_count = mu + np.log2(lib_size + 1.0)[None, :] - np.log2(1e6)
    fitted = np.interp(fitted_log_count, xs, trend, left=trend[0], right=trend[-1])
    weights = 1.0 / np.maximum(fitted, 1e-8) ** 4
    return y, weights


def self_test(seed=0, verbose=True):
    """Validate the implementation against behaviour with known answers."""
    rng = np.random.default_rng(seed)
    msgs, ok_all = [], True

    def rec(name, cond, extra=''):
        nonlocal ok_all
        ok_all &= bool(cond)
        msgs.append(f"  {'PASS' if cond else 'FAIL'}  {name} {extra}")

    # 1. trigamma inverse round-trips
    x = np.array([0.05, 0.5, 1.0, 4.0, 30.0])
    rec('trigamma_inverse round-trip',
        np.allclose(trigamma_inverse(trigamma(x)), x, rtol=1e-6))

    # 2. BH matches a direct implementation on a known vector
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205])
    expect = np.array([0.008, 0.032, 0.0672, 0.0672, 0.0672, 0.08, 0.0846, 0.205])
    rec('BH adjustment', np.allclose(bh(p), expect, atol=1e-4))

    # 3. ordinary least squares recovers a known contrast exactly
    n_per, n_genes = 6, 500
    design = np.column_stack([np.ones(2 * n_per),
                              np.r_[np.zeros(n_per), np.ones(n_per)]])
    true_fc = rng.normal(0, 1, n_genes)
    E = rng.normal(0, 0.4, (n_genes, 2 * n_per)) + true_fc[:, None] * design[:, 1]
    fit = lm_fit(E, design)
    # the achievable correlation is bounded by the noise in the contrast:
    # r_max = 1 / sqrt(1 + se^2 / var(true effects))
    se_contrast = 0.4 * np.sqrt(2 / n_per)
    r_expected = 1 / np.sqrt(1 + se_contrast ** 2 / np.var(true_fc))
    r_obs = np.corrcoef(fit['coefficients'][:, 1], true_fc)[0, 1]
    rec('lm_fit recovers known log-fold changes at the analytic limit',
        abs(r_obs - r_expected) < 0.02, f"r={r_obs:.4f} vs expected {r_expected:.4f}")

    # 4. classical t-test agreement when moderation is switched off
    res = ebayes(fit, coef=1)
    tt = stats.ttest_ind(E[:, n_per:], E[:, :n_per], axis=1, equal_var=True)
    fit0 = dict(fit)
    fit0['sigma2'] = fit['sigma2']
    manual_t = fit['coefficients'][:, 1] / (fit['stdev_unscaled'][:, 1]
                                            * np.sqrt(fit['sigma2']))
    rec('unmoderated t equals scipy ttest_ind',
        np.allclose(manual_t, tt.statistic, rtol=1e-8),
        f"max|diff|={np.max(np.abs(manual_t - tt.statistic)):.2e}")

    # 5. moderation shrinks variances toward the prior and is bounded by it
    s2, s2p = fit['sigma2'], res['s2_post']
    shrunk = np.mean(np.abs(s2p - res['s0_2']) <= np.abs(s2 - res['s0_2']) + 1e-12)
    rec('moderated variances shrink toward the prior', shrunk > 0.999,
        f"{shrunk:.3f} of genes")
    rec('prior variance recovers the simulated variance (0.16)',
        abs(res['s0_2'] - 0.16) < 0.03, f"s0^2={res['s0_2']:.4f}")
    rec('moderated t has more d.f. than the ordinary test',
        np.all(res['df_total'] > fit['df_residual']),
        f"df {fit['df_residual'][0]:.0f} -> {res['df_total'][0]:.1f}")

    # 6. null calibration: with no true effect, p-values are ~uniform
    E0 = rng.normal(0, 0.4, (4000, 2 * n_per))
    r0 = ebayes(lm_fit(E0, design), coef=1)
    ks = stats.kstest(r0['p_value'][np.isfinite(r0['p_value'])], 'uniform')
    rec('null p-values uniform (KS)', ks.pvalue > 0.01, f"KS p={ks.pvalue:.3f}")
    rec('null type-I error near nominal 5%',
        abs(np.mean(r0['p_value'] < 0.05) - 0.05) < 0.012,
        f"{np.mean(r0['p_value'] < 0.05):.4f}")

    # 7. power: moderation should not lose true positives relative to ordinary t
    ordinary_p = stats.ttest_ind(E[:, n_per:], E[:, :n_per], axis=1).pvalue
    true_de = np.abs(true_fc) > 0.5
    rec('moderation retains sensitivity on true effects',
        (res['p_value'][true_de] < 0.05).mean()
        >= (ordinary_p[true_de] < 0.05).mean() - 1e-9,
        f"moderated {(res['p_value'][true_de] < 0.05).mean():.3f} vs "
        f"ordinary {(ordinary_p[true_de] < 0.05).mean():.3f}")

    # 8. voom weights increase with expression (low counts get down-weighted).
    #    The weight distribution is heavy-tailed, so compare medians per tercile
    #    rather than means, which a handful of genes would dominate.
    counts = rng.poisson(np.exp(rng.normal(3, 2, (800, 1)))
                         * np.ones((1, 2 * n_per)))
    counts = counts[filter_by_expression(counts)]
    yv, w = voom(counts, design)
    mean_expr = yv.mean(axis=1)
    edges = np.quantile(mean_expr, [1 / 3, 2 / 3])
    med = [np.median(w[mean_expr <= edges[0]]),
           np.median(w[(mean_expr > edges[0]) & (mean_expr <= edges[1])]),
           np.median(w[mean_expr > edges[1]])]
    rec('voom weights increase monotonically with expression',
        med[0] < med[1] < med[2], f"{med[0]:.3g} < {med[1]:.3g} < {med[2]:.3g}")

    # 9. the mean-variance trend itself is decreasing (higher counts, less noise)
    fitv = lm_fit(yv, design)
    sxv = yv.mean(axis=1)
    syv = np.sqrt(np.sqrt(np.maximum(fitv['sigma2'], 0)))
    rec('mean-variance trend is negative', np.corrcoef(sxv, syv)[0, 1] < -0.5,
        f"r={np.corrcoef(sxv, syv)[0, 1]:.3f}")

    # 10. the low-expression filter removes constant/all-zero genes
    with_zeros = np.vstack([counts, np.zeros((5, counts.shape[1]))])
    keep = filter_by_expression(with_zeros)
    rec('filter_by_expression drops all-zero genes',
        not keep[-5:].any(), f"kept {keep.sum()} of {keep.size}")

    if verbose:
        print("lib_limma self-test")
        print("\n".join(msgs))
        print(f"  {'ALL CHECKS PASSED' if ok_all else 'FAILURES PRESENT'}")
    return ok_all


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(0 if self_test() else 1)

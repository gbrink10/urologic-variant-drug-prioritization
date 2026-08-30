"""Shared gene-symbol normalisation against the HGNC legacy -> current map.

Used by every enrichment and scoring step so that a gene renamed since the
platform was designed (IL8 -> CXCL8, WHSC1 -> NSD2) is not silently dropped from
the pathway it belongs to.
"""
from pathlib import Path
import pandas as pd

_MAP = None


def load_map():
    global _MAP
    if _MAP is None:
        p = Path(__file__).resolve().parents[2] / 'data' / 'hgnc_symbol_map.csv'
        m = pd.read_csv(p)
        _MAP = dict(zip(m['legacy_symbol'].astype(str).str.upper(),
                        m['current_symbol'].astype(str).str.upper()))
    return _MAP


def normalize(values):
    """Map a sequence of symbols to current HGNC symbols (upper case)."""
    m = load_map()
    s = pd.Series(list(values), dtype=object).astype(str).str.strip().str.upper()
    return s.map(lambda g: m.get(g, g))


_ENS = None


def ensembl_map():
    """Ensembl gene id -> current HGNC symbol, from the HGNC complete set."""
    global _ENS
    if _ENS is None:
        p = Path(__file__).resolve().parents[2] / 'data' / 'hgnc_complete_set.txt'
        h = pd.read_csv(p, sep='	', low_memory=False,
                        usecols=['symbol', 'ensembl_gene_id'])
        h = h.dropna(subset=['ensembl_gene_id'])
        _ENS = dict(zip(h['ensembl_gene_id'].astype(str).str.strip(),
                        h['symbol'].astype(str).str.upper()))
    return _ENS


def to_symbols(values):
    """Normalise a mix of Ensembl ids and gene symbols to current symbols."""
    ens = ensembl_map()
    s = pd.Series(list(values), dtype=object).astype(str).str.strip()
    base = s.str.replace(r'\.\d+$', '', regex=True)
    out = base.map(lambda g: ens.get(g)) if base.str.startswith('ENSG').any() else None
    if out is None:
        return normalize(s)
    return out.fillna(pd.Series(normalize(s).values, index=out.index))

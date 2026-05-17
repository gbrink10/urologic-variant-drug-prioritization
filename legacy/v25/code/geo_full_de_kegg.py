#!/usr/bin/env python
"""
Full DE analysis (all genes) + KEGG pathway enrichment across 5 GEO datasets.
Outputs: FULL_DE_RESULTS.csv, KEGG_ENRICHMENT.csv
"""
import gzip, math, statistics, csv, re, os
from pathlib import Path

BASE = Path(r"C:/Users/garre/OneDrive/Books_Uro/Desktop/VALIDATION_PACKAGE_Bladder_Cancer_Study")
DOWNLOADS = BASE / "1_FINALIZED_PAPERS"
RAW = BASE / "4_VALIDATION_DOCUMENTS" / "STRICT28_RAW_DOWNLOADS"
OUT = BASE

# ── helpers ──────────────────────────────────────────────────────────────────
def mean(v): return sum(v)/len(v) if v else 0.0

def safe_log2(a, b, eps=1e-9):
    return math.log2(max(b, eps) / max(a, eps))

try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

def welch_t(a, b):
    """Welch two-sample t-test with Welch-Satterthwaite df.
    Returns (t-statistic, two-sided p-value from the t-distribution survival function).
    Uses scipy.stats.t.sf when available; otherwise falls back to the
    normal approximation for environments without scipy.
    """
    if len(a) < 2 or len(b) < 2: return 0.0, 1.0
    n1, n2 = len(a), len(b)
    m1, m2 = mean(a), mean(b)
    v1 = statistics.variance(a); v2 = statistics.variance(b)
    se2 = v1/n1 + v2/n2
    if se2 < 1e-30: return 0.0, 1.0
    se = math.sqrt(se2)
    t = (m1 - m2) / se
    df = se2**2 / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1))
    if _HAS_SCIPY:
        # Two-sided p from the actual t-distribution with Welch-Satterthwaite df.
        p = 2.0 * _scipy_stats.t.sf(abs(t), df)
    else:
        # Fallback: normal approximation (only used if scipy is unavailable).
        x = abs(t)
        t2 = 1/(1+0.2316419*x)
        poly = t2*(0.319381530 + t2*(-0.356563782 + t2*(1.781477937 + t2*(-1.821255978 + t2*1.330274429))))
        p = 2 * 0.3989422803 * math.exp(-0.5*x*x) * poly
    return t, max(p, 1e-10)

def read_gz_lines(path):
    with gzip.open(str(path), 'rt', encoding='utf-8', errors='replace') as f:
        return f.readlines()

# ── KEGG pathway gene sets ────────────────────────────────────────────────────
KEGG = {
    "Cell_Cycle": {
        "CDK1","CDK2","CDK4","CDK6","CDKN1A","CDKN2A","CDKN2B","RB1","E2F1","E2F2","E2F3",
        "CCND1","CCND2","CCND3","CCNE1","CCNE2","CCNA1","CCNA2","CCNB1","CCNB2",
        "AURKA","AURKB","AURKC","BUB1","BUB1B","BUB3","MAD2L1","MAD2L2",
        "PLK1","PLK2","PLK3","CDC20","CDC25A","CDC25B","CDC25C","WEE1",
        "MCM2","MCM3","MCM4","MCM5","MCM6","MCM7","PCNA","RFC1",
        "CHEK1","CHEK2","ATM","ATR","TP53","PRKDC","H2AFX",
        "SKP2","FBXW7","RBL1","RBL2","TFDP1","TFDP2",
    },
    "PI3K_AKT": {
        "PIK3CA","PIK3CB","PIK3CD","PIK3CG","PIK3R1","PIK3R2","PIK3R3",
        "AKT1","AKT2","AKT3","PTEN","MTOR","RPTOR","MLST8","RICTOR",
        "RPS6KB1","RPS6KB2","EIF4EBP1","RPS6","GSK3A","GSK3B",
        "MDM2","MDM4","TP53","BCL2","BCL2L1","MCL1","BAD",
        "VEGFA","VEGFB","VEGFC","KDR","FLT1","FLT4",
        "FGFR1","FGFR2","FGFR3","FGFR4","EGFR","ERBB2","ERBB3","ERBB4",
        "PDGFRA","PDGFRB","KIT","MET","IGF1R","INSR","IRS1","IRS2",
        "GRB2","SOS1","SOS2","HRAS","KRAS","NRAS","RAF1","BRAF",
        "MAP2K1","MAP2K2","MAPK1","MAPK3","TSC1","TSC2","RHEB",
    },
    "HIF1_Signaling": {
        "HIF1A","EPAS1","ARNT","VHL","EGLN1","EGLN2","EGLN3",
        "VEGFA","VEGFB","VEGFC","KDR","FLT1","NRP1","NRP2",
        "HK1","HK2","LDHA","LDHB","ALDOA","ENO1","GAPDH","PFKL","PFKM","PGK1","PKM",
        "SLC2A1","SLC2A3","CA9","CA12","BNIP3","BNIP3L",
        "EPO","TGFA","HMOX1","NOS2","NOS3","ADM","SERPINE1",
        "CDKN1A","MYC","TWIST1","SNAI1","CTGF",
    },
    "VEGF_Signaling": {
        "VEGFA","VEGFB","VEGFC","VEGFD","PGF","KDR","FLT1","FLT4","NRP1","NRP2",
        "PLCG1","PLCG2","PIK3CA","PIK3R1","AKT1","AKT2","AKT3",
        "MAPK1","MAPK3","MAP2K1","RAF1","HRAS","KRAS",
        "PTK2","SRC","YES1","FYN","PXNVCL1",
        "PTPN11","GRB2","SHC1","NCK1","NCK2",
        "KRAS","HRAS","NRAS","ARAF",
        "CASP9","CASP3","BCL2","BAD",
        "RAC1","CDC42","PAK1","PAK2","LIMK1","LIMK2","CFL1","CFL2",
    },
    "p53_Signaling": {
        "TP53","MDM2","MDM4","CDKN1A","CDKN2A","GADD45A","GADD45B","GADD45G",
        "BAX","BBC3","PMAIP1","BID","CASP3","CASP6","CASP7","CASP8","CASP9",
        "CHEK1","CHEK2","ATM","ATR","RRM2","RRM2B","PCNA","POLD1",
        "CCNG1","CCNG2","SFN","PTEN","TSC2","SERPINE1","TNFRSF10B","TNFRSF10A",
        "FAS","RPRM","STEAP3","IGFBP3","PERP",
    },
    "DNA_Repair_HR": {
        "BRCA1","BRCA2","PALB2","RAD51","RAD51C","RAD51D","XRCC2","XRCC3",
        "ATM","ATR","NBN","MRE11A","MRE11","RAD50","RPA1","RPA2","RPA3",
        "BARD1","BRIP1","FANCA","FANCC","FANCD2","FANCI","FANCJ","FANCL","FANCM",
        "CHEK1","CHEK2","TOPBP1","ATRIP","MDC1","H2AFX","PARP1","PARP2",
        "RAD17","RAD9A","HUS1","RFC1","RFC2","RFC3","RFC4","RFC5",
    },
    "Epigenetic_Regulation": {
        "EZH2","EED","SUZ12","RBBP4","RBBP7","BMI1","RING1","RNF2",
        "DNMT1","DNMT3A","DNMT3B","DNMT3L","TET1","TET2","TET3",
        "KDM1A","KDM2B","KDM5B","KDM5C","KDM6A","KDM6B",
        "HDAC1","HDAC2","HDAC3","HDAC4","HDAC5","HDAC6","HDAC7","HDAC8",
        "SETD2","SETD1A","SETD1B","KMT2A","KMT2B","KMT2C","KMT2D",
        "EP300","CREBBP","HAT1","KAT2A","KAT2B","KAT5","KAT6A","KAT8",
        "SMARCA4","SMARCB1","SMARCC1","SMARCC2","ARID1A","ARID1B",
    },
    "Apoptosis_BCL2": {
        "BCL2","BCL2L1","BCL2L2","BCL2L10","MCL1","BCL2A1",
        "BAX","BAK1","BOK","BAD","BID","PMAIP1","BBC3","HRK","BCL2L11",
        "CASP3","CASP6","CASP7","CASP8","CASP9","CASP10",
        "APAF1","CYCS","DIABLO","HTRA2","XIAP","BIRC2","BIRC3",
        "FAS","FASLG","TNFRSF10A","TNFRSF10B","TRADD","FADD","TRAF2",
        "TP53","MDM2","PUMA","NOXA",
    },
}

# ── Ensembl→Symbol map (from previous analysis) ──────────────────────────────
ENSG_SYM = {
    "ENSG00000171862":"PTEN","ENSG00000141510":"TP53","ENSG00000012048":"BRCA1",
    "ENSG00000139618":"BRCA2","ENSG00000196712":"NF1","ENSG00000134057":"CCNB1",
    "ENSG00000105173":"CCNE1","ENSG00000110092":"CCND1","ENSG00000129514":"FOXA1",
    "ENSG00000125845":"FOXA2","ENSG00000125846":"FOXA2","ENSG00000171121":"KCNMB3",
    "ENSG00000117399":"CDC20","ENSG00000166033":"HTRA1","ENSG00000085563":"ABCB1",
    "ENSG00000177606":"JUN","ENSG00000136997":"MYC","ENSG00000116478":"HDAC1",
    "ENSG00000101033":"PARP4","ENSG00000139618":"BRCA2","ENSG00000171862":"PTEN",
    "ENSG00000171862":"PTEN","ENSG00000012048":"BRCA1",
    "ENSG00000181449":"SOX2","ENSG00000147889":"CDKN2A","ENSG00000105810":"CDK6",
    "ENSG00000135446":"CDK4","ENSG00000123374":"CDK2","ENSG00000170312":"CDK1",
    "ENSG00000159216":"RUNX1","ENSG00000101412":"E2F1","ENSG00000197102":"DZIP3",
    "ENSG00000163251":"FZD5","ENSG00000073111":"MCM2","ENSG00000082258":"CCNT2",
    "ENSG00000153879":"CEBPG","ENSG00000166033":"HTRA1","ENSG00000065978":"YBX1",
    "ENSG00000188906":"LZTR1","ENSG00000141736":"ERBB2","ENSG00000146648":"EGFR",
    "ENSG00000157764":"BRAF","ENSG00000133703":"KRAS","ENSG00000174775":"HRAS",
    "ENSG00000213281":"NRAS","ENSG00000067606":"PRKCZ","ENSG00000168484":"SFTPC",
    "ENSG00000145675":"PIK3R1","ENSG00000121879":"PIK3CA","ENSG00000085276":"MECOM",
    "ENSG00000117461":"PIK3R3","ENSG00000105851":"PIK3CG","ENSG00000116285":"ERRFI1",
    "ENSG00000173153":"ESRRA","ENSG00000130164":"LDLR","ENSG00000102144":"PGK1",
    "ENSG00000114268":"PFKFB2","ENSG00000159322":"ADPGK","ENSG00000111640":"GAPDH",
    "ENSG00000156531":"PHF6","ENSG00000134283":"HK1","ENSG00000159399":"HK2",
    "ENSG00000100604":"CHGA","ENSG00000126562":"WNK4","ENSG00000183454":"GRIN2A",
    "ENSG00000185386":"MAPK11","ENSG00000107643":"MAPK8","ENSG00000100030":"MAPK1",
    "ENSG00000102882":"MAPK3","ENSG00000067048":"DDX3Y","ENSG00000129824":"RPS4Y1",
    "ENSG00000198692":"EIF1AY","ENSG00000150093":"ITGB1","ENSG00000116044":"NFE2L2",
    "ENSG00000165025":"SYK","ENSG00000197122":"SRC","ENSG00000128052":"KDR",
    "ENSG00000102755":"FLT1","ENSG00000112715":"VEGFA","ENSG00000150630":"VEGFC",
    "ENSG00000119738":"EPAS1","ENSG00000100644":"HIF1A","ENSG00000134086":"VHL",
    "ENSG00000070669":"ASNS","ENSG00000197142":"ACSL5","ENSG00000133661":"SLC1A5",
    "ENSG00000135932":"CAD","ENSG00000165525":"NEMF","ENSG00000136504":"KAT7",
    "ENSG00000065613":"SLK","ENSG00000129055":"ANAMORSIN","ENSG00000142178":"SLC6A6",
    "ENSG00000122025":"FLT3","ENSG00000143570":"SLC9A3R1","ENSG00000196576":"PLXNB2",
    "ENSG00000113296":"THBS3","ENSG00000186532":"SLCO4A1","ENSG00000149294":"NCAM1",
    "ENSG00000006047":"YAP1","ENSG00000051382":"PIK3CB","ENSG00000105647":"PIK3R2",
    "ENSG00000171094":"ALK","ENSG00000075420":"FNBP4","ENSG00000138798":"EGF",
    "ENSG00000109320":"NFKB1","ENSG00000134070":"IRAK2","ENSG00000006468":"ETV1",
    "ENSG00000178568":"ERBB4","ENSG00000065361":"ERBB3","ENSG00000184389":"AGAP3",
    "ENSG00000169855":"ROBO3","ENSG00000109339":"MAPK10","ENSG00000108984":"MAP2K6",
    "ENSG00000167264":"DUS2","ENSG00000168071":"CCDC12","ENSG00000088986":"DYNLL1",
    "ENSG00000163283":"ALPP","ENSG00000101811":"CSTF2","ENSG00000107201":"DDX58",
    "ENSG00000126266":"PURB","ENSG00000132703":"APOBEC3F","ENSG00000100345":"MYH9",
    "ENSG00000181472":"RB1","ENSG00000175793":"SFN","ENSG00000183579":"ZNRF3",
    "ENSG00000128191":"DAGLA","ENSG00000026025":"VIM","ENSG00000115414":"FN1",
    "ENSG00000105976":"MET","ENSG00000149311":"ATM","ENSG00000175054":"ATR",
    "ENSG00000139618":"BRCA2","ENSG00000116062":"MSH6","ENSG00000060491":"OGFR",
    "ENSG00000140463":"BRD4","ENSG00000073282":"TP63","ENSG00000078237":"TIGAR",
    "ENSG00000141646":"SMAD4","ENSG00000171862":"PTEN","ENSG00000101134":"PSMB10",
    "ENSG00000143401":"ANP32A","ENSG00000198901":"PRC1","ENSG00000166033":"HTRA1",
    "ENSG00000073792":"IGF2R","ENSG00000074047":"GLI2","ENSG00000108055":"SMC3",
    "ENSG00000164976":"KCNK10","ENSG00000123560":"PLP1","ENSG00000116830":"TTR",
    "ENSG00000107485":"GATA3","ENSG00000106799":"TGFBR1","ENSG00000163513":"TGFBR2",
    "ENSG00000139644":"TMBIM6","ENSG00000175197":"DDIT3","ENSG00000196591":"HDAC2",
    "ENSG00000130816":"DNMT1","ENSG00000119772":"DNMT3A","ENSG00000007372":"PAX6",
    "ENSG00000171843":"MLLT3","ENSG00000101443":"WASH4P","ENSG00000276043":"WASH7P",
    "ENSG00000064601":"CTSA","ENSG00000166033":"HTRA1","ENSG00000108379":"WNT3",
    "ENSG00000125538":"IL1B","ENSG00000197601":"BCL2","ENSG00000171791":"BCL2",
    "ENSG00000107485":"GATA3","ENSG00000164659":"IKBKG","ENSG00000214041":"BCL2L1",
    "ENSG00000087086":"FTL","ENSG00000122786":"CALD1","ENSG00000076053":"RBX1",
    "ENSG00000116016":"EPAS1","ENSG00000163599":"CTLA4","ENSG00000168310":"IRF2",
    "ENSG00000100243":"SSFA2","ENSG00000149295":"MAP2K5","ENSG00000163545":"NUAK2",
    "ENSG00000120697":"ALG1","ENSG00000188042":"ARL4C","ENSG00000136205":"TNS3",
    "ENSG00000154556":"SORBS2","ENSG00000100156":"SLC16A10","ENSG00000135127":"CCDC80",
    "ENSG00000060327":"SNTG2","ENSG00000147041":"KCNQ5","ENSG00000148053":"NTRK2",
    "ENSG00000115738":"ID2","ENSG00000067955":"CBFB","ENSG00000088038":"CNOT3",
    "ENSG00000133805":"AMPD3","ENSG00000196565":"GNG12","ENSG00000109906":"ZBTB16",
    "ENSG00000116106":"EPHA4","ENSG00000135679":"MDM2","ENSG00000165699":"TSC1",
    "ENSG00000103197":"TSC2","ENSG00000175221":"MCL1","ENSG00000100644":"HIF1A",
    "ENSG00000116560":"SETD2","ENSG00000163737":"PBRM1","ENSG00000187210":"BAP1",
    "ENSG00000158528":"PPP1R9A","ENSG00000155380":"SLC16A1","ENSG00000157554":"ERG",
    "ENSG00000132965":"ALOX5AP","ENSG00000131238":"PON1","ENSG00000143514":"TP53BP1",
    "ENSG00000065361":"ERBB3","ENSG00000006025":"SPHK1","ENSG00000128422":"KRT17",
    "ENSG00000144724":"PTPRG","ENSG00000064012":"CASR","ENSG00000185515":"BRPF1",
    "ENSG00000157851":"DPPA5","ENSG00000196549":"MME","ENSG00000165905":"TMEFF2",
    "ENSG00000267534":"EZH2","ENSG00000106462":"EZH2","ENSG00000108379":"WNT3",
    "ENSG00000183971":"SMAD9","ENSG00000198732":"SAMD9L","ENSG00000169083":"AR",
}

# ── load full expression matrices ─────────────────────────────────────────────
def parse_rpkm_gse199274():
    """Returns dict: gene -> {sample: value}. All genes."""
    path = DOWNLOADS / "GSE199274_mr99-mr110_RPKM.txt.gz"
    lines = read_gz_lines(path)
    hdr = lines[0].strip().split("\t")
    samples = hdr[1:]
    data = {}
    for line in lines[1:]:
        parts = line.strip().split("\t")
        if len(parts) < 2: continue
        gene = parts[0].strip()
        try:
            vals = [float(x) for x in parts[1:len(samples)+1]]
        except: continue
        data[gene] = {samples[i]: vals[i] for i in range(len(vals))}
    return data, samples

def parse_tpm_gse216053():
    """Returns dict: ensembl_or_sym -> {sample: value}. Resolves symbol if possible."""
    path = DOWNLOADS / "GSE216053_TPM_PM154_decitabine.txt.gz"
    lines = read_gz_lines(path)
    hdr = lines[0].strip().split("\t")
    samples = hdr[1:]
    data = {}
    for line in lines[1:]:
        parts = line.strip().split("\t")
        if len(parts) < 2: continue
        raw_id = parts[0].strip().split(".")[0]  # strip version
        sym = ENSG_SYM.get(raw_id, raw_id)
        try:
            vals = [float(x) for x in parts[1:len(samples)+1]]
        except: continue
        data[sym] = {samples[i]: vals[i] for i in range(len(vals))}
    return data, samples

def parse_ncounter_gse130598():
    """Returns dict: gene->{label: value}, and two lists: tumor_labels, normal_labels."""
    path = RAW / "GSE130598" / "GSE130598_series_matrix.txt.gz"
    lines = read_gz_lines(path)
    titles, gsm_ids, tissue_types = [], [], []
    table_lines = []
    in_table = False
    for line in lines:
        if "!Sample_title" in line:
            parts = line.strip().split("\t")
            titles = [p.strip('"') for p in parts[1:]]
        if "!Sample_geo_accession" in line:
            parts = line.strip().split("\t")
            gsm_ids = [p.strip('"') for p in parts[1:]]
        if "tissue:" in line and "!Sample_characteristics" in line:
            parts = line.strip().split("\t")
            tissue_types = [p.strip('"').replace("tissue: ","").strip() for p in parts[1:]]
        if "series_matrix_table_begin" in line.lower() or "matrix_table_begin" in line.lower():
            in_table = True; continue
        if "series_matrix_table_end" in line.lower() or "matrix_table_end" in line.lower():
            in_table = False
        if in_table:
            table_lines.append(line.strip())
    if not table_lines: return {}, [], []
    raw_hdr = [h.strip('"') for h in table_lines[0].split("\t")]
    col_ids = raw_hdr[1:]  # GSM IDs from table header
    # build tissue label per column using GSM mapping
    gsm_to_tissue = {}
    if gsm_ids and tissue_types:
        for g, t in zip(gsm_ids, tissue_types):
            gsm_to_tissue[g] = t
    # build meaningful sample labels: use position-based tissue if available
    labels = []
    tumor_labels, normal_labels = [], []
    for i, col in enumerate(col_ids):
        tissue = gsm_to_tissue.get(col, "")
        if not tissue and titles and i < len(titles):
            tissue = "tumor" if "tumor" in titles[i].lower() else "normal"
        lbl = f"{tissue}_{i+1}" if tissue else f"sample_{i+1}"
        labels.append(lbl)
        if "tumor" in tissue.lower():
            tumor_labels.append(lbl)
        elif "normal" in tissue.lower() or "adjacent" in tissue.lower():
            normal_labels.append(lbl)
    data = {}
    for line in table_lines[1:]:
        parts = [p.strip('"') for p in line.strip().split("\t")]
        if len(parts) < 2: continue
        gene = parts[0].strip()
        try:
            vals = [float(x) for x in parts[1:len(labels)+1]]
        except: continue
        data[gene] = {labels[i]: vals[i] for i in range(len(vals))}
    return data, tumor_labels, normal_labels

def parse_htseq_gse143630():
    """Returns gene -> {sample: value}."""
    path = DOWNLOADS / "GSE143630_RCC_htseq_counts.txt.gz"
    lines = read_gz_lines(path)
    raw_hdr = lines[0].strip()
    sep = "\t" if "\t" in raw_hdr else " "
    hdr = [h.strip('"') for h in raw_hdr.split(sep)]
    samples = hdr[1:] if hdr[0] == "" else hdr[1:]
    data = {}
    for line in lines[1:]:
        parts = [p.strip('"') for p in line.strip().split(sep)]
        if len(parts) < 2: continue
        gene = parts[0].strip()
        if gene.startswith("__"): continue
        try:
            vals = [math.log2(float(x)+1) for x in parts[1:len(samples)+1]]
        except: continue
        data[gene] = {samples[i]: vals[i] for i in range(len(vals))}
    return data, samples

def parse_vst_gse157256():
    """Returns gene -> {sample: value}. Format: ENSGXXX.ver|SYMBOL val1 val2..."""
    path = DOWNLOADS / "GSE157256_VST_normalized.txt.gz"
    lines = read_gz_lines(path)
    raw_hdr = lines[0].strip()
    sep = "\t" if "\t" in raw_hdr else " "
    hdr = [h.strip('"') for h in raw_hdr.split(sep)]
    # detect value start: col0 = gene_id (ENSG|symbol or symbol), remaining = samples
    first_data = lines[1].strip().split(sep)
    try: float(first_data[1].strip('"')); val_start = 1
    except: val_start = 2
    samples = hdr[val_start:]
    data = {}
    for line in lines[1:]:
        parts = [p.strip('"') for p in line.strip().split(sep)]
        if len(parts) < val_start+1: continue
        raw_id = parts[0].strip()
        # extract symbol: if "ENSG...|SYMBOL" format, take SYMBOL part
        if "|" in raw_id:
            sym = raw_id.split("|")[-1].split(".")[0].strip()
        else:
            ensg = raw_id.split(".")[0]
            sym = ENSG_SYM.get(ensg, raw_id.split(".")[0])
        # col1 may also be duplicate gene id when val_start==2
        if not sym or sym.startswith("ENSG"):
            sym = raw_id
        try:
            vals = [float(x) for x in parts[val_start:val_start+len(samples)]]
        except: continue
        data[sym] = {samples[i]: vals[i] for i in range(len(vals))}
    return data, samples

# ── group definitions ─────────────────────────────────────────────────────────
def get_groups_199274(samples):
    """LKO controls vs shCXCR7"""
    lko = [s for s in samples if any(x in s for x in ["mr99","mr100","mr101","mr105","mr106","mr107"])]
    sh  = [s for s in samples if any(x in s for x in ["mr102","mr103","mr104","mr108","mr109","mr110"])]
    return lko, sh, "LKO_control", "shCXCR7"

def get_groups_216053(samples):
    ctrl = [s for s in samples if "control" in s.lower() or "ctrl" in s.lower()]
    trt  = [s for s in samples if "day14" in s.lower() or "decitabine" in s.lower() or "treated" in s.lower()]
    if not ctrl:
        ctrl = samples[:3]; trt = samples[3:]
    return ctrl, trt, "Control_NEPC", "Decitabine_D14"

def get_groups_130598(tumor_labels, normal_labels):
    return normal_labels, tumor_labels, "Normal_adjacent", "MIBC_tumor"

def get_groups_143630(samples):
    stageI  = [s for s in samples if s.startswith("T1") or "-T1" in s or "_T1" in s or s.startswith("1-") or "stage_1" in s.lower() or "stageI_" in s.lower()]
    stageII = [s for s in samples if s.startswith("T2") or "-T2" in s or "_T2" in s or s.startswith("2-") or "stage_2" in s.lower() or "stageII_" in s.lower()]
    if not stageI or not stageII:
        # split evenly
        n24 = len(samples)//2
        stageI = samples[:n24]; stageII = samples[n24:]
    return stageI, stageII, "ccRCC_StageI", "ccRCC_StageII"

def get_groups_157256(samples):
    normal = [s for s in samples if "normal" in s.lower() or "adj" in s.lower() or "norm" in s.lower()]
    tumor  = [s for s in samples if "tumor" in s.lower() or "met" in s.lower() or "primary" in s.lower()]
    if not normal or not tumor:
        normal = samples[:5]; tumor = samples[5:]
    return normal, tumor, "Normal_kidney", "Tumor_Metastasis"

# ── full DE analysis ──────────────────────────────────────────────────────────
def run_de(data, grp_a, grp_b, label_a, label_b, dataset, cancer):
    rows = []
    for gene, smap in data.items():
        va = [smap[s] for s in grp_a if s in smap]
        vb = [smap[s] for s in grp_b if s in smap]
        if len(va) < 2 or len(vb) < 2: continue
        ma, mb = mean(va), mean(vb)
        t, p = welch_t(va, vb)
        fc = safe_log2(ma, mb)
        rows.append({
            "dataset": dataset, "cancer": cancer,
            "gene": gene, "group_a": label_a, "group_b": label_b,
            "mean_a": round(ma,4), "mean_b": round(mb,4),
            "log2FC": round(fc,4), "t_stat": round(t,4), "p_value": round(p,6),
            "n_a": len(va), "n_b": len(vb),
        })
    return rows

# ── KEGG enrichment: hypergeometric test ─────────────────────────────────────
def logchoose(n, k):
    if k < 0 or k > n: return -math.inf
    return sum(math.log(n-i) - math.log(i+1) for i in range(k))

def hypergeom_pval(k, N, K, n):
    """P(X >= k) where X ~ Hypergeometric(N, K, n)"""
    if k == 0: return 1.0
    log_total = logchoose(N, n)
    p = 0.0
    for x in range(k, min(n, K)+1):
        lp = logchoose(K, x) + logchoose(N-K, n-x) - log_total
        p += math.exp(lp)
    return min(p, 1.0)

def compute_kegg_enrichment(de_rows):
    """Returns list of enrichment result rows."""
    # group by dataset+comparison
    by_ds = {}
    for r in de_rows:
        key = (r["dataset"], r["cancer"], r["group_a"], r["group_b"])
        by_ds.setdefault(key, []).append(r)

    results = []
    for (ds, cancer, ga, gb), rows in by_ds.items():
        genes_all = {r["gene"] for r in rows}
        N = len(genes_all)
        sig_up = {r["gene"] for r in rows if r["p_value"] < 0.05 and r["log2FC"] > 0.5}
        sig_dn = {r["gene"] for r in rows if r["p_value"] < 0.05 and r["log2FC"] < -0.5}
        sig_any = sig_up | sig_dn

        for pw_name, pw_genes in KEGG.items():
            # overlaps
            pw_in_ds = pw_genes & genes_all
            if len(pw_in_ds) < 3: continue
            K = len(pw_in_ds)
            n_sig = len(sig_any)
            k_sig = len(sig_any & pw_in_ds)
            k_up  = len(sig_up & pw_in_ds)
            k_dn  = len(sig_dn & pw_in_ds)

            p_any = hypergeom_pval(k_sig, N, K, n_sig) if n_sig > 0 else 1.0
            p_up  = hypergeom_pval(k_up,  N, K, len(sig_up)) if sig_up else 1.0

            expected = K * n_sig / N if N > 0 else 0
            odds = (k_sig / (n_sig - k_sig + 1e-9)) / (K / (N - K + 1e-9)) if n_sig > 0 else 1.0

            sig_pw_genes_list = sorted(sig_any & pw_in_ds)
            up_genes_list     = sorted(sig_up & pw_in_ds)

            results.append({
                "dataset": ds, "cancer": cancer, "comparison": f"{gb}_vs_{ga}",
                "pathway": pw_name, "N_tested": N, "K_in_pathway": K,
                "n_sig_DE": n_sig, "k_sig_in_pathway": k_sig,
                "k_upregulated": k_up, "k_downregulated": k_dn,
                "expected": round(expected, 2), "odds_ratio": round(odds, 3),
                "p_value_enrichment": round(p_any, 6),
                "p_value_upregulated": round(p_up, 6),
                "neg_log10_p": round(-math.log10(max(p_any, 1e-10)), 3),
                "sig_pathway_genes": ";".join(sig_pw_genes_list[:20]),
                "upregulated_pathway_genes": ";".join(up_genes_list[:20]),
            })
    return results

# ── main ──────────────────────────────────────────────────────────────────────
print("Loading GSE199274 RPKM...")
data199274, samp199274 = parse_rpkm_gse199274()
ga, gb, la, lb = get_groups_199274(samp199274)
print(f"  Groups: {la} n={len(ga)}, {lb} n={len(gb)}, genes={len(data199274)}")
de199274 = run_de(data199274, ga, gb, la, lb, "GSE199274", "NEPC")

print("Loading GSE216053 TPM...")
data216053, samp216053 = parse_tpm_gse216053()
ga, gb, la, lb = get_groups_216053(samp216053)
print(f"  Groups: {la} n={len(ga)}, {lb} n={len(gb)}, genes={len(data216053)}")
de216053 = run_de(data216053, ga, gb, la, lb, "GSE216053", "NEPC")

print("Loading GSE130598 nCounter...")
data130598, tumor_lbls, normal_lbls = parse_ncounter_gse130598()
ga, gb, la, lb = get_groups_130598(tumor_lbls, normal_lbls)
print(f"  Groups: {la} n={len(ga)}, {lb} n={len(gb)}, genes={len(data130598)}")
de130598 = run_de(data130598, ga, gb, la, lb, "GSE130598", "MPBC_MIBC")

print("Loading GSE143630 htseq...")
data143630, samp143630 = parse_htseq_gse143630()
ga, gb, la, lb = get_groups_143630(samp143630)
print(f"  Groups: {la} n={len(ga)}, {lb} n={len(gb)}, genes={len(data143630)}")
de143630 = run_de(data143630, ga, gb, la, lb, "GSE143630", "ccRCC")

print("Loading GSE157256 VST...")
data157256, samp157256 = parse_vst_gse157256()
ga, gb, la, lb = get_groups_157256(samp157256)
print(f"  Groups: {la} n={len(ga)}, {lb} n={len(gb)}, genes={len(data157256)}")
de157256 = run_de(data157256, ga, gb, la, lb, "GSE157256", "RCC_HLRCC")

all_de = de199274 + de216053 + de130598 + de143630 + de157256
print(f"\nTotal DE rows: {len(all_de)}")

# write full DE results
de_path = OUT / "FULL_DE_RESULTS.csv"
if all_de:
    with open(de_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_de[0].keys())
        w.writeheader(); w.writerows(all_de)
    print(f"Saved: {de_path}")

# KEGG enrichment
print("\nRunning KEGG enrichment...")
kegg_rows = compute_kegg_enrichment(all_de)
kegg_path = OUT / "KEGG_ENRICHMENT.csv"
if kegg_rows:
    with open(kegg_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kegg_rows[0].keys())
        w.writeheader(); w.writerows(kegg_rows)
    print(f"Saved: {kegg_path}")

# summary of significant pathway hits
print("\nSignificant KEGG enrichment (p<0.05, k>=2):")
sig = sorted([r for r in kegg_rows if r["p_value_enrichment"] < 0.05 and r["k_sig_in_pathway"] >= 2],
             key=lambda x: x["p_value_enrichment"])
for r in sig[:30]:
    print(f"  {r['dataset']} | {r['pathway']}: k={r['k_sig_in_pathway']}/{r['K_in_pathway']} "
          f"OR={r['odds_ratio']} p={r['p_value_enrichment']:.4f} up:{r['upregulated_pathway_genes'][:60]}")

print("\nDone.")

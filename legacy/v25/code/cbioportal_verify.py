"""Query cBioPortal API to verify alteration frequencies cited in the FDA repurposing manuscript."""
import json
import urllib.request

API = "https://www.cbioportal.org/api"

# Cohort sizes (from prior verification: patientCount)
COHORTS = {
    "blca_tcga_pan_can_atlas_2018": 411,
    "kirc_tcga_pan_can_atlas_2018": 512,
    "prad_tcga_pan_can_atlas_2018": 494,
}

# Entrez Gene IDs
GENES = {
    "TP53": 7157, "PIK3CA": 5290, "CDKN2A": 1029, "FGFR3": 2261,
    "ERCC2": 2068, "ATM": 472, "ERBB2": 2064, "AURKA": 6790,
    "VHL": 7428, "PBRM1": 55193, "SETD2": 29072, "BAP1": 8314,
    "MTOR": 2475, "PTEN": 5728, "RB1": 5925, "NECTIN4": 81607,
}

# Manuscript-cited frequencies
MANUSCRIPT_CLAIMS = {
    ("BLCA", "TP53", "mut"): 48,
    ("BLCA", "PIK3CA", "mut"): 22,
    ("BLCA", "CDKN2A", "deep_del"): 33,
    ("BLCA", "FGFR3", "alt"): 19,
    ("BLCA", "ERCC2", "mut"): 19,
    ("BLCA", "ATM", "mut"): 18,
    ("BLCA", "ERBB2", "alt"): 7,
    ("BLCA", "AURKA", "amp"): 7,
    ("KIRC", "VHL", "alt"): 52,
    ("KIRC", "PBRM1", "alt"): 44,
    ("KIRC", "SETD2", "alt"): 16,
    ("KIRC", "BAP1", "alt"): 13,
    ("KIRC", "MTOR", "alt"): 9,
    ("KIRC", "CDKN2A", "del"): 5,
    ("PRAD", "PTEN", "alt"): 41,
    ("PRAD", "RB1", "del"): 3,
}

def post(path, body):
    req = urllib.request.Request(API + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def count_mutated_samples(study_id, entrez_id):
    """Count unique samples with non-synonymous mutations in the given gene."""
    profile_id = f"{study_id}_mutations"
    sample_list_id = f"{study_id}_sequenced"
    body = {
        "molecularProfileIds": [profile_id],
        "entrezGeneIds": [entrez_id],
    }
    muts = post("/mutations/fetch?projection=SUMMARY&sampleListId=" + sample_list_id, body)
    # Use 'mutationType' to exclude silent
    silent = {"Silent", "Intron", "3'UTR", "5'UTR", "RNA", "IGR", "5'Flank", "3'Flank"}
    samples = set()
    for m in muts:
        if m.get("mutationType") not in silent:
            samples.add(m["sampleId"])
    return len(samples)

def cna_counts(study_id, entrez_id):
    """Return dict of {-2: deep_del, -1: shallow_del, 1: gain, 2: amp} sample counts."""
    profile_id = f"{study_id}_gistic"
    sample_list_id = f"{study_id}_cna"
    body = {
        "entrezGeneIds": [entrez_id],
        "sampleListId": sample_list_id,
    }
    try:
        data = post(f"/molecular-profiles/{profile_id}/discrete-copy-number/fetch?discreteCopyNumberEventType=ALL&projection=SUMMARY", body)
    except Exception as e:
        return {"error": str(e)}
    counts = {-2: 0, -1: 0, 0: 0, 1: 0, 2: 0}
    for d in data:
        counts[d["alteration"]] = counts.get(d["alteration"], 0) + 1
    return counts

def structural_variant_samples(study_id, entrez_id):
    """Count samples with structural variants (fusions) involving the gene."""
    profile_id = f"{study_id}_structural_variants"
    sample_list_id = f"{study_id}_sv"
    body = {
        "entrezGeneIds": [entrez_id],
        "sampleMolecularIdentifiers": None,
    }
    try:
        # Try simple structural-variants fetch
        body2 = {
            "molecularProfileIds": [profile_id],
            "entrezGeneIds": [entrez_id],
        }
        data = post("/structural-variant/fetch", body2)
        return len(set(d["sampleId"] for d in data))
    except Exception:
        return 0

results = []
for (cancer, gene, kind), claim in MANUSCRIPT_CLAIMS.items():
    study_id = {"BLCA": "blca_tcga_pan_can_atlas_2018",
                "KIRC": "kirc_tcga_pan_can_atlas_2018",
                "PRAD": "prad_tcga_pan_can_atlas_2018"}[cancer]
    n = COHORTS[study_id]
    entrez = GENES[gene]

    mut_n = count_mutated_samples(study_id, entrez)
    cnas = cna_counts(study_id, entrez)
    sv_n = structural_variant_samples(study_id, entrez)

    mut_pct = round(100 * mut_n / n, 1)
    deep_del_pct = round(100 * cnas.get(-2, 0) / n, 1) if isinstance(cnas, dict) and "error" not in cnas else None
    amp_pct = round(100 * cnas.get(2, 0) / n, 1) if isinstance(cnas, dict) and "error" not in cnas else None
    sv_pct = round(100 * sv_n / n, 1)

    alt_n = len(set())
    # any-alteration = union of mutated samples, deep_del samples, amp samples, sv samples
    # but we only have counts here, not sample IDs from CNA. Approximate alt_pct = mut + deep_del + amp + sv (upper bound, not strict union)
    upper_alt_pct = round(mut_pct + (deep_del_pct or 0) + (amp_pct or 0) + sv_pct, 1)

    results.append({
        "cancer": cancer, "gene": gene, "kind": kind, "claim_pct": claim,
        "mut_pct": mut_pct, "deep_del_pct": deep_del_pct, "amp_pct": amp_pct,
        "sv_pct": sv_pct, "approx_any_alt_pct": upper_alt_pct,
        "n_cohort": n,
    })
    print(f"{cancer:5s} {gene:8s} {kind:10s} claim={claim:>3}%  mut={mut_pct:>5}%  deep_del={deep_del_pct}%  amp={amp_pct}%  sv={sv_pct}%  approx_any={upper_alt_pct}%")

with open("C:/Users/garre/cbioportal_verify_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved to cbioportal_verify_results.json")

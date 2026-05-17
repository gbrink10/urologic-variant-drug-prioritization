"""Second pass: check 'any alteration' frequencies using cBioPortal's standard combined definition (mut + CNA deep_del/amp + SV), and check TMB-H frequency."""
import json
import urllib.request

API = "https://www.cbioportal.org/api"

def post(path, body):
    req = urllib.request.Request(API + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

COHORTS = {
    "blca_tcga_pan_can_atlas_2018": 411,
    "kirc_tcga_pan_can_atlas_2018": 512,
    "prad_tcga_pan_can_atlas_2018": 494,
}
GENES = {
    "TP53": 7157, "PIK3CA": 5290, "CDKN2A": 1029, "FGFR3": 2261,
    "ERCC2": 2068, "ATM": 472, "ERBB2": 2064, "AURKA": 6790,
    "VHL": 7428, "PBRM1": 55193, "SETD2": 29072, "BAP1": 8314,
    "MTOR": 2475, "PTEN": 5728, "RB1": 5925,
}

# Get the size of {study}_all sample list (the "all profiled samples" denominator cBioPortal uses by default)
def sample_list_size(list_id):
    data = get(f"/sample-lists/{list_id}")
    return data["sampleCount"]

print("Sample list sizes (cBioPortal denominators):")
for study in COHORTS:
    for suffix in ["_all", "_sequenced", "_cna", "_3way_complete", "_rna_seq_v2_mrna"]:
        try:
            n = sample_list_size(study + suffix)
            print(f"  {study + suffix}: {n}")
        except Exception:
            pass

# Standard cBioPortal "altered" = mut OR (CNA in {-2, 2}) OR SV
def altered_samples_combined(study, entrez):
    # Get mutation-bearing samples
    muts = post(f"/mutations/fetch?projection=SUMMARY&sampleListId={study}_sequenced",
        {"molecularProfileIds": [f"{study}_mutations"], "entrezGeneIds": [entrez]})
    silent = {"Silent", "Intron", "3'UTR", "5'UTR", "RNA", "IGR", "5'Flank", "3'Flank"}
    mut_samples = {m["sampleId"] for m in muts if m.get("mutationType") not in silent}

    # CNA -2 or 2
    cna = post(f"/molecular-profiles/{study}_gistic/discrete-copy-number/fetch?discreteCopyNumberEventType=ALL&projection=SUMMARY",
        {"entrezGeneIds": [entrez], "sampleListId": f"{study}_cna"})
    cna_samples = {d["sampleId"] for d in cna if d["alteration"] in (-2, 2)}

    # SV
    try:
        sv = post("/structural-variant/fetch",
            {"molecularProfileIds": [f"{study}_structural_variants"], "entrezGeneIds": [entrez]})
        sv_samples = {s["sampleId"] for s in sv}
    except Exception:
        sv_samples = set()

    return mut_samples | cna_samples | sv_samples, mut_samples, cna_samples, sv_samples

print("\nCombined alteration frequencies (% of patient cohort denominator):\n")
print(f"{'Cancer':<6} {'Gene':<8} {'Combined%':<10} {'Mut%':<8} {'CNA(±2)%':<10} {'SV%':<8} {'Mut+CNA+SV n':<14}")
for cancer, study in [("BLCA", "blca_tcga_pan_can_atlas_2018"),
                      ("KIRC", "kirc_tcga_pan_can_atlas_2018"),
                      ("PRAD", "prad_tcga_pan_can_atlas_2018")]:
    n = COHORTS[study]
    for gene in GENES:
        # Restrict to relevant per-cancer set
        rel = {
            "BLCA": ["TP53","PIK3CA","CDKN2A","FGFR3","ERCC2","ATM","ERBB2","AURKA"],
            "KIRC": ["VHL","PBRM1","SETD2","BAP1","MTOR","CDKN2A"],
            "PRAD": ["PTEN","RB1"],
        }
        if gene not in rel[cancer]:
            continue
        try:
            all_alt, mut, cna, sv = altered_samples_combined(study, GENES[gene])
            print(f"{cancer:<6} {gene:<8} {100*len(all_alt)/n:<10.1f} {100*len(mut)/n:<8.1f} {100*len(cna)/n:<10.1f} {100*len(sv)/n:<8.1f} {len(all_alt):<14}")
        except Exception as e:
            print(f"{cancer:<6} {gene:<8} ERROR: {e}")

# TMB-H frequency in BLCA: TMB ≥10 mut/Mb per TCGA/cBioPortal clinical attribute
print("\nChecking TMB-H frequency for BLCA (clinical attribute TMB_NONSYNONYMOUS):")
try:
    data = post("/clinical-data/fetch?clinicalDataType=SAMPLE",
        {"attributeIds": ["TMB_NONSYNONYMOUS"],
         "identifiers": []  # empty = all samples
        })
except Exception as e:
    print(f"  TMB clinical query failed: {e}")
    # Alternative: query the sample-level clinical-data with the BLCA study filter
    try:
        url = "/clinical-data-counts/fetch"
        d = post(url, {
            "attributes": [{"attributeId": "TMB_NONSYNONYMOUS", "clinicalDataType": "SAMPLE"}],
            "studyViewFilter": {"studyIds": ["blca_tcga_pan_can_atlas_2018"]}
        })
        print(f"  TMB counts (BLCA): {d}")
    except Exception as e2:
        print(f"  Alternate TMB query also failed: {e2}")

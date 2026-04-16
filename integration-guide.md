# Drug Discovery API — Integration Guide

Version: 1.0  
Last Updated: April 2026  
Base URL: https://drug-discovery-orchestrator.fly.dev

---

## Overview

The Drug Discovery API provides six AI-powered computational biology tasks via a single authenticated REST service hosted on Fly.io.

Partners send requests to task-specific POST endpoints and receive AI model predictions for molecule generation, ADMET property prediction, drug-target interaction, molecular docking, pose rescoring, and retrosynthesis — all through the same orchestrator, authenticated with a single API key.

Typical integration time: **2–4 weeks**

---

## Base URL

**Production**

```
https://drug-discovery-orchestrator.fly.dev
```

---

## Authentication

The Drug Discovery API uses a **single authentication layer** shared across all six tasks.

Two equivalent methods are accepted:

**Method A — X-API-Key header** (used by the Gradio HF Space demo):
```
X-API-Key: YOUR_PARTNER_API_KEY
Content-Type: application/json
```

**Method B — Bearer token** (standard REST integration):
```
Authorization: Bearer YOUR_PARTNER_API_KEY
Content-Type: application/json
```

Partners do **not** need a HuggingFace token. The orchestrator handles all routing to HF Inference Endpoints internally, injecting its own `HF_TOKEN`.

Keys are stored as SHA-256 hashes in Fly.io secrets (`PARTNER_KEY_HASH_<NAME>`). To generate a hash:
```python
import hashlib
print(hashlib.sha256("RAW_KEY_HERE".encode()).hexdigest())
```

---

## Architecture

```
Partner Platform
      ↓  POST /<task-endpoint>  +  API key
Drug Discovery Orchestrator (Fly.io)
      ↓  SHA-256 key hash verification
      ↓  routes by endpoint path
  ┌──────────────────┬────────────────────┬──────────────────────┬───────────────┬────────────┬──────────────────┐
  ↓                  ↓                    ↓                      ↓               ↓            ↓
Molecule Gen      Property Pred        Drug-Target            DiffDock-HF    GNINA-HF    Retrosynthesis
HF Endpoint       HF Endpoint          HF Endpoint            HF Endpoint    HF Endpoint  HF Endpoint
  └──────────────────┴────────────────────┴──────────────────────┴───────────────┴────────────┴──────────────────┘
                                                   ↓
                                        Drug Discovery Orchestrator
                                                   ↓
                                            Response → Partner
```

---

## Health Check

```
GET https://drug-discovery-orchestrator.fly.dev/health
```

Response:
```json
{
  "ok": true,
  "partners_registered": 2,
  "hf_token_set": true,
  "endpoints": [
    "molecule-generation",
    "property-prediction",
    "drug-target-interaction",
    "diffdock-hf",
    "gnina-hf",
    "retrosynthesis"
  ]
}
```

---

# Task 1: Molecule Generation

## What it does

Masked-SMILES completion: fills `<mask>` tokens in a partial SMILES string to generate novel drug-like candidate molecules.

Outputs per request:
- Top-K completed SMILES strings, ranked by model score
- Per-molecule Lipinski drug-likeness assessment (Rule-of-Five)
- Molecular descriptors (MW, LogP, HBD, HBA, TPSA, rotatable bonds)

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/molecule-generation
```

## Request Structure

```json
{
  "inputs": {
    "masked_smiles": "CC(C)Cc1ccc(C(C)<mask>C(=O)O)cc1",
    "top_k": 5,
    "filter_valid": true
  }
}
```

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `masked_smiles` | string | Yes | SMILES string with one or more `<mask>` tokens to be completed |
| `top_k` | integer | Yes | Number of top completions to return (1–20) |
| `filter_valid` | boolean | Yes | If true, return only chemically valid molecules |

## Response Structure

```json
{
  "status": "success",
  "model_info": {
    "name": "ChemBERTa-masked-SMILES",
    "version": "1.0"
  },
  "statistics": {
    "total_completions": 5,
    "valid_molecules": 4,
    "drug_like_molecules": 3
  },
  "completed_molecules": [
    {
      "completed_smiles": "CC(C)Cc1ccc(C(C)CC(=O)O)cc1",
      "score": 0.9821,
      "drug_like": true,
      "lipinski_violations": 0,
      "properties": {
        "molecular_weight": 220.31,
        "logp": 3.12,
        "hbd": 1,
        "hba": 2,
        "tpsa": 37.3,
        "rotatable_bonds": 5
      }
    }
  ]
}
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `status` | `"success"` or `"error"` |
| `statistics.total_completions` | Total completions generated before filtering |
| `statistics.valid_molecules` | Completions that parse as valid chemical structures |
| `statistics.drug_like_molecules` | Valid molecules passing Lipinski's Rule-of-Five (0 violations) |
| `completed_smiles` | The full completed SMILES string |
| `score` | Model confidence score (0–1; higher = better completion quality) |
| `drug_like` | True if Lipinski violations = 0 |
| `lipinski_violations` | Count of Lipinski rules violated (0–4; 0 = fully compliant) |
| `properties.molecular_weight` | Molecular weight in Daltons |
| `properties.logp` | Octanol-water partition coefficient |
| `properties.hbd` | Hydrogen bond donors |
| `properties.hba` | Hydrogen bond acceptors |
| `properties.tpsa` | Topological polar surface area (Å²) |
| `properties.rotatable_bonds` | Count of rotatable bonds |

**Lipinski's Rule-of-Five thresholds:**

| Property | Threshold | Direction |
|----------|-----------|-----------|
| MW | ≤ 500 Da | Lower = more oral-bioavailable |
| LogP | ≤ 5 | Lower = more soluble |
| HBD | ≤ 5 | Lower = better |
| HBA | ≤ 10 | Lower = better |

---

# Task 2: Property Prediction

## What it does

Multi-task ADMET property prediction using MTL-BERT (Zhang et al. 2022). Accepts one or more SMILES strings and returns predicted values for up to 8 properties.

**Model:** MTL-BERT — multitask BERT pretrained on 1.7 M ChEMBL molecules, fine-tuned on 60 ADMET datasets.  
**Reference:** DOI: 10.34133/research.0004

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/property-prediction
```

## Request Structure

```json
{
  "inputs": {
    "smiles_list": [
      "CC(=O)Oc1ccccc1C(=O)O",
      "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
    ],
    "tasks": [
      "solubility",
      "toxicity",
      "bioavailability",
      "bbb_penetration",
      "cyp_inhibition",
      "herg_cardiotoxicity",
      "caco2_permeability",
      "lipophilicity"
    ]
  },
  "parameters": {}
}
```

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `smiles_list` | array of strings | Yes | One or more valid SMILES strings |
| `tasks` | array of strings | Yes | Property tasks to predict (see table below) |

**Available tasks:**

| Task name | Type | Score range | Interpretation |
|-----------|------|-------------|----------------|
| `solubility` | Classification | 0–1 | >0.5 = predicted aqueous-soluble (LogS threshold) |
| `toxicity` | Classification | 0–1 | >0.5 = predicted mutagenic / toxic (AMES endpoint) |
| `bioavailability` | Classification | 0–1 | >0.5 = predicted oral bioavailability >20% (F₂₀% dataset) |
| `bbb_penetration` | Classification | 0–1 | >0.5 = predicted to cross blood-brain barrier |
| `cyp_inhibition` | Classification | 0–1 per isoform | >0.5 = predicted inhibitor (CYP3A4/2D6/2C9/2C19/1A2) |
| `herg_cardiotoxicity` | Classification | 0–1 | >0.5 = predicted hERG channel inhibitor (cardiac safety risk) |
| `caco2_permeability` | Regression | −1 to 0 | Closer to 0 = higher predicted intestinal permeability |
| `lipophilicity` | Regression | −1 to 0 | Closer to 0 = more lipophilic (higher log D at pH 7.4) |

## Response Structure

```json
[
  {
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "properties": {
      "solubility": 0.72,
      "toxicity": 0.13,
      "bioavailability": 0.81,
      "bbb_penetration": 0.31,
      "cyp_inhibition": {
        "CYP3A4": 0.11,
        "CYP2D6": 0.08,
        "CYP2C9": 0.14,
        "CYP2C19": 0.10,
        "CYP1A2": 0.09
      },
      "herg_cardiotoxicity": 0.09,
      "caco2_permeability": -0.38,
      "lipophilicity": -0.61
    },
    "molecular_descriptors": {
      "molecular_weight": 180.16,
      "logp": 1.19,
      "hbd": 1,
      "hba": 4,
      "tpsa": 63.6,
      "rotatable_bonds": 3
    }
  }
]
```

**Notes:**
- `cyp_inhibition` returns a sub-object with one score per isoform.
- Regression scores (`caco2_permeability`, `lipophilicity`) use a normalised −1 to 0 scale; **0 = most favourable** end.
- The response is a JSON array with one entry per SMILES string.

---

# Task 3: Drug–Target Interaction

## What it does

Binding affinity prediction between a small-molecule drug (SMILES) and a protein target (amino-acid sequence) using the DeepPurpose framework.

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/drug-target-interaction
```

## Request Structure

```json
{
  "inputs": {
    "drug_smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "target_sequence": "MLARALLLCAVLALSHTANPCCSHPCQNRGVCMSVGFDQYKCDCTRTGFYGENCSTPEFLTRIKLFLKPTPNTVHYILTHFKGFWNVVNNIPFLRNAIMSYVLTSRSHLIDSPPTYNADYGYKSWEAFSNLSYYTRALPPVPDDCPTPLGVKGKKQLPDSNEIVEKLLLRRKFIPD",
    "target_name": "COX-2",
    "drug_encoding": "MPNN",
    "target_encoding": "CNN"
  },
  "parameters": {}
}
```

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `drug_smiles` | string | Yes | SMILES string of the drug molecule |
| `target_sequence` | string | Yes | Single-letter amino-acid sequence of the target protein |
| `target_name` | string | Yes | Human-readable label for the target (used in output only) |
| `drug_encoding` | string | Yes | Drug molecular representation method |
| `target_encoding` | string | Yes | Protein sequence encoding method |

**Drug encoding options:**

| Value | Description |
|-------|-------------|
| `MPNN` | Message-Passing Neural Network (graph-based, best for complex structures) |
| `CNN` | Convolutional Neural Network on SMILES string |
| `Morgan` | Morgan circular fingerprint |
| `Daylight` | Daylight fingerprint |
| `rdkit_2d_normalized` | RDKit 2D normalized descriptors |

**Target encoding options:**

| Value | Description |
|-------|-------------|
| `CNN` | Convolutional Neural Network on amino-acid sequence |
| `Transformer` | Transformer encoder on amino-acid sequence |
| `AAC` | Amino acid composition |
| `PseAAC` | Pseudo amino acid composition |
| `Conjoint_triad` | Conjoint triad features |

## Response Structure

```json
{
  "drug_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "target_name": "COX-2",
  "target_sequence_length": 181,
  "binding_prediction": {
    "binding_affinity": -7.42,
    "confidence": 0.83,
    "interaction_strength": "Strong",
    "clinical_relevance": "High",
    "prediction_method": "MPNN+CNN"
  },
  "drug_properties": {
    "molecular_weight": 180.16,
    "logp": 1.19,
    "hbd": 1,
    "hba": 4
  },
  "protein_properties": {
    "sequence_length": 181,
    "amino_acid_composition": "..."
  }
}
```

**Binding prediction fields:**

| Field | Range | Interpretation |
|-------|-------|----------------|
| `binding_affinity` | Continuous (negative) | Lower (more negative) = stronger predicted binding |
| `confidence` | 0–1 | Model certainty; higher = more confident prediction |
| `interaction_strength` | Strong / Moderate / Weak | Qualitative label derived from affinity score |
| `clinical_relevance` | High / Medium / Low | Indicative category based on thresholds — not a clinical prediction |

---

# Task 4: Molecular Docking (DiffDock-HF)

## What it does

Diffusion-based **blind** molecular docking. No binding box or reference crystal structure is required — the model predicts the binding site from sequence alone.

**Model:** DiffDock (Corso et al. 2023) — diffusion generative model for molecular docking.

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/diffdock-hf
```

**Timeout:** 300 s (5 minutes)

## Request Structure

```json
{
  "inputs": {
    "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "protein_sequence": "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFSRILLGTPNEAIWPDIVYLPDFKPSFPQWRRKDLSQVVPSLDPRGIDLLDKLLAKNLVEDAHSLTSGSTPTLSSSAGSVTPMSTKVLV",
    "complex_name": "cdk2_ibuprofen"
  },
  "parameters": {
    "samples_per_complex": 2,
    "inference_steps": 4
  }
}
```

**Input fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ligand_smiles` | string | Yes | — | SMILES string of the ligand / drug molecule |
| `protein_sequence` | string | Yes | — | Protein amino-acid sequence (single-letter code). FASTA format accepted — header lines starting with `>` are stripped automatically. |
| `complex_name` | string | No | `"complex"` | Human-readable label for the protein-ligand complex |
| `samples_per_complex` | integer | No | `2` | Number of diffusion samples (binding poses) to generate (1–10) |
| `inference_steps` | integer | No | `4` | Number of diffusion inference steps (1–50); more steps = higher quality but slower |

## Response Structure

```json
{
  "status": "success",
  "complex_name": "cdk2_ibuprofen",
  "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
  "num_poses": 2,
  "best_confidence": 1.24,
  "best_estimated_dG_kcal_mol": -7.86,
  "ligand_properties": {
    "molecular_weight": 206.28,
    "logp": 3.72,
    "hbd": 1,
    "hba": 2
  },
  "poses": [
    {
      "rank": 1,
      "confidence": 1.24,
      "estimated_dG_kcal_mol": -7.86,
      "pose_centroid_xyz": { "x": 12.4, "y": -3.1, "z": 8.7 }
    },
    {
      "rank": 2,
      "confidence": 0.61,
      "estimated_dG_kcal_mol": -6.92,
      "pose_centroid_xyz": { "x": 9.1, "y": -5.3, "z": 11.2 }
    }
  ],
  "protein_pdb": "ATOM      1  N   MET A   1 ..."
}
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `num_poses` | Number of binding poses generated |
| `best_confidence` | Highest confidence score across all poses |
| `best_estimated_dG_kcal_mol` | ΔG proxy for the best pose (kcal/mol) |
| `poses[].rank` | Pose rank (1 = highest confidence) |
| `poses[].confidence` | DiffDock confidence score (≈ −5 to +5); **>0 = likely near-native** (RMSD < 2 Å vs. crystal structure) |
| `poses[].estimated_dG_kcal_mol` | Empirical ΔG proxy: ≈ −1.5 × confidence − 6.0 kcal/mol. **Not a true binding free energy — use GNINA for rigorous rescoring.** |
| `poses[].pose_centroid_xyz` | 3D coordinates of the pose centroid |
| `protein_pdb` | Full protein structure in PDB format (for 3D visualisation) |

💡 **Next step:** Pass the full response JSON as `diffdock_output` to `/gnina-hf` for CNN rescoring.

---

# Task 5: Pose Rescoring (GNINA-HF)

## What it does

CNN-based rescoring of DiffDock binding poses using GNINA. Re-ranks poses by three complementary scores and identifies the best candidate pose.

**Model:** GNINA (McNutt et al. 2021) — convolutional neural network trained on protein-ligand complexes from the PDB.

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/gnina-hf
```

**Timeout:** 300 s (5 minutes)

## Request Structure

```json
{
  "inputs": {
    "diffdock_output": {
      "status": "success",
      "complex_name": "cdk2_ibuprofen",
      "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "poses": [ ... ],
      "protein_pdb": "ATOM ..."
    },
    "top_n_poses": 2
  },
  "parameters": {
    "score_only": true,
    "seed": 0,
    "cpu": 4
  }
}
```

**Input fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `diffdock_output` | object | Yes | — | The **complete** JSON response from a `/diffdock-hf` call |
| `top_n_poses` | integer | No | `2` | Number of top DiffDock poses to rescore (1–20) |
| `score_only` | boolean | No | `true` | If true, score poses without energy minimisation (faster) |
| `seed` | integer | No | `0` | Random seed for reproducibility |
| `cpu` | integer | No | `4` | Number of CPU threads to use |

## Response Structure

```json
{
  "complex_name": "cdk2_ibuprofen",
  "num_scored": 2,
  "num_input_poses": 2,
  "mode": "score_only",
  "best_minimizedAffinity": -8.14,
  "best_CNNscore": 0.76,
  "best_CNNaffinity": 7.3,
  "score_notes": {
    "minimizedAffinity_unit": "kcal/mol",
    "CNNscore_range": "0–1",
    "CNNaffinity_unit": "pKi/pKd"
  },
  "scored_poses": [
    {
      "diffdock_rank": 1,
      "diffdock_confidence": 1.24,
      "minimizedAffinity": -8.14,
      "CNNscore": 0.76,
      "CNNaffinity": 7.3
    },
    {
      "diffdock_rank": 2,
      "diffdock_confidence": 0.61,
      "minimizedAffinity": -6.87,
      "CNNscore": 0.52,
      "CNNaffinity": 6.1
    }
  ]
}
```

**Score interpretation:**

| Score | Range | Interpretation |
|-------|-------|----------------|
| `minimizedAffinity` | kcal/mol (negative) | More negative = stronger predicted binding. Typical drug-like range: −4 to −12 kcal/mol |
| `CNNscore` | 0–1 | Probability that pose is an active binder. **>0.5 = likely active** |
| `CNNaffinity` | pKi/pKd | −log₁₀(Kd/Ki). **6 ≈ 1 µM potency, 9 ≈ 1 nM potency** |

---

# Task 6: Retrosynthesis

## What it does

AI-planned multi-step backward synthetic route planning from a target molecule to purchasable starting materials.

**Model:** GLN / OpenRetro retrosynthesis AI.

## Endpoint

```
POST https://drug-discovery-orchestrator.fly.dev/retrosynthesis
```

## Request Structure

```json
{
  "inputs": {
    "target_smiles": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
    "max_depth": 5,
    "min_confidence": 0.3
  },
  "parameters": {}
}
```

**Input fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target_smiles` | string | Yes | — | SMILES string of the target molecule to synthesise |
| `max_depth` | integer | No | `5` | Maximum number of retrosynthetic steps to search (1–10) |
| `min_confidence` | float | No | `0.3` | Minimum step confidence threshold; routes with lower-confidence steps are excluded (0.0–1.0) |

## Response Structure

```json
{
  "status": "success",
  "target_molecule": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
  "routes_found": 2,
  "best_route_feasibility": 0.87,
  "model_info": { "name": "GLN-Retrosynthesis" },
  "synthesis_routes": [
    {
      "route_id": 1,
      "feasibility_score": 0.87,
      "synthetic_accessibility": 2.4,
      "overall_yield": "34%",
      "total_steps": 3,
      "estimated_cost": "$120",
      "estimated_time": "2 days",
      "starting_materials": [
        "CC1=CC=CC=C1",
        "NNS(=O)(=O)c1ccc(cc1)"
      ],
      "steps": [
        {
          "step": 1,
          "reaction_type": "Condensation",
          "reactants": ["CC1=CC=CC=C1", "NNS(=O)(=O)c1ccc(cc1)"],
          "confidence": 0.91,
          "yield_estimate": "65%",
          "conditions": {
            "solvent": "EtOH",
            "temperature": "80°C",
            "catalyst": "AcOH",
            "time": "4h"
          }
        }
      ]
    }
  ]
}
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `routes_found` | Total number of routes found meeting the min_confidence threshold |
| `best_route_feasibility` | Highest feasibility score among all routes |
| `feasibility_score` | 0–1; higher = more synthetically feasible route |
| `synthetic_accessibility` | SA score 1–10; 1 = trivially easy, 10 = extremely difficult. Drug candidates typically 1–4 |
| `overall_yield` | Compounded yield estimate across all steps |
| `estimated_cost` | Indicative reagent cost (not a market price) |
| `estimated_time` | Indicative synthesis time |
| `starting_materials` | SMILES list of purchasable starting materials |
| `steps[].confidence` | Model certainty for this individual reaction step (0–1) |
| `steps[].yield_estimate` | Per-step yield estimate |
| `steps[].conditions` | Solvent, temperature, catalyst, and reaction time |

---

# Common Integration Patterns

## Sequential Pipeline Integration

The recommended pipeline chains tasks in sequence:

```python
import requests

BASE = "https://drug-discovery-orchestrator.fly.dev"
HEADERS = {"X-API-Key": "YOUR_KEY", "Content-Type": "application/json"}

# Step 1: Generate candidates
mol_resp = requests.post(f"{BASE}/molecule-generation", headers=HEADERS, json={
    "inputs": {"masked_smiles": "CC(C)Cc1ccc(C(C)<mask>C(=O)O)cc1", "top_k": 5, "filter_valid": True}
})
candidates = mol_resp.json()["completed_molecules"]

# Step 2: Filter by ADMET properties
for mol in candidates:
    prop_resp = requests.post(f"{BASE}/property-prediction", headers=HEADERS, json={
        "inputs": {"smiles_list": [mol["completed_smiles"]], "tasks": ["solubility", "toxicity", "herg_cardiotoxicity"]}
    })
    mol["admet"] = prop_resp.json()[0]["properties"]

# Step 3: Rank by DTI
for mol in candidates:
    dti_resp = requests.post(f"{BASE}/drug-target-interaction", headers=HEADERS, json={
        "inputs": {
            "drug_smiles": mol["completed_smiles"],
            "target_sequence": "MLARALLLCAVLALSHTANPCC...",
            "target_name": "COX-2",
            "drug_encoding": "MPNN",
            "target_encoding": "CNN"
        }
    })
    mol["binding_affinity"] = dti_resp.json()["binding_prediction"]["binding_affinity"]

# Step 4: Dock top candidate
top_mol = sorted(candidates, key=lambda m: m["binding_affinity"])[0]
dock_resp = requests.post(f"{BASE}/diffdock-hf", headers=HEADERS, json={
    "inputs": {
        "ligand_smiles": top_mol["completed_smiles"],
        "protein_sequence": "MENFQKVEKIGEGTYGVVYK...",
        "complex_name": "top_candidate"
    },
    "parameters": {"samples_per_complex": 3, "inference_steps": 10}
}, timeout=300)
diffdock_output = dock_resp.json()

# Step 5: Rescore poses
rescore_resp = requests.post(f"{BASE}/gnina-hf", headers=HEADERS, json={
    "inputs": {"diffdock_output": diffdock_output, "top_n_poses": 3},
    "parameters": {"score_only": True, "seed": 0, "cpu": 4}
}, timeout=300)

# Step 6: Plan synthesis for confirmed hit
retro_resp = requests.post(f"{BASE}/retrosynthesis", headers=HEADERS, json={
    "inputs": {
        "target_smiles": top_mol["completed_smiles"],
        "max_depth": 5,
        "min_confidence": 0.3
    }
})
```

## Docking → Rescoring (Two-Step)

DiffDock and GNINA are designed to work together. The GNINA endpoint accepts the raw DiffDock JSON response:

```python
# Dock
dock = requests.post(f"{BASE}/diffdock-hf", headers=HEADERS, json={...}, timeout=300).json()

# Rescore — pass full docking response directly
rescore = requests.post(f"{BASE}/gnina-hf", headers=HEADERS, json={
    "inputs": {
        "diffdock_output": dock,   # full DiffDock response object
        "top_n_poses": 2
    },
    "parameters": {"score_only": True, "seed": 0, "cpu": 4}
}, timeout=300).json()

print(f"Best CNNscore: {rescore['best_CNNscore']}")
print(f"Best affinity: {rescore['best_minimizedAffinity']} kcal/mol")
```

## Batch Property Prediction

The `/property-prediction` endpoint accepts multiple SMILES in a single call:

```python
smiles_batch = [
    "CC(=O)Oc1ccccc1C(=O)O",
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "c1ccc2ccccc2c1"
]

resp = requests.post(f"{BASE}/property-prediction", headers=HEADERS, json={
    "inputs": {
        "smiles_list": smiles_batch,
        "tasks": ["solubility", "toxicity", "bioavailability", "herg_cardiotoxicity"]
    },
    "parameters": {}
}).json()

for entry in resp:
    props = entry["properties"]
    print(f"{entry['smiles']}: sol={props['solubility']:.2f}, tox={props['toxicity']:.2f}")
```

---

# Error Handling

## HTTP Status Codes

| Code | Source | Meaning | Action |
|------|--------|---------|--------|
| 401 | Orchestrator | Missing API key | Add `X-API-Key` or `Authorization: Bearer` header |
| 403 | Orchestrator | Invalid API key | Verify key; contact administrator |
| 500 | Orchestrator | `HF_TOKEN` not set | Server-side configuration issue — contact admin |
| 4xx | HF Endpoint | Model input error | Check `detail` field in response body |
| 5xx | HF Endpoint | Model unavailable | HF endpoint cold-starting — retry after 30 s |

## Error Response Format

```json
{
  "detail": "Invalid API key."
}
```

or for HF-originated errors:

```json
{
  "detail": {
    "error": "Input validation error",
    "warnings": ["..."]
  }
}
```

## Retry Logic

```python
import time

def call_with_retry(url, headers, payload, timeout=120, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code < 500:
                return resp.json()
            print(f"Attempt {attempt+1}: HTTP {resp.status_code} — retrying in 30s...")
            time.sleep(30)
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt+1}: Timeout — retrying...")
            time.sleep(10)
    raise RuntimeError("Max retries exceeded")
```

---

# Rate Limits

No hard rate limits are enforced by default. For high-volume workloads:
- Docking tasks (`/diffdock-hf`, `/gnina-hf`) have a 300 s timeout — avoid parallelising more than 2–3 simultaneously.
- Property prediction accepts batches — prefer sending one request with 50 SMILES over 50 individual requests.

---

# Integration Support

For technical integration questions, include:
- Task endpoint name (e.g., `diffdock-hf`)
- Request body (redact API key)
- Response body or Fly.io log excerpt
- Python / cURL version and OS

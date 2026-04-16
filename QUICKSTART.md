# Drug Discovery API — Quickstart

Run your first AI-powered drug discovery prediction in under 5 minutes.

---

## Step 1 — Get Your API Key

You need one credential:

**Drug Discovery Partner API Key**

Used as `X-API-Key` header or `Authorization: Bearer` token. Works for all six tasks.

Request access: contact your administrator.

---

## Step 2 — Verify the Service is Running

```bash
curl https://drug-discovery-orchestrator.fly.dev/health
```

Expected response:
```json
{
  "ok": true,
  "partners_registered": 1,
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

## Step 3 — Pick a Task

| Task | Endpoint |
|------|----------|
| Molecule Generation | `POST /molecule-generation` |
| Property Prediction | `POST /property-prediction` |
| Drug–Target Interaction | `POST /drug-target-interaction` |
| Molecular Docking | `POST /diffdock-hf` |
| Pose Rescoring | `POST /gnina-hf` |
| Retrosynthesis | `POST /retrosynthesis` |

All tasks use the same base URL and the same API key.

The only structural difference per task is the endpoint path and the `inputs` / `parameters` payload shape.

---

## Task 1 — Molecule Generation

Generate drug-like candidates by completing a masked SMILES string.

```bash
curl https://drug-discovery-orchestrator.fly.dev/molecule-generation \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "masked_smiles": "CC(C)Cc1ccc(C(C)<mask>C(=O)O)cc1",
      "top_k": 5,
      "filter_valid": true
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "model_info": { "name": "ChemBERTa-masked-SMILES" },
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

---

## Task 2 — Property Prediction

Predict ADMET and physicochemical properties for one or more SMILES strings.

```bash
curl https://drug-discovery-orchestrator.fly.dev/property-prediction \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "smiles_list": ["CC(=O)Oc1ccccc1C(=O)O"],
      "tasks": ["solubility", "toxicity", "bioavailability", "herg_cardiotoxicity"]
    },
    "parameters": {}
  }'
```

**Response:**
```json
[
  {
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "properties": {
      "solubility": 0.72,
      "toxicity": 0.13,
      "bioavailability": 0.81,
      "herg_cardiotoxicity": 0.09
    },
    "molecular_descriptors": {
      "molecular_weight": 180.16,
      "logp": 1.19,
      "hbd": 1,
      "hba": 4
    }
  }
]
```

---

## Task 3 — Drug–Target Interaction

Predict binding affinity between a drug and a protein.

```bash
curl https://drug-discovery-orchestrator.fly.dev/drug-target-interaction \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "drug_smiles": "CC(=O)Oc1ccccc1C(=O)O",
      "target_sequence": "MLARALLLCAVLALSHTANPCCSHPCQNRGVCMSVGFDQYKCDCTRTGFYGENCSTPEFLTRIKLFLKPTPNTVHYILTHFKGFWNVVNNIPFLRNAIMSYVLTSRSHLIDSPPTYNADYGYKSWEAFSNLSYYTRALPPVPDDCPTPLGVKGKKQLPDSNEIVEKLLLRRKFIPD",
      "target_name": "COX-2",
      "drug_encoding": "MPNN",
      "target_encoding": "CNN"
    },
    "parameters": {}
  }'
```

**Response:**
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
    "logp": 1.19
  },
  "protein_properties": {
    "sequence_length": 181,
    "amino_acid_composition": "..."
  }
}
```

---

## Task 4 — Molecular Docking (DiffDock)

Blind diffusion-based docking — no binding box required.

```bash
curl https://drug-discovery-orchestrator.fly.dev/diffdock-hf \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "protein_sequence": "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALK",
      "complex_name": "cdk2_ibuprofen"
    },
    "parameters": {
      "samples_per_complex": 2,
      "inference_steps": 4
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "complex_name": "cdk2_ibuprofen",
  "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
  "num_poses": 2,
  "best_confidence": 1.24,
  "best_estimated_dG_kcal_mol": -7.86,
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
  "ligand_properties": {
    "molecular_weight": 206.28,
    "logp": 3.72
  }
}
```

💡 **Next step:** Pass the full JSON response as `diffdock_output` to `/gnina-hf` for CNN rescoring.

---

## Task 5 — Pose Rescoring (GNINA)

CNN-based rescoring of DiffDock poses. Typically called right after Task 4.

```bash
curl https://drug-discovery-orchestrator.fly.dev/gnina-hf \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "diffdock_output": { "status": "success", "complex_name": "cdk2_ibuprofen", "poses": [...] },
      "top_n_poses": 2
    },
    "parameters": {
      "score_only": true,
      "seed": 0,
      "cpu": 4
    }
  }'
```

**Response:**
```json
{
  "complex_name": "cdk2_ibuprofen",
  "num_scored": 2,
  "num_input_poses": 2,
  "mode": "score_only",
  "best_minimizedAffinity": -8.14,
  "best_CNNscore": 0.76,
  "best_CNNaffinity": 7.3,
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

---

## Task 6 — Retrosynthesis

Plan multi-step synthetic routes for a target molecule.

```bash
curl https://drug-discovery-orchestrator.fly.dev/retrosynthesis \
  -H "X-API-Key: YOUR_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "target_smiles": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
      "max_depth": 5,
      "min_confidence": 0.3
    },
    "parameters": {}
  }'
```

**Response:**
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
      "starting_materials": ["CC1=CC=CC=C1", "NNS(=O)(=O)c1ccc(cc1)"],
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

---

## Step 4 — Import Postman Collection

Import `postman_collection.json` and set environment variables:

```
partner_api_key = your Drug Discovery API key
base_url        = https://drug-discovery-orchestrator.fly.dev
```

The collection includes pre-built requests for all six tasks.

---

## Authentication Methods

| Method | Header | Notes |
|--------|--------|-------|
| X-API-Key | `X-API-Key: YOUR_KEY` | Used by Gradio HF Space demo |
| Bearer token | `Authorization: Bearer YOUR_KEY` | Standard REST clients |

Both methods are equivalent and accept the same key value.

---

## Common Errors

| Code | Meaning | Fix |
|------|---------|-----|
| 401 | Missing API key | Add `X-API-Key` or `Authorization: Bearer` header |
| 403 | Invalid API key | Verify the key value |
| 500 | Server misconfiguration | `HF_TOKEN` env var not set — contact admin |
| 4xx (from HF) | Model error | Check `detail` in response body |
| 5xx (from HF) | Model unavailable | HF endpoint cold — retry after ~30 s |

---

## Recommended Workflow

```
Molecule Generation  →  Property Prediction  →  Drug–Target Interaction
                                                          ↓
                              Pose Rescoring (GNINA)  ←  Molecular Docking (DiffDock)
                                                          ↓
                                               Retrosynthesis
```

---

## Support

Contact your administrator for API key provisioning and technical support.

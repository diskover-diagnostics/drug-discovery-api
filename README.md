# Drug Discovery API

The Drug Discovery API provides six AI-powered computational biology endpoints via a single authenticated REST service.

All six tasks share the same base URL, authentication layer, and `X-API-Key` / `Bearer` token scheme.

---

## Tasks

| Task | Endpoint | What it does |
|------|----------|--------------|
| **Molecule Generation** | `POST /molecule-generation` | Complete masked SMILES tokens; generate drug-like candidates |
| **Property Prediction** | `POST /property-prediction` | Predict ADMET & physicochemical properties (MTL-BERT) |
| **Drug–Target Interaction** | `POST /drug-target-interaction` | Predict binding affinity between a drug and a protein |
| **Molecular Docking** | `POST /diffdock-hf` | Diffusion-based blind docking (DiffDock) |
| **Pose Rescoring** | `POST /gnina-hf` | CNN-based rescoring of docking poses (GNINA) |
| **Retrosynthesis** | `POST /retrosynthesis` | Plan multi-step synthetic routes for a target molecule |

---

## Base URL

```
https://drug-discovery-orchestrator.fly.dev
```

All task endpoints are `POST` requests to paths beneath this base URL.

---

## Authentication

Two equivalent authentication methods are accepted:

**Option A — X-API-Key header** (used by the HuggingFace Space Gradio demo):
```
X-API-Key: YOUR_PARTNER_API_KEY
```

**Option B — Bearer token** (standard REST integration):
```
Authorization: Bearer YOUR_PARTNER_API_KEY
```

Partners do **not** need a HuggingFace token. The orchestrator handles all routing to HF Inference Endpoints internally.

---

## Architecture

```
Partner / Client
      ↓  POST /<task-endpoint>  +  X-API-Key or Bearer token
Drug Discovery Orchestrator (Fly.io)
      ↓  SHA-256 key verification
      ↓  routes to correct HF Inference Endpoint
  ┌──────────────┬──────────────────┬───────────────────┬───────────────┬──────────────┬─────────────────┐
  ↓              ↓                  ↓                   ↓               ↓              ↓
Molecule     Property          Drug–Target         DiffDock-HF      GNINA-HF     Retrosynthesis
Generation   Prediction        Interaction         (Docking)       (Rescoring)
  HF Endpoint  HF Endpoint       HF Endpoint         HF Endpoint     HF Endpoint   HF Endpoint
  └──────────────┴──────────────────┴───────────────────┴───────────────┴──────────────┴─────────────────┘
                                          ↓
                               Drug Discovery Orchestrator
                                          ↓
                                   Response → Partner
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | Run your first prediction in 5 minutes |
| [integration-guide.md](./integration-guide.md) | Full integration reference for all 6 tasks |
| [partner-pack.md](./partner-pack.md) | Partner onboarding guide |
| [openapi.yaml](./openapi.yaml) | OpenAPI 3.0 specification |
| [postman_collection.json](./postman_collection.json) | Postman collection with all 6 tasks |
| [curl_examples.sh](./curl_examples.sh) | Ready-to-run cURL examples |

---

## Task Summary

### Molecule Generation
Generative masked-SMILES completion:
- Fills `<mask>` tokens in a partial SMILES string to produce complete candidate molecules
- Returns top-K completions ranked by model score
- Each candidate annotated with Lipinski drug-likeness and key molecular descriptors (MW, LogP, HBD, HBA, TPSA, rotatable bonds)

### Property Prediction
Multi-task ADMET property prediction (MTL-BERT, Zhang et al. 2022):
- Solubility, toxicity (AMES), oral bioavailability, BBB penetration
- CYP isoform inhibition (3A4, 2D6, 2C9, 2C19, 1A2)
- hERG cardiotoxicity
- Caco-2 intestinal permeability and lipophilicity
- Accepts multiple SMILES strings per request

### Drug–Target Interaction
Binding affinity prediction between a small-molecule drug and a protein target:
- Returns binding affinity score, confidence (0–1), interaction strength label, and clinical relevance category
- Configurable drug encoding (MPNN, CNN, Morgan, Daylight, rdkit_2d_normalized)
- Configurable target encoding (CNN, Transformer, AAC, PseAAC, Conjoint_triad)

### Molecular Docking (DiffDock)
Diffusion-based blind molecular docking — no binding-box required:
- Takes a protein amino-acid sequence and a ligand SMILES
- Returns multiple ranked binding poses with confidence scores and estimated ΔG
- Outputs full PDB-format protein structure for downstream visualisation

### Pose Rescoring (GNINA)
CNN-based rescoring of DiffDock poses using the GNINA neural network:
- Re-ranks poses by minimizedAffinity (kcal/mol), CNNscore (0–1), and CNNaffinity (predicted pKi/pKd)
- Typically called immediately after Molecular Docking

### Retrosynthesis
AI-planned multi-step backward synthesis routes:
- Finds feasible synthetic pathways from a target molecule to purchasable starting materials
- Each route annotated with feasibility score, SA score, overall yield, step-by-step conditions and confidence

---

## Timeouts

| Task | Timeout |
|------|---------|
| Molecule Generation | 120 s |
| Property Prediction | 120 s |
| Drug–Target Interaction | 120 s |
| Molecular Docking (DiffDock) | 300 s |
| Pose Rescoring (GNINA) | 300 s |
| Retrosynthesis | 120 s |

---

## Error Codes

| HTTP Code | Meaning | Resolution |
|-----------|---------|------------|
| 401 | Missing API key | Add `X-API-Key` or `Authorization: Bearer` header |
| 403 | Invalid API key | Check key value; contact your administrator |
| 500 | Server misconfiguration | `HF_TOKEN` not set — contact support |
| 4xx / 5xx (HF) | Upstream model error | Check response `detail`; retry after 30 s if model is cold |

---

## Request Access

Contact info@diskoverdiagnostics.com to receive a partner API key.

---

## License

Copyright Drug Discovery API  
All rights reserved.

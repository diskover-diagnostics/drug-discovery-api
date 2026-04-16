# Drug Discovery API — Partner Pack

Version: 1.0  
Last Updated: April 2026

---

## What is the Drug Discovery API?

The Drug Discovery API is a set of six AI-powered computational biology tasks delivered via a single authenticated REST service.

Each task is a dedicated endpoint. All six endpoints share the same base URL and authentication layer — one partner API key grants access to all licensed tasks.

---

## The Six Tasks

### 1. Molecule Generation — `/molecule-generation`

**What it does:**
- Completes masked SMILES tokens to generate novel candidate drug molecules
- Returns top-K completions ranked by model quality score
- Filters candidates by structural validity and Lipinski's Rule-of-Five drug-likeness

**Model:** ChemBERTa-style masked-SMILES language model

**Use cases:**
- Lead generation from known scaffolds
- Bioisostere exploration
- Fragment growing and SMILES scaffold decoration

**Inputs:** Masked SMILES string (with `<mask>` token), top_k count, validity filter flag  
**Endpoint:** `POST /molecule-generation`

---

### 2. Property Prediction — `/property-prediction`

**What it does:**
- Predicts up to 8 ADMET and physicochemical properties for any number of SMILES strings
- Classification properties output a 0–1 probability; regression properties output a normalised −1 to 0 score

**Model:** MTL-BERT (Zhang et al. 2022, *Research* DOI: 10.34133/research.0004) — multitask BERT pretrained on 1.7 M ChEMBL molecules, fine-tuned on 60 ADMET datasets

**Properties supported:**

| Property | Type | Score range | >threshold means |
|----------|------|-------------|-----------------|
| Solubility | Classification | 0–1 | Predicted aqueous-soluble |
| Toxicity | Classification | 0–1 | Predicted mutagenic / toxic (AMES) |
| Bioavailability | Classification | 0–1 | Oral bioavailability > 20% |
| BBB Penetration | Classification | 0–1 | Crosses blood-brain barrier |
| CYP Inhibition | Classification | 0–1 per isoform | Inhibits CYP3A4/2D6/2C9/2C19/1A2 |
| hERG Cardiotoxicity | Classification | 0–1 | hERG channel inhibitor |
| Caco-2 Permeability | Regression | −1 to 0 | Closer to 0 = higher permeability |
| Lipophilicity | Regression | −1 to 0 | Closer to 0 = more lipophilic |

**Use cases:**
- Early ADMET triage of generated molecules
- Lead optimisation safety profiling
- Multi-parameter optimisation (MPO) scoring

**Inputs:** List of SMILES strings, list of desired property tasks  
**Endpoint:** `POST /property-prediction`

---

### 3. Drug–Target Interaction — `/drug-target-interaction`

**What it does:**
- Predicts the binding affinity between a small-molecule drug (SMILES) and a protein target (amino-acid sequence)
- Returns binding affinity score, model confidence, qualitative interaction strength, and indicative clinical relevance

**Model:** DeepPurpose DTI framework with configurable drug and target encoders

**Drug encoding options:** MPNN, CNN, Morgan, Daylight, rdkit_2d_normalized  
**Target encoding options:** CNN, Transformer, AAC, PseAAC, Conjoint_triad

**Use cases:**
- Virtual screening of compound libraries against a target
- Drug repurposing candidate evaluation
- Target deconvolution

**Inputs:** Drug SMILES, protein amino-acid sequence, target name, encoding choices  
**Endpoint:** `POST /drug-target-interaction`

---

### 4. Molecular Docking — `/diffdock-hf`

**What it does:**
- Performs diffusion-based **blind** molecular docking — no binding box or crystal structure required
- Takes a protein amino-acid sequence and a ligand SMILES
- Returns multiple ranked binding poses with confidence scores and estimated ΔG (kcal/mol)
- Also returns PDB-format protein structure for 3D visualisation

**Model:** DiffDock — diffusion-based molecular docking (Corso et al. 2023)

**Key facts:**
- Confidence score range: ≈ −5 to +5; values >0 indicate a likely near-native pose (RMSD < 2 Å)
- Estimated ΔG is an empirical proxy: ≈ −1.5 × confidence − 6.0 kcal/mol; **not** a true binding free energy
- Timeout: 300 s (5 minutes)

**Use cases:**
- Structure-based virtual screening without a crystal structure
- Binding pose prediction for downstream GNINA rescoring
- Hit-to-lead docking studies

**Inputs:** Ligand SMILES, protein amino-acid sequence, complex label name, samples per complex, inference steps  
**Endpoint:** `POST /diffdock-hf`

---

### 5. Pose Rescoring — `/gnina-hf`

**What it does:**
- CNN-based rescoring of DiffDock binding poses using GNINA's neural network
- Re-ranks poses by minimizedAffinity (kcal/mol), CNNscore (0–1), and CNNaffinity (predicted pKi/pKd)
- Accepts the full DiffDock JSON output directly — no manual data transformation needed

**Model:** GNINA (McNutt et al. 2021) — convolutional neural network trained on protein-ligand complexes

**Score interpretation:**

| Score | Range | Meaning |
|-------|-------|---------|
| minimizedAffinity | kcal/mol (negative) | More negative = stronger predicted binding; typical drug range −4 to −12 |
| CNNscore | 0–1 | Probability the pose is an active binder; >0.5 = likely active |
| CNNaffinity | pKi/pKd | −log₁₀(Kd/Ki); 6 ≈ 1 µM potency, 9 ≈ 1 nM potency |

**Use cases:**
- Refining and re-ranking DiffDock pose predictions
- Selecting the best binding pose for MD simulation
- Second-stage scoring in a virtual screening pipeline

**Inputs:** Full DiffDock-HF JSON response, number of top poses to rescore, GNINA options (score_only, seed, cpu)  
**Endpoint:** `POST /gnina-hf`

---

### 6. Retrosynthesis — `/retrosynthesis`

**What it does:**
- Plans multi-step backward synthetic routes from a target molecule to purchasable starting materials
- Returns feasibility-ranked routes with step-by-step conditions, yield estimates, and SA scores

**Model:** GLN / OpenRetro retrosynthesis AI

**Output per route:**

| Field | Meaning |
|-------|---------|
| feasibility_score | 0–1; higher = more synthetically feasible |
| synthetic_accessibility (SA) | 1–10; 1 = trivially easy, 10 = extremely difficult; drug candidates typically 1–4 |
| overall_yield | Compounded yield estimate across all steps |
| estimated_cost | Indicative reagent cost |
| starting_materials | List of SMILES for purchasable precursors |

**Use cases:**
- Synthetic feasibility assessment during lead optimisation
- Route scouting before medicinal chemistry synthesis
- Cost and timeline estimation for early drug candidate synthesis

**Inputs:** Target molecule SMILES, max search depth, minimum route confidence  
**Endpoint:** `POST /retrosynthesis`

---

## Recommended Pipeline

```
1. Molecule Generation      — Generate candidates from a masked scaffold
        ↓
2. Property Prediction      — ADMET triage: filter by solubility, toxicity, BBB, hERG
        ↓
3. Drug–Target Interaction  — Rank survivors by predicted binding affinity
        ↓
4. Molecular Docking        — Blind docking of top candidates against the target protein
        ↓
5. Pose Rescoring           — GNINA CNN re-ranking of DiffDock poses
        ↓
6. Retrosynthesis           — Synthetic route planning for confirmed hits
```

---

## Authentication

```
POST https://drug-discovery-orchestrator.fly.dev/<task-endpoint>
X-API-Key: YOUR_PARTNER_API_KEY
Content-Type: application/json
```

Or equivalently:

```
Authorization: Bearer YOUR_PARTNER_API_KEY
```

One key works for all six tasks.

---

## Architecture

```
Partner Platform
      ↓  POST /<task>  (inputs + API key)
Drug Discovery Orchestrator (Fly.io)
      ↓  SHA-256 key hash verification
      ↓  routes by endpoint path
HF Inference Endpoints (one per task)
      ↓  AI model inference
Drug Discovery Orchestrator
      ↓  response
Partner Platform
```

Partners never interact directly with HuggingFace. No HF token is needed on the partner side.

---

## Getting Started

### 1. Receive API Key

Your key is provisioned by an administrator and grants access to all licensed task endpoints.

### 2. Test Health Endpoint

```bash
curl https://drug-discovery-orchestrator.fly.dev/health
```

Confirm `"ok": true` and that all endpoints are listed.

### 3. Run First Request

Import `postman_collection.json` and set:
- `base_url` = `https://drug-discovery-orchestrator.fly.dev`
- `partner_api_key` = your key

Or run `curl_examples.sh` with `PARTNER_API_KEY` set as an environment variable.

### 4. Integrate

Follow `integration-guide.md` for:
- Full field-by-field input reference per task
- Response field descriptions
- Recommended pipeline sequencing (Docking → Rescoring)
- Batch processing patterns

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

## Error Handling

| Scenario | Detection | Action |
|----------|-----------|--------|
| Missing API key | HTTP 401 | Add `X-API-Key` or `Authorization: Bearer` header |
| Invalid API key | HTTP 403 | Verify key value; contact administrator |
| Server misconfiguration | HTTP 500 | `HF_TOKEN` not configured — contact admin |
| HF model unavailable | 4xx/5xx from HF | Retry after 30 seconds |

---

## Integration Resources

| Resource | File |
|----------|------|
| Integration Guide | integration-guide.md |
| OpenAPI Specification | openapi.yaml |
| Postman Collection | postman_collection.json |
| cURL Examples | curl_examples.sh |

---

## Typical Integration Timeline

| Phase | Duration |
|-------|----------|
| API test & validation | 1–2 days |
| Data mapping & SMILES preparation | 3–5 days |
| Pipeline integration | 1–2 weeks |
| Testing & go-live | 1 week |
| **Total** | **2–4 weeks** |

---

## Support

For technical integration questions, include:
- Task name (e.g., `property-prediction`, `diffdock-hf`)
- Request body (redact API key)
- Response body or Fly.io log excerpt

---

## License

Copyright Drug Discovery API  
All rights reserved.  
Proprietary and confidential — partner use only.

# Drug Discovery API — Python Examples

Python examples for all six Drug Discovery API tasks.

Base URL: `https://drug-discovery-orchestrator.fly.dev`

---

## Prerequisites

**Python 3.8+** and `requests`:

```bash
pip install requests
```

No other dependencies required. All examples use only the standard library plus `requests`.

---

## Setup

Set your partner API key as an environment variable before running any example:

```bash
# Linux / macOS
export PARTNER_API_KEY="your_key_here"

# Windows CMD
set PARTNER_API_KEY=your_key_here

# Windows PowerShell
$env:PARTNER_API_KEY="your_key_here"
```

All scripts import the key from `config.py`. If the variable is not set, the placeholder `YOUR_PARTNER_API_KEY` is used and all requests will return HTTP 403.

---

## File Structure

```
python_examples/
├── config.py                      # Shared config: BASE_URL, HEADERS, molecule constants
├── 01_molecule_generation.py      # Task 1 — generate candidates from masked SMILES
├── 02_property_prediction.py      # Task 2 — ADMET property prediction (batch)
├── 03_drug_target_interaction.py  # Task 3 — binding affinity prediction
├── 04_molecular_docking.py        # Task 4 — DiffDock blind docking
├── 05_pose_rescoring.py           # Task 5 — GNINA CNN pose rescoring
├── 06_retrosynthesis.py           # Task 6 — retrosynthetic route planning
└── 07_full_pipeline.py            # Full end-to-end pipeline (Tasks 1 → 6)
```

---

## Running Individual Examples

Run each script from the `python_examples/` directory:

```bash
cd drug-discovery-api/python_examples

python 01_molecule_generation.py
python 02_property_prediction.py
python 03_drug_target_interaction.py
python 04_molecular_docking.py
python 05_pose_rescoring.py          # requires output_04_diffdock.json (run 04 first)
python 06_retrosynthesis.py
python 07_full_pipeline.py           # runs all 6 tasks sequentially
```

---

## Task Descriptions

### Task 1 — Molecule Generation (`01_molecule_generation.py`)

Fills `<mask>` tokens in a partial SMILES string to generate novel drug-like candidates.

**Input:** Masked SMILES string  
**Output:** Top-K completions with Lipinski drug-likeness and molecular descriptors

```python
from 01_molecule_generation import molecule_generation

result = molecule_generation(
    masked_smiles="CC(C)Cc1ccc(C(C)<mask>C(=O)O)cc1",
    top_k=5,
    filter_valid=True,
)
for mol in result["completed_molecules"]:
    print(mol["completed_smiles"], mol["score"], mol["drug_like"])
```

---

### Task 2 — Property Prediction (`02_property_prediction.py`)

Predicts up to 8 ADMET and physicochemical properties for a batch of SMILES strings.

**Score types:**
- Classification (0–1): `solubility`, `toxicity`, `bioavailability`, `bbb_penetration`, `cyp_inhibition`, `herg_cardiotoxicity`. **>0.5 = property present**
- Regression (−1 to 0): `caco2_permeability`, `lipophilicity`. **Closer to 0 = more favourable**

```python
from 02_property_prediction import property_prediction

results = property_prediction(
    smiles_list=["CC(=O)Oc1ccccc1C(=O)O", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"],
    tasks=["solubility", "toxicity", "herg_cardiotoxicity"],
)
for entry in results:
    props = entry["properties"]
    print(entry["smiles"], props["solubility"], props["toxicity"])
```

---

### Task 3 — Drug–Target Interaction (`03_drug_target_interaction.py`)

Predicts binding affinity between a drug (SMILES) and a protein target (amino-acid sequence).

**Output interpretation:**
- `binding_affinity`: lower (more negative) = stronger binding
- `confidence`: 0–1, model certainty
- `interaction_strength`: Strong / Moderate / Weak

```python
from 03_drug_target_interaction import drug_target_interaction

result = drug_target_interaction(
    drug_smiles="CC(=O)Oc1ccccc1C(=O)O",
    target_sequence="MLARALLLCAVLALSHTANPCC...",
    target_name="COX-2",
    drug_encoding="MPNN",
    target_encoding="CNN",
)
pred = result["binding_prediction"]
print(pred["binding_affinity"], pred["interaction_strength"])
```

Available encodings:
- **Drug:** `MPNN`, `CNN`, `Morgan`, `Daylight`, `rdkit_2d_normalized`
- **Target:** `CNN`, `Transformer`, `AAC`, `PseAAC`, `Conjoint_triad`

---

### Task 4 — Molecular Docking (`04_molecular_docking.py`)

Diffusion-based blind molecular docking — no binding box required.

**Score interpretation:**
- `confidence` ≈ −5 to +5: **>0 = likely near-native** (RMSD < 2 Å vs crystal structure)
- `estimated_dG_kcal_mol`: empirical proxy only — **not a true binding free energy**

**Timeout: 300 seconds.** The script saves `output_04_diffdock.json` — needed by Task 5.

```python
from 04_molecular_docking import molecular_docking

result = molecular_docking(
    ligand_smiles="CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    protein_sequence="MENFQKVEKIGEGTYGVVYK...",
    complex_name="cdk2_ibuprofen",
    samples_per_complex=3,
    inference_steps=10,
)
for pose in result["poses"]:
    print(pose["rank"], pose["confidence"], pose["estimated_dG_kcal_mol"])
```

---

### Task 5 — Pose Rescoring (`05_pose_rescoring.py`)

CNN-based rescoring of DiffDock poses using GNINA. Accepts the full DiffDock JSON response.

**Run Task 4 first** to generate `output_04_diffdock.json`.

**Score interpretation:**

| Score | Range | Meaning |
|-------|-------|---------|
| `minimizedAffinity` | kcal/mol (negative) | More negative = stronger binding; drug range −4 to −12 |
| `CNNscore` | 0–1 | **>0.5 = likely active binder** |
| `CNNaffinity` | pKi/pKd | 6 ≈ 1 µM, 9 ≈ 1 nM potency |

```python
from 05_pose_rescoring import pose_rescoring
import json

with open("output_04_diffdock.json") as f:
    diffdock_output = json.load(f)

result = pose_rescoring(
    diffdock_output=diffdock_output,
    top_n_poses=3,
    score_only=True,
)
print(result["best_CNNscore"], result["best_minimizedAffinity"])
```

---

### Task 6 — Retrosynthesis (`06_retrosynthesis.py`)

AI-planned multi-step backward synthetic route planning from target molecule to purchasable starting materials.

**Score interpretation:**
- `feasibility_score` (0–1): higher = more synthetically feasible
- `synthetic_accessibility` (SA score 1–10): drug candidates typically 1–4
- `overall_yield`: compounded yield estimate across all steps

```python
from 06_retrosynthesis import retrosynthesis

result = retrosynthesis(
    target_smiles="CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
    max_depth=5,
    min_confidence=0.3,
)
for route in result["synthesis_routes"]:
    print(route["route_id"], route["feasibility_score"], route["overall_yield"])
    for step in route["steps"]:
        print(f"  Step {step['step']}: {step['reaction_type']} — conf={step['confidence']:.2f}")
```

---

### Task 7 — Full Pipeline (`07_full_pipeline.py`)

Chains all six tasks in sequence with ADMET filtering and DTI-based candidate selection.

**Pipeline flow:**
```
1. Generate candidates (masked SMILES → top-5 completions)
          ↓
2. ADMET triage (filter: toxicity <0.5, hERG <0.5, solubility >0.3)
          ↓
3. DTI ranking (sort survivors by binding affinity — most negative first)
          ↓
4. Dock top candidate (DiffDock, 3 poses, 10 inference steps)
          ↓
5. Rescore poses (GNINA CNN)
          ↓
6. Retrosynthesis (top candidate → synthetic routes)
```

**Output files:**
- `pipeline_output.json` — complete results from all 6 steps
- `pipeline_top_candidate.txt` — one-line summary of best candidate

```python
from 07_full_pipeline import run_pipeline
from config import IBUPROFEN_MASKED, CDK2_SEQUENCE

output = run_pipeline(
    masked_smiles=IBUPROFEN_MASKED,
    protein_sequence=CDK2_SEQUENCE,
    target_name="CDK2",
)
```

---

## Timeouts

| Task | Script | Timeout |
|------|--------|---------|
| Tasks 1–3, 6 | `01–03`, `06` | 120 s |
| Tasks 4–5 | `04`, `05` | 300 s |
| Full pipeline | `07` | varies per step |

---

## Error Handling

All scripts raise `requests.exceptions.HTTPError` on HTTP 4xx/5xx responses.

`07_full_pipeline.py` includes automatic retry logic (3 attempts, 30 s back-off on 5xx).

**Common errors:**

| HTTP Code | Cause | Fix |
|-----------|-------|-----|
| 401 | Missing API key | Set `PARTNER_API_KEY` env variable |
| 403 | Invalid API key | Verify key value |
| 500 | HF_TOKEN not set | Contact administrator |
| 5xx from HF | Model cold-starting | Retry after 30 s |

---

## Output Files

Each script saves raw JSON output:

| File | Created by |
|------|------------|
| `output_01_molecule_generation.json` | `01_molecule_generation.py` |
| `output_02_property_prediction.json` | `02_property_prediction.py` |
| `output_03_dti.json` | `03_drug_target_interaction.py` |
| `output_04_diffdock.json` | `04_molecular_docking.py` — **required by Task 5** |
| `output_05_gnina.json` | `05_pose_rescoring.py` |
| `output_06_retrosynthesis.json` | `06_retrosynthesis.py` |
| `pipeline_output.json` | `07_full_pipeline.py` |
| `pipeline_top_candidate.txt` | `07_full_pipeline.py` |

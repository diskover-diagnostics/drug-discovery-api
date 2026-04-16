#!/usr/bin/env bash
# Drug Discovery API — cURL examples for all 6 tasks
# Set PARTNER_API_KEY before running:
#   export PARTNER_API_KEY="your_key_here"

PARTNER_API_KEY="${PARTNER_API_KEY:-YOUR_PARTNER_API_KEY}"
BASE="https://drug-discovery-orchestrator.fly.dev"

echo "===== Drug Discovery API — cURL Examples ====="

# ---------------------------------------------------------------------------
# Health check (no auth required)
# ---------------------------------------------------------------------------
echo -e "\n--- Health Check ---"
curl -s "$BASE/health" | python3 -m json.tool

# ---------------------------------------------------------------------------
# 1. Molecule Generation
# ---------------------------------------------------------------------------
echo -e "\n--- Task 1: Molecule Generation ---"
curl -s "$BASE/molecule-generation" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "masked_smiles": "CC(C)Cc1ccc(C(C)<mask>C(=O)O)cc1",
      "top_k": 5,
      "filter_valid": true
    }
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 2. Property Prediction — full 8-property ADMET profile (Aspirin)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 2: Property Prediction (Aspirin) ---"
curl -s "$BASE/property-prediction" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "smiles_list": ["CC(=O)Oc1ccccc1C(=O)O"],
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
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 2b. Property Prediction — batch (Aspirin + Ibuprofen + Naphthalene)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 2b: Property Prediction (batch) ---"
curl -s "$BASE/property-prediction" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "smiles_list": [
        "CC(=O)Oc1ccccc1C(=O)O",
        "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "c1ccc2ccccc2c1"
      ],
      "tasks": ["solubility", "toxicity", "bioavailability", "herg_cardiotoxicity"]
    },
    "parameters": {}
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 3. Drug–Target Interaction (Aspirin vs COX-2, MPNN+CNN)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 3: Drug-Target Interaction (Aspirin vs COX-2) ---"
curl -s "$BASE/drug-target-interaction" \
  -H "X-API-Key: $PARTNER_API_KEY" \
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
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 3b. Drug–Target Interaction (Ibuprofen vs CDK2, Morgan+Transformer)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 3b: Drug-Target Interaction (Ibuprofen vs CDK2) ---"
curl -s "$BASE/drug-target-interaction" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "drug_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "target_sequence": "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFSRILLGTPNEAIWPDIVYLPDFKPSFPQWRRKDLSQVVPSLDPRGIDLLDKLLAKNLVEDAHSLTSGSTPTLSSSAGSVTPMSTKVLV",
      "target_name": "CDK2",
      "drug_encoding": "Morgan",
      "target_encoding": "Transformer"
    },
    "parameters": {}
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 4. Molecular Docking — DiffDock (Ibuprofen vs CDK2)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 4: Molecular Docking — DiffDock (Ibuprofen vs CDK2) ---"
DIFFDOCK_RESPONSE=$(curl -s "$BASE/diffdock-hf" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "ligand_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "protein_sequence": "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFSRILLGTPNEAIWPDIVYLPDFKPSFPQWRRKDLSQVVPSLDPRGIDLLDKLLAKNLVEDAHSLTSGSTPTLSSSAGSVTPMSTKVLV",
      "complex_name": "cdk2_ibuprofen"
    },
    "parameters": {
      "samples_per_complex": 2,
      "inference_steps": 4
    }
  }')

echo "$DIFFDOCK_RESPONSE" | python3 -m json.tool

# ---------------------------------------------------------------------------
# 5. Pose Rescoring — GNINA (uses DiffDock output from step 4)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 5: Pose Rescoring — GNINA (rescoring DiffDock output) ---"
echo "$DIFFDOCK_RESPONSE" | python3 -c "
import json, sys
diffdock_output = json.load(sys.stdin)
payload = {
    'inputs': {
        'diffdock_output': diffdock_output,
        'top_n_poses': 2
    },
    'parameters': {
        'score_only': True,
        'seed': 0,
        'cpu': 4
    }
}
print(json.dumps(payload))
" | curl -s "$BASE/gnina-hf" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- | python3 -m json.tool

# ---------------------------------------------------------------------------
# 5b. Pose Rescoring — GNINA (manual JSON — replace diffdock_output inline)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 5b: Pose Rescoring — GNINA (inline JSON example) ---"
curl -s "$BASE/gnina-hf" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "diffdock_output": {
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
        "protein_pdb": "ATOM      1  N   MET A   1      ..."
      },
      "top_n_poses": 2
    },
    "parameters": {
      "score_only": true,
      "seed": 0,
      "cpu": 4
    }
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 6. Retrosynthesis — Celecoxib scaffold
# ---------------------------------------------------------------------------
echo -e "\n--- Task 6: Retrosynthesis (Celecoxib scaffold) ---"
curl -s "$BASE/retrosynthesis" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "target_smiles": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F",
      "max_depth": 5,
      "min_confidence": 0.3
    },
    "parameters": {}
  }' | python3 -m json.tool

# ---------------------------------------------------------------------------
# 6b. Retrosynthesis — Ibuprofen (simple molecule, expect trivial routes)
# ---------------------------------------------------------------------------
echo -e "\n--- Task 6b: Retrosynthesis (Ibuprofen) ---"
curl -s "$BASE/retrosynthesis" \
  -H "X-API-Key: $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "target_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "max_depth": 3,
      "min_confidence": 0.5
    },
    "parameters": {}
  }' | python3 -m json.tool

echo -e "\n===== Done ====="

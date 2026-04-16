"""
Task 3 — Drug–Target Interaction (DTI)
Drug Discovery API Python Example

Predicts binding affinity between a small-molecule drug (SMILES) and a protein
target (amino-acid sequence) using the DeepPurpose framework.

Output interpretation:
  binding_affinity  : lower (more negative) = stronger predicted binding
  confidence        : 0–1, model certainty
  interaction_strength : Strong / Moderate / Weak
  clinical_relevance   : High / Medium / Low (indicative, not clinical)

Usage:
    export PARTNER_API_KEY="your_key"
    python 03_drug_target_interaction.py
"""

import json
import requests
from config import BASE_URL, HEADERS, ASPIRIN_SMILES, IBUPROFEN_SMILES, COX2_SEQUENCE, CDK2_SEQUENCE


def drug_target_interaction(
    drug_smiles: str,
    target_sequence: str,
    target_name: str,
    drug_encoding: str = "MPNN",
    target_encoding: str = "CNN",
) -> dict:
    """
    Predict binding affinity between a drug and a protein target.

    Args:
        drug_smiles:     SMILES string of the drug molecule.
        target_sequence: Single-letter amino-acid sequence of the target protein.
        target_name:     Human-readable label for the target (output label only).
        drug_encoding:   One of: MPNN, CNN, Morgan, Daylight, rdkit_2d_normalized
        target_encoding: One of: CNN, Transformer, AAC, PseAAC, Conjoint_triad

    Returns:
        API response dict with 'binding_prediction' sub-dict.
    """
    payload = {
        "inputs": {
            "drug_smiles": drug_smiles,
            "target_sequence": target_sequence,
            "target_name": target_name,
            "drug_encoding": drug_encoding,
            "target_encoding": target_encoding,
        },
        "parameters": {},
    }

    response = requests.post(
        f"{BASE_URL}/drug-target-interaction",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def print_results(result: dict) -> None:
    pred  = result.get("binding_prediction", {})
    dprops = result.get("drug_properties", {})

    print(f"\n{'='*60}")
    print("DRUG–TARGET INTERACTION RESULTS")
    print(f"{'='*60}")
    print(f"  Drug            : {result.get('drug_smiles', '—')}")
    print(f"  Target          : {result.get('target_name', '—')}  "
          f"(length: {result.get('target_sequence_length', '—')} aa)")
    print(f"  Method          : {pred.get('prediction_method', '—')}")
    print()
    print(f"  Binding Affinity: {pred.get('binding_affinity', '—'):.3f}  "
          f"(more negative = stronger binding)")
    print(f"  Confidence      : {pred.get('confidence', '—'):.3f}  (0–1)")
    print(f"  Strength        : {pred.get('interaction_strength', '—')}")
    print(f"  Clinical Cat.   : {pred.get('clinical_relevance', '—')}")
    print()
    print(f"  Drug MW         : {dprops.get('molecular_weight', '—')}")
    print(f"  Drug LogP       : {dprops.get('logp', '—')}")
    print()


if __name__ == "__main__":
    # --- Example 1: Aspirin vs COX-2 (MPNN + CNN) ---
    print("Example 1: Aspirin vs COX-2  (MPNN drug + CNN target)")
    result1 = drug_target_interaction(
        drug_smiles=ASPIRIN_SMILES,
        target_sequence=COX2_SEQUENCE,
        target_name="COX-2",
        drug_encoding="MPNN",
        target_encoding="CNN",
    )
    print_results(result1)

    # --- Example 2: Ibuprofen vs CDK2 (Morgan + Transformer) ---
    print("Example 2: Ibuprofen vs CDK2  (Morgan drug + Transformer target)")
    result2 = drug_target_interaction(
        drug_smiles=IBUPROFEN_SMILES,
        target_sequence=CDK2_SEQUENCE,
        target_name="CDK2",
        drug_encoding="Morgan",
        target_encoding="Transformer",
    )
    print_results(result2)

    # Save
    with open("output_03_dti.json", "w") as f:
        json.dump({"aspirin_cox2": result1, "ibuprofen_cdk2": result2}, f, indent=2)
    print("Raw output saved → output_03_dti.json")

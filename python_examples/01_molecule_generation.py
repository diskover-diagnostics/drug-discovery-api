"""
Task 1 — Molecule Generation
Drug Discovery API Python Example

Fills <mask> tokens in a partial SMILES string to generate novel drug-like candidates.
Returns top-K completions with Lipinski drug-likeness and molecular descriptors.

Usage:
    export PARTNER_API_KEY="your_key"
    python 01_molecule_generation.py
"""

import json
import requests
from config import BASE_URL, HEADERS, IBUPROFEN_MASKED


def molecule_generation(
    masked_smiles: str,
    top_k: int = 5,
    filter_valid: bool = True,
) -> dict:
    """
    Generate drug-like candidate molecules by completing a masked SMILES string.

    Args:
        masked_smiles: SMILES string containing one or more <mask> tokens.
        top_k:         Number of top completions to return (1–20).
        filter_valid:  If True, return only chemically valid completions.

    Returns:
        API response dict with 'completed_molecules' list.
    """
    payload = {
        "inputs": {
            "masked_smiles": masked_smiles,
            "top_k": top_k,
            "filter_valid": filter_valid,
        }
    }

    response = requests.post(
        f"{BASE_URL}/molecule-generation",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def print_results(result: dict) -> None:
    stats = result.get("statistics", {})
    molecules = result.get("completed_molecules", [])

    print(f"\n{'='*60}")
    print("MOLECULE GENERATION RESULTS")
    print(f"{'='*60}")
    print(f"  Total generated : {stats.get('total_completions', '—')}")
    print(f"  Valid molecules : {stats.get('valid_molecules', '—')}")
    print(f"  Drug-like (Ro5) : {stats.get('drug_like_molecules', '—')}")
    print()

    for i, mol in enumerate(molecules, 1):
        props = mol.get("properties", {})
        violations = mol.get("lipinski_violations", "—")
        flag = "✓" if mol.get("drug_like") else "✗"

        print(f"  [{i}] {flag} {mol['completed_smiles']}")
        print(f"       Score     : {mol.get('score', 0):.4f}")
        print(f"       Lipinski  : {violations} violation(s)")
        print(f"       MW={props.get('molecular_weight','—')}  "
              f"LogP={props.get('logp','—')}  "
              f"HBD={props.get('hbd','—')}  "
              f"HBA={props.get('hba','—')}  "
              f"TPSA={props.get('tpsa','—')}")
        print()


if __name__ == "__main__":
    print(f"Masked SMILES : {IBUPROFEN_MASKED}")
    print("Sending request to /molecule-generation ...")

    result = molecule_generation(
        masked_smiles=IBUPROFEN_MASKED,
        top_k=5,
        filter_valid=True,
    )

    print_results(result)

    # Save raw JSON for inspection
    with open("output_01_molecule_generation.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Raw output saved → output_01_molecule_generation.json")

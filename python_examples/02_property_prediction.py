"""
Task 2 — Property Prediction (ADMET)
Drug Discovery API Python Example

Predicts up to 8 ADMET and physicochemical properties for one or more SMILES strings.
Model: MTL-BERT (Zhang et al. 2022, DOI: 10.34133/research.0004)

Score types:
  Classification (solubility, toxicity, bioavailability, BBB, CYP, hERG): 0–1 probability
    > 0.5 = property is predicted present
  Regression (Caco-2, lipophilicity): normalised −1 to 0
    Closer to 0 = more favourable

Usage:
    export PARTNER_API_KEY="your_key"
    python 02_property_prediction.py
"""

import json
import requests
from config import BASE_URL, HEADERS, ASPIRIN_SMILES, IBUPROFEN_SMILES

ALL_TASKS = [
    "solubility",
    "toxicity",
    "bioavailability",
    "bbb_penetration",
    "cyp_inhibition",
    "herg_cardiotoxicity",
    "caco2_permeability",
    "lipophilicity",
]


def property_prediction(smiles_list: list, tasks: list = None) -> list:
    """
    Predict ADMET and physicochemical properties for a batch of SMILES strings.

    Args:
        smiles_list: List of valid SMILES strings.
        tasks:       List of property task names (default: all 8).

    Returns:
        List of dicts, one per input SMILES, each with 'properties' and
        'molecular_descriptors' sub-dicts.
    """
    if tasks is None:
        tasks = ALL_TASKS

    payload = {
        "inputs": {
            "smiles_list": smiles_list,
            "tasks": tasks,
        },
        "parameters": {},
    }

    response = requests.post(
        f"{BASE_URL}/property-prediction",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def print_results(results: list) -> None:
    print(f"\n{'='*60}")
    print("PROPERTY PREDICTION RESULTS")
    print(f"{'='*60}")

    for entry in results:
        smiles = entry.get("smiles", "—")
        props  = entry.get("properties", {})
        desc   = entry.get("molecular_descriptors", {})

        print(f"\n  SMILES: {smiles}")
        print(f"  ─────────────────────────────────────────────")

        # Molecular descriptors
        print(f"  Descriptors:")
        print(f"    MW={desc.get('molecular_weight','—')}  "
              f"LogP={desc.get('logp','—')}  "
              f"HBD={desc.get('hbd','—')}  "
              f"HBA={desc.get('hba','—')}  "
              f"TPSA={desc.get('tpsa','—')}")

        # Classification properties (0–1; >0.5 = present)
        print(f"\n  Properties (0–1 classification, >0.5 = positive):")
        for key in ["solubility", "toxicity", "bioavailability",
                    "bbb_penetration", "herg_cardiotoxicity"]:
            val = props.get(key)
            if val is not None:
                flag = "⚠" if (key == "toxicity" or key == "herg_cardiotoxicity") and val > 0.5 else (
                    "✓" if val > 0.5 else "✗"
                )
                print(f"    {flag} {key:<22} {val:.3f}")

        # CYP isoform inhibition
        cyp = props.get("cyp_inhibition")
        if cyp:
            print(f"\n  CYP Inhibition (>0.5 = inhibitor):")
            for iso, val in cyp.items():
                flag = "⚠" if val > 0.5 else "  "
                print(f"    {flag} {iso:<10} {val:.3f}")

        # Regression properties (−1 to 0; closer to 0 = better)
        print(f"\n  Regression properties (−1 to 0; closer to 0 = better):")
        for key in ["caco2_permeability", "lipophilicity"]:
            val = props.get(key)
            if val is not None:
                print(f"    {key:<22} {val:.3f}")

    print()


if __name__ == "__main__":
    smiles_batch = [ASPIRIN_SMILES, IBUPROFEN_SMILES]
    print(f"Predicting ADMET for {len(smiles_batch)} molecules ...")
    print(f"  1. {ASPIRIN_SMILES}  (Aspirin)")
    print(f"  2. {IBUPROFEN_SMILES}  (Ibuprofen)")

    results = property_prediction(
        smiles_list=smiles_batch,
        tasks=ALL_TASKS,
    )

    print_results(results)

    with open("output_02_property_prediction.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Raw output saved → output_02_property_prediction.json")

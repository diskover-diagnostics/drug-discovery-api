"""
Task 4 — Molecular Docking (DiffDock-HF)
Drug Discovery API Python Example

Diffusion-based blind molecular docking — no binding box or crystal structure required.
Returns multiple ranked binding poses with confidence scores and estimated ΔG.

Score interpretation:
  confidence          : ≈ −5 to +5. >0 = likely near-native pose (RMSD < 2 Å)
  estimated_dG_kcal_mol: empirical proxy only (≈ −1.5 × confidence − 6.0). NOT a true binding free energy.

Timeout: 300 s (5 minutes). Use timeout=300 in requests.

Usage:
    export PARTNER_API_KEY="your_key"
    python 04_molecular_docking.py
"""

import json
import requests
from config import BASE_URL, HEADERS, IBUPROFEN_SMILES, CDK2_SEQUENCE


def molecular_docking(
    ligand_smiles: str,
    protein_sequence: str,
    complex_name: str = "complex",
    samples_per_complex: int = 2,
    inference_steps: int = 4,
) -> dict:
    """
    Run diffusion-based blind molecular docking (DiffDock).

    Args:
        ligand_smiles:        SMILES string of the ligand / drug molecule.
        protein_sequence:     Protein amino-acid sequence (single-letter; FASTA accepted).
        complex_name:         Human-readable label for this protein-ligand complex.
        samples_per_complex:  Number of binding poses to generate (1–10).
        inference_steps:      Diffusion inference steps (1–50); more = higher quality, slower.

    Returns:
        API response dict with 'poses' list and 'protein_pdb' string.
    """
    payload = {
        "inputs": {
            "ligand_smiles": ligand_smiles,
            "protein_sequence": protein_sequence,
            "complex_name": complex_name,
        },
        "parameters": {
            "samples_per_complex": samples_per_complex,
            "inference_steps": inference_steps,
        },
    }

    response = requests.post(
        f"{BASE_URL}/diffdock-hf",
        headers=HEADERS,
        json=payload,
        timeout=300,          # 5-minute timeout for docking
    )
    response.raise_for_status()
    return response.json()


def print_results(result: dict) -> None:
    poses = result.get("poses", [])
    lprops = result.get("ligand_properties", {})

    print(f"\n{'='*60}")
    print("MOLECULAR DOCKING RESULTS (DiffDock)")
    print(f"{'='*60}")
    print(f"  Complex         : {result.get('complex_name', '—')}")
    print(f"  Ligand          : {result.get('ligand_smiles', '—')}")
    print(f"  Poses generated : {result.get('num_poses', 0)}")
    print(f"  Best confidence : {result.get('best_confidence', '—'):.3f}"
          f"  (>0 = likely near-native)")
    print(f"  Best est. ΔG    : {result.get('best_estimated_dG_kcal_mol', '—'):.2f} kcal/mol"
          f"  (empirical proxy)")
    print()

    print(f"  Ligand:  MW={lprops.get('molecular_weight','—')}  "
          f"LogP={lprops.get('logp','—')}  "
          f"HBD={lprops.get('hbd','—')}  "
          f"HBA={lprops.get('hba','—')}")
    print()

    print(f"  {'Rank':<6} {'Confidence':>12} {'Est. ΔG (kcal/mol)':>20}  Centroid (x, y, z)")
    print(f"  {'─'*70}")
    for pose in poses:
        xyz = pose.get("pose_centroid_xyz", {})
        print(f"  {pose.get('rank','?'):<6} "
              f"{pose.get('confidence', 0):>12.3f} "
              f"{pose.get('estimated_dG_kcal_mol', 0):>20.2f}  "
              f"({xyz.get('x','?')}, {xyz.get('y','?')}, {xyz.get('z','?')})")

    pdb_preview = result.get("protein_pdb", "")
    print(f"\n  protein_pdb: {len(pdb_preview)} characters  "
          f"(first 80: {pdb_preview[:80]}...)")
    print()

    print("  ⮕ Pass this full response as 'diffdock_output' to /gnina-hf for CNN rescoring")
    print()


if __name__ == "__main__":
    print(f"Docking Ibuprofen → CDK2 ...")
    print(f"  Ligand  : {IBUPROFEN_SMILES}")
    print(f"  Target  : CDK2  ({len(CDK2_SEQUENCE)} aa)")
    print(f"  Timeout : 300 s\n")

    result = molecular_docking(
        ligand_smiles=IBUPROFEN_SMILES,
        protein_sequence=CDK2_SEQUENCE,
        complex_name="cdk2_ibuprofen",
        samples_per_complex=2,
        inference_steps=4,
    )

    print_results(result)

    # Save the full output — needed as input to 05_pose_rescoring.py
    with open("output_04_diffdock.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Raw output saved → output_04_diffdock.json")
    print("Use output_04_diffdock.json as input to 05_pose_rescoring.py")

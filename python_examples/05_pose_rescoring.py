"""
Task 5 — Pose Rescoring (GNINA-HF)
Drug Discovery API Python Example

CNN-based rescoring of DiffDock binding poses using GNINA.
Accepts the full DiffDock JSON response and re-ranks poses by three scores.

Score interpretation:
  minimizedAffinity (kcal/mol): more negative = stronger binding. Drug range: −4 to −12.
  CNNscore (0–1)              : >0.5 = likely active binder.
  CNNaffinity (pKi/pKd)       : 6 ≈ 1 µM potency, 9 ≈ 1 nM potency.

Two usage modes:
  A) Pipe from 04_molecular_docking.py in the same session (recommended for automation).
  B) Load output_04_diffdock.json from disk (for step-by-step testing).

Usage:
    export PARTNER_API_KEY="your_key"
    python 04_molecular_docking.py      # generates output_04_diffdock.json
    python 05_pose_rescoring.py         # loads output_04_diffdock.json
"""

import json
import os
import requests
from config import BASE_URL, HEADERS


def pose_rescoring(
    diffdock_output: dict,
    top_n_poses: int = 2,
    score_only: bool = True,
    seed: int = 0,
    cpu: int = 4,
) -> dict:
    """
    Rescore DiffDock binding poses with GNINA's CNN scoring function.

    Args:
        diffdock_output: Complete JSON response dict from /diffdock-hf.
        top_n_poses:     Number of top DiffDock poses to rescore (1–20).
        score_only:      If True, score without energy minimisation (faster).
        seed:            Random seed for reproducibility.
        cpu:             Number of CPU threads.

    Returns:
        API response dict with 'scored_poses' list and best-score summary.
    """
    payload = {
        "inputs": {
            "diffdock_output": diffdock_output,
            "top_n_poses": top_n_poses,
        },
        "parameters": {
            "score_only": score_only,
            "seed": seed,
            "cpu": cpu,
        },
    }

    response = requests.post(
        f"{BASE_URL}/gnina-hf",
        headers=HEADERS,
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def print_results(result: dict) -> None:
    poses = result.get("scored_poses", [])

    print(f"\n{'='*60}")
    print("POSE RESCORING RESULTS (GNINA)")
    print(f"{'='*60}")
    print(f"  Complex         : {result.get('complex_name', '—')}")
    print(f"  Mode            : {result.get('mode', '—')}")
    print(f"  Poses rescored  : {result.get('num_scored', '—')} / "
          f"{result.get('num_input_poses', '—')} input poses")
    print()
    print(f"  Best minimizedAffinity : {result.get('best_minimizedAffinity', '—'):.2f} kcal/mol")
    print(f"  Best CNNscore          : {result.get('best_CNNscore', '—'):.3f}  "
          f"(>0.5 = likely active)")
    print(f"  Best CNNaffinity       : {result.get('best_CNNaffinity', '—'):.1f}  "
          f"(pKi/pKd; 6 ≈ 1 µM, 9 ≈ 1 nM)")
    print()

    header = f"  {'DiffDock Rank':<14} {'Confidence':>12} {'minAffinity':>12} {'CNNscore':>10} {'CNNaffinity':>12}"
    print(header)
    print(f"  {'─'*62}")
    for pose in poses:
        cnn_flag = " ✓" if pose.get("CNNscore", 0) > 0.5 else "  "
        print(f"  {pose.get('diffdock_rank','?'):<14} "
              f"{pose.get('diffdock_confidence', 0):>12.3f} "
              f"{pose.get('minimizedAffinity', 0):>12.2f} "
              f"{pose.get('CNNscore', 0):>10.3f}{cnn_flag} "
              f"{pose.get('CNNaffinity', 0):>12.1f}")
    print()


if __name__ == "__main__":
    # --- Load DiffDock output from previous step ---
    docking_file = "output_04_diffdock.json"

    if not os.path.exists(docking_file):
        print(f"ERROR: {docking_file} not found.")
        print("Run 04_molecular_docking.py first to generate the DiffDock output.")
        raise SystemExit(1)

    with open(docking_file) as f:
        diffdock_output = json.load(f)

    print(f"Loaded DiffDock output: complex='{diffdock_output.get('complex_name')}'  "
          f"poses={diffdock_output.get('num_poses')}")
    print("Sending to /gnina-hf for CNN rescoring ...\n")

    result = pose_rescoring(
        diffdock_output=diffdock_output,
        top_n_poses=diffdock_output.get("num_poses", 2),
        score_only=True,
        seed=0,
        cpu=4,
    )

    print_results(result)

    with open("output_05_gnina.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Raw output saved → output_05_gnina.json")

"""
Task 6 — Retrosynthesis
Drug Discovery API Python Example

AI-planned multi-step backward synthetic route planning from a target molecule
to purchasable starting materials using the GLN/OpenRetro model.

Output interpretation:
  feasibility_score      : 0–1; higher = more synthetically feasible route.
  synthetic_accessibility: SA score 1–10; drug candidates typically score 1–4.
                           1 = trivially easy, 10 = extremely difficult.
  overall_yield          : compounded yield estimate across all steps.
  steps[].confidence     : 0–1, model certainty for each individual reaction step.

Usage:
    export PARTNER_API_KEY="your_key"
    python 06_retrosynthesis.py
"""

import json
import requests
from config import BASE_URL, HEADERS, IBUPROFEN_SMILES, CELECOXIB_SMILES


def retrosynthesis(
    target_smiles: str,
    max_depth: int = 5,
    min_confidence: float = 0.3,
) -> dict:
    """
    Plan multi-step backward synthetic routes for a target molecule.

    Args:
        target_smiles:   SMILES string of the molecule to synthesise.
        max_depth:       Maximum retrosynthetic steps to search (1–10).
        min_confidence:  Minimum per-step confidence threshold (0.0–1.0).

    Returns:
        API response dict with 'synthesis_routes' list.
    """
    payload = {
        "inputs": {
            "target_smiles": target_smiles,
            "max_depth": max_depth,
            "min_confidence": min_confidence,
        },
        "parameters": {},
    }

    response = requests.post(
        f"{BASE_URL}/retrosynthesis",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def print_results(result: dict) -> None:
    routes = result.get("synthesis_routes", [])

    print(f"\n{'='*60}")
    print("RETROSYNTHESIS RESULTS")
    print(f"{'='*60}")
    print(f"  Target    : {result.get('target_molecule', '—')}")
    print(f"  Routes    : {result.get('routes_found', 0)} found")
    print(f"  Best feas.: {result.get('best_route_feasibility', '—'):.3f}")
    print()

    for route in routes:
        steps = route.get("steps", [])
        print(f"  ── Route {route.get('route_id', '?')} ──────────────────────────────────")
        print(f"     Feasibility    : {route.get('feasibility_score', '—'):.3f}")
        print(f"     SA score       : {route.get('synthetic_accessibility', '—')}  "
              f"(1=easy, 10=hard; drug range 1–4)")
        print(f"     Overall yield  : {route.get('overall_yield', '—')}")
        print(f"     Total steps    : {route.get('total_steps', len(steps))}")
        print(f"     Est. cost      : {route.get('estimated_cost', '—')}")
        print(f"     Est. time      : {route.get('estimated_time', '—')}")
        print()

        sm = route.get("starting_materials", [])
        if sm:
            print(f"     Starting materials:")
            for s in sm:
                print(f"       • {s}")
        print()

        for step in steps:
            cond = step.get("conditions", {})
            print(f"     Step {step.get('step', '?')}: {step.get('reaction_type', '—')}")
            print(f"       Reactants  : {', '.join(step.get('reactants', []))}")
            print(f"       Confidence : {step.get('confidence', '—'):.2f}  |  "
                  f"Yield: {step.get('yield_estimate', '—')}")
            print(f"       Conditions : {cond.get('solvent','—')}  "
                  f"{cond.get('temperature','—')}  "
                  f"cat={cond.get('catalyst','—')}  "
                  f"t={cond.get('time','—')}")
            print()


if __name__ == "__main__":
    # --- Example 1: Ibuprofen (simple, short routes expected) ---
    print("Example 1: Retrosynthesis for Ibuprofen")
    print(f"  SMILES: {IBUPROFEN_SMILES}")
    result1 = retrosynthesis(
        target_smiles=IBUPROFEN_SMILES,
        max_depth=3,
        min_confidence=0.5,
    )
    print_results(result1)

    # --- Example 2: Celecoxib scaffold (more complex) ---
    print("\nExample 2: Retrosynthesis for Celecoxib scaffold")
    print(f"  SMILES: {CELECOXIB_SMILES}")
    result2 = retrosynthesis(
        target_smiles=CELECOXIB_SMILES,
        max_depth=5,
        min_confidence=0.3,
    )
    print_results(result2)

    with open("output_06_retrosynthesis.json", "w") as f:
        json.dump({"ibuprofen": result1, "celecoxib": result2}, f, indent=2)
    print("Raw output saved → output_06_retrosynthesis.json")

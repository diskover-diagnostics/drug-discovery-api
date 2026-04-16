"""
Full Drug Discovery Pipeline
Drug Discovery API Python Example

Chains all six tasks end-to-end:
  1. Molecule Generation      — generate candidates from a masked scaffold
  2. Property Prediction      — ADMET triage; filter out toxic / hERG-positive molecules
  3. Drug–Target Interaction  — rank survivors by predicted binding affinity
  4. Molecular Docking        — blind docking of the top candidate
  5. Pose Rescoring           — GNINA CNN re-ranking of DiffDock poses
  6. Retrosynthesis           — synthetic route planning for the confirmed hit

Usage:
    export PARTNER_API_KEY="your_key"
    python 07_full_pipeline.py

Output files created:
    pipeline_output.json           — complete results from all six tasks
    pipeline_top_candidate.txt     — one-line summary of the best candidate
"""

import json
import time
import requests
from config import (
    BASE_URL, HEADERS,
    IBUPROFEN_MASKED, CDK2_SEQUENCE,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _post(endpoint: str, payload: dict, timeout: int = 120) -> dict:
    """POST to the Drug Discovery API with basic retry logic."""
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=HEADERS, json=payload, timeout=timeout)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
            print(f"  [retry {attempt}/3] HTTP {resp.status_code} from {endpoint} — waiting 30 s ...")
            time.sleep(30)
        except requests.exceptions.Timeout:
            print(f"  [retry {attempt}/3] Timeout on {endpoint} — waiting 10 s ...")
            time.sleep(10)
    raise RuntimeError(f"Failed to reach /{endpoint} after 3 attempts")


def _sep(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── Step 1: Molecule Generation ───────────────────────────────────────────────

def step1_generate(masked_smiles: str, top_k: int = 5) -> list:
    _sep("STEP 1 — Molecule Generation")
    print(f"  Masked SMILES : {masked_smiles}")

    result = _post("molecule-generation", {
        "inputs": {
            "masked_smiles": masked_smiles,
            "top_k": top_k,
            "filter_valid": True,
        }
    })

    molecules = result.get("completed_molecules", [])
    stats = result.get("statistics", {})
    print(f"  Generated     : {stats.get('total_completions')}  |  "
          f"Valid: {stats.get('valid_molecules')}  |  "
          f"Drug-like: {stats.get('drug_like_molecules')}")

    for i, m in enumerate(molecules, 1):
        flag = "✓" if m.get("drug_like") else "✗"
        print(f"  [{i}] {flag} score={m.get('score',0):.3f}  {m['completed_smiles']}")

    return molecules


# ── Step 2: Property Prediction (ADMET triage) ────────────────────────────────

def step2_admet_triage(molecules: list) -> list:
    _sep("STEP 2 — Property Prediction (ADMET Triage)")

    smiles_list = [m["completed_smiles"] for m in molecules]
    result = _post("property-prediction", {
        "inputs": {
            "smiles_list": smiles_list,
            "tasks": ["solubility", "toxicity", "bioavailability", "herg_cardiotoxicity"],
        },
        "parameters": {},
    })

    survivors = []
    for entry in result:
        props = entry.get("properties", {})
        tox   = props.get("toxicity", 1.0)
        herg  = props.get("herg_cardiotoxicity", 1.0)
        sol   = props.get("solubility", 0.0)
        bio   = props.get("bioavailability", 0.0)

        # Pass: low toxicity AND low hERG risk AND reasonable solubility + bioavailability
        passed = (tox < 0.5) and (herg < 0.5) and (sol > 0.3) and (bio > 0.3)
        status = "PASS" if passed else "FAIL"
        print(f"  {status}  {entry['smiles'][:50]}"
              f"  tox={tox:.2f}  herg={herg:.2f}  sol={sol:.2f}  bio={bio:.2f}")

        if passed:
            # Carry ADMET data forward
            matched = next(
                (m for m in molecules if m["completed_smiles"] == entry["smiles"]), {}
            )
            matched["admet"] = props
            survivors.append(matched)

    print(f"\n  Survivors: {len(survivors)} / {len(molecules)} passed ADMET triage")
    return survivors


# ── Step 3: Drug–Target Interaction ──────────────────────────────────────────

def step3_dti(molecules: list, protein_sequence: str, target_name: str) -> list:
    _sep(f"STEP 3 — Drug–Target Interaction (target: {target_name})")

    for mol in molecules:
        result = _post("drug-target-interaction", {
            "inputs": {
                "drug_smiles": mol["completed_smiles"],
                "target_sequence": protein_sequence,
                "target_name": target_name,
                "drug_encoding": "MPNN",
                "target_encoding": "CNN",
            },
            "parameters": {},
        })
        pred = result.get("binding_prediction", {})
        mol["binding_affinity"] = pred.get("binding_affinity", 0.0)
        mol["dti_confidence"]   = pred.get("confidence", 0.0)
        mol["dti_strength"]     = pred.get("interaction_strength", "—")
        print(f"  affinity={mol['binding_affinity']:.3f}  "
              f"conf={mol['dti_confidence']:.2f}  "
              f"({mol['dti_strength']})  "
              f"{mol['completed_smiles'][:50]}")

    # Sort: more negative affinity = stronger binding
    molecules.sort(key=lambda m: m["binding_affinity"])
    top = molecules[0]
    print(f"\n  Top candidate : {top['completed_smiles']}")
    print(f"  Affinity      : {top['binding_affinity']:.3f}  ({top['dti_strength']})")
    return molecules


# ── Step 4: Molecular Docking ─────────────────────────────────────────────────

def step4_docking(smiles: str, protein_sequence: str, complex_name: str) -> dict:
    _sep(f"STEP 4 — Molecular Docking (DiffDock) — {complex_name}")
    print(f"  Ligand  : {smiles}")
    print(f"  Timeout : 300 s  (this may take a few minutes)")

    result = _post("diffdock-hf", {
        "inputs": {
            "ligand_smiles": smiles,
            "protein_sequence": protein_sequence,
            "complex_name": complex_name,
        },
        "parameters": {
            "samples_per_complex": 3,
            "inference_steps": 10,
        },
    }, timeout=300)

    poses = result.get("poses", [])
    print(f"\n  Poses generated : {result.get('num_poses', 0)}")
    print(f"  Best confidence : {result.get('best_confidence', '—'):.3f}  (>0 = near-native)")
    print(f"  Best est. ΔG    : {result.get('best_estimated_dG_kcal_mol', '—'):.2f} kcal/mol")
    for pose in poses:
        xyz = pose.get("pose_centroid_xyz", {})
        print(f"    Rank {pose.get('rank')}:  conf={pose.get('confidence',0):.3f}  "
              f"dG={pose.get('estimated_dG_kcal_mol',0):.2f}  "
              f"centroid=({xyz.get('x')},{xyz.get('y')},{xyz.get('z')})")
    return result


# ── Step 5: Pose Rescoring ────────────────────────────────────────────────────

def step5_rescore(diffdock_output: dict) -> dict:
    _sep("STEP 5 — Pose Rescoring (GNINA)")
    print(f"  Rescoring {diffdock_output.get('num_poses', '?')} poses ...")

    result = _post("gnina-hf", {
        "inputs": {
            "diffdock_output": diffdock_output,
            "top_n_poses": diffdock_output.get("num_poses", 3),
        },
        "parameters": {
            "score_only": True,
            "seed": 0,
            "cpu": 4,
        },
    }, timeout=300)

    print(f"\n  Best minimizedAffinity : {result.get('best_minimizedAffinity','—'):.2f} kcal/mol")
    print(f"  Best CNNscore          : {result.get('best_CNNscore','—'):.3f}  (>0.5 = active)")
    print(f"  Best CNNaffinity       : {result.get('best_CNNaffinity','—'):.1f}  (pKi/pKd)")

    for pose in result.get("scored_poses", []):
        flag = "✓" if pose.get("CNNscore", 0) > 0.5 else " "
        print(f"    {flag} Rank {pose.get('diffdock_rank')}:  "
              f"minAff={pose.get('minimizedAffinity',0):.2f}  "
              f"CNNscore={pose.get('CNNscore',0):.3f}  "
              f"CNNaff={pose.get('CNNaffinity',0):.1f}")
    return result


# ── Step 6: Retrosynthesis ────────────────────────────────────────────────────

def step6_retrosynthesis(smiles: str) -> dict:
    _sep("STEP 6 — Retrosynthesis")
    print(f"  Target SMILES : {smiles}")

    result = _post("retrosynthesis", {
        "inputs": {
            "target_smiles": smiles,
            "max_depth": 5,
            "min_confidence": 0.3,
        },
        "parameters": {},
    })

    routes = result.get("synthesis_routes", [])
    print(f"\n  Routes found  : {result.get('routes_found', 0)}")
    print(f"  Best feas.    : {result.get('best_route_feasibility', '—'):.3f}")

    for route in routes[:2]:          # print top 2 routes
        print(f"\n  Route {route.get('route_id')}:")
        print(f"    Feasibility : {route.get('feasibility_score','—'):.3f}  |  "
              f"SA={route.get('synthetic_accessibility','—')}  |  "
              f"Yield={route.get('overall_yield','—')}  |  "
              f"Steps={route.get('total_steps','—')}")
        sm = route.get("starting_materials", [])
        if sm:
            print(f"    Starting materials: {', '.join(sm)}")
        for step in route.get("steps", []):
            cond = step.get("conditions", {})
            print(f"    Step {step.get('step')}: {step.get('reaction_type')}  "
                  f"conf={step.get('confidence',0):.2f}  yield={step.get('yield_estimate','—')}  "
                  f"[{cond.get('solvent','?')} / {cond.get('temperature','?')}]")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def run_pipeline(
    masked_smiles: str = IBUPROFEN_MASKED,
    protein_sequence: str = CDK2_SEQUENCE,
    target_name: str = "CDK2",
) -> dict:
    print("\n" + "=" * 60)
    print("  DRUG DISCOVERY API — FULL PIPELINE")
    print("  Target:", target_name)
    print("=" * 60)

    pipeline_output = {}

    # Step 1: Generate candidates
    candidates = step1_generate(masked_smiles, top_k=5)
    pipeline_output["step1_generation"] = candidates

    if not candidates:
        print("\n  No candidates generated — pipeline stopped.")
        return pipeline_output

    # Step 2: ADMET triage
    survivors = step2_admet_triage(candidates)
    pipeline_output["step2_survivors"] = survivors

    if not survivors:
        print("\n  No molecules passed ADMET triage — using all candidates for DTI.")
        survivors = candidates[:3]   # fall back to top-3 by generation score

    # Step 3: DTI ranking
    ranked = step3_dti(survivors, protein_sequence, target_name)
    pipeline_output["step3_ranked"] = ranked
    top_mol = ranked[0]

    # Step 4: Docking
    dock_result = step4_docking(
        smiles=top_mol["completed_smiles"],
        protein_sequence=protein_sequence,
        complex_name=f"{target_name.lower()}_top_candidate",
    )
    pipeline_output["step4_docking"] = dock_result

    # Step 5: Pose rescoring
    rescore_result = step5_rescore(dock_result)
    pipeline_output["step5_rescoring"] = rescore_result

    # Step 6: Retrosynthesis
    retro_result = step6_retrosynthesis(top_mol["completed_smiles"])
    pipeline_output["step6_retrosynthesis"] = retro_result

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Top candidate   : {top_mol['completed_smiles']}")
    print(f"  Gen. score      : {top_mol.get('score', '—'):.4f}")
    print(f"  Lipinski viol.  : {top_mol.get('lipinski_violations', '—')}")
    print(f"  Binding aff.    : {top_mol.get('binding_affinity', '—'):.3f} ({top_mol.get('dti_strength','—')})")
    print(f"  Best dock conf. : {dock_result.get('best_confidence', '—'):.3f}")
    print(f"  Best CNN score  : {rescore_result.get('best_CNNscore', '—'):.3f}")
    print(f"  Synth. routes   : {retro_result.get('routes_found', 0)}")
    print(f"  Best SA score   : {retro_result.get('synthesis_routes', [{}])[0].get('synthetic_accessibility', '—')}")
    print("=" * 60)

    # Save top-candidate summary
    summary_line = (
        f"SMILES={top_mol['completed_smiles']}  "
        f"affinity={top_mol.get('binding_affinity', '?'):.3f}  "
        f"CNNscore={rescore_result.get('best_CNNscore', '?'):.3f}  "
        f"routes={retro_result.get('routes_found', 0)}"
    )
    with open("pipeline_top_candidate.txt", "w") as f:
        f.write(summary_line + "\n")
    print(f"\n  Top candidate summary → pipeline_top_candidate.txt")

    return pipeline_output


if __name__ == "__main__":
    output = run_pipeline(
        masked_smiles=IBUPROFEN_MASKED,
        protein_sequence=CDK2_SEQUENCE,
        target_name="CDK2",
    )

    with open("pipeline_output.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("  Full pipeline output → pipeline_output.json")

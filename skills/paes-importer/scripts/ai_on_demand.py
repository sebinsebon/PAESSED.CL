#!/usr/bin/env python3
"""Host-CLI handoff for unresolved Etapa 1 candidates.

This module deliberately has no adapter for a particular agent. The current
host CLI creates a request from a minimum evidence crop and applies a strict
response after deterministic revalidation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator


AI_RESPONSE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "candidate_id", "action", "agent", "result"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "candidate_id": {"type": "string", "minLength": 1},
        "action": {"enum": ["replace", "retain_unresolved"]},
        "agent": {
            "type": "object", "additionalProperties": False,
            "required": ["cli", "model"],
            "properties": {
                "cli": {"type": "string", "minLength": 1},
                "model": {"type": "string", "minLength": 1},
            },
        },
        "result": {
            "oneOf": [
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "latex", "display", "source_ids", "owner"],
                    "properties": {
                        "type": {"const": "math"},
                        "latex": {"type": "string", "minLength": 1},
                        "display": {"type": "boolean"},
                        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "owner": {"type": "string", "minLength": 1},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "asset_id", "source_ids", "owner"],
                    "properties": {
                        "type": {"const": "image"},
                        "asset_id": {"type": "string", "minLength": 1},
                        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "owner": {"type": "string", "minLength": 1},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "rows", "source_ids", "owner"],
                    "properties": {
                        "type": {"const": "table"},
                        "rows": {"type": "array"},
                        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "owner": {"type": "string", "minLength": 1},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "reason", "source_ids", "owner"],
                    "properties": {
                        "type": {"const": "unresolved"},
                        "reason": {"type": "string", "minLength": 1},
                        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "owner": {"type": "string", "minLength": 1},
                    },
                },
            ]
        },
    },
}


def validate_ai_response(response: dict, candidate: dict) -> dict:
    errors = sorted(Draft202012Validator(AI_RESPONSE_SCHEMA).iter_errors(response), key=lambda error: list(error.path))
    if errors:
        raise ValueError("Invalid AI response: " + "; ".join(error.message for error in errors))
    if response["candidate_id"] != candidate.get("candidate_id"):
        raise ValueError("AI response candidate_id does not match the target")
    result = response["result"]
    expected = list(candidate.get("source_ids", []))
    if result["owner"] != candidate.get("owner"):
        raise ValueError("AI response owner does not match the target")
    if sorted(result["source_ids"]) != sorted(expected):
        raise ValueError("AI response must consume exactly the candidate source_ids")
    if result["type"] == "math":
        if any(char == "$" and (index == 0 or result["latex"][index - 1] != "\\") for index, char in enumerate(result["latex"])):
            raise ValueError("Math LaTeX must not contain unescaped dollar delimiters")
    if response["action"] == "retain_unresolved" and result["type"] != "unresolved":
        raise ValueError("retain_unresolved requires an unresolved result")
    if response["action"] == "replace" and result["type"] == "unresolved":
        raise ValueError("replace requires a typed result")
    return response


def build_ai_request(candidate: dict, evidence: list[dict]) -> dict:
    evidence_id = candidate.get("ai_evidence_id") or candidate.get("evidence_id")
    selected = next((entry for entry in evidence if entry.get("id") == evidence_id), None)
    if not selected:
        raise ValueError("No minimum evidence crop is registered for candidate")
    kind = candidate.get("candidate_type", "visual")
    if kind == "math":
        instruction = (
            "Inspect only this crop. Transcribe exactly the complete mathematical "
            "expression into LaTeX. Preserve order, grouping, operators, fractions, "
            "exponents and display mode. Never solve, simplify or explain."
        )
    elif kind == "table":
        instruction = (
            "Inspect only this crop. Reconstruct the table faithfully, preserving "
            "rows, columns and cell content. Do not infer missing content."
        )
    else:
        instruction = (
            "Inspect only this crop. Associate or describe the visual faithfully "
            "for rendering. Do not solve, explain or classify the question."
        )
    return {
        "schema_version": "1.0",
        "candidate_id": candidate["candidate_id"],
        "candidate_type": kind,
        "owner": candidate.get("owner"),
        "source_ids": list(candidate.get("source_ids", [])),
        "evidence": {"id": evidence_id, "path": selected["path"]},
        "instruction": instruction,
        "response_contract": "skills/paes-importer/schema/ai-response.schema.json",
    }


def iter_blocks(blocks):
    for block in blocks:
        yield block
        if block.get("type") == "table":
            for row in block.get("rows", []):
                for cell in row.get("cells", []):
                    yield from iter_blocks(cell.get("blocks", []))


def iter_candidates(draft: dict):
    for question in draft.get("questions", []):
        blocks = list(question.get("stem", []))
        blocks.extend(block for option in question.get("options", []) for block in option.get("blocks", []))
        for block in iter_blocks(blocks):
            if block.get("type") == "unresolved" and block.get("candidate_id"):
                yield question, block


def _replace_candidate(blocks, candidate_id, replacement):
    for index, block in enumerate(blocks):
        if block.get("candidate_id") == candidate_id:
            blocks[index] = replacement
            return True
        if block.get("type") == "table":
            for row in block.get("rows", []):
                for cell in row.get("cells", []):
                    if _replace_candidate(cell.get("blocks", []), candidate_id, replacement):
                        return True
    return False


def _question_blocks(question):
    blocks = list(question.get("stem", []))
    blocks.extend(block for option in question.get("options", []) for block in option.get("blocks", []))
    return blocks


def recalculate_draft(draft: dict, question) -> dict:
    """Re-run coverage and fidelity; AI output never supplies a status."""
    from import_benchmark import assess_source_coverage, determine_extraction_status
    from structural_fidelity import fidelity_report

    blocks = _question_blocks(question)
    region_ids = set(question.get("region_ids", []))
    inventory = [entry for entry in draft.get("source_objects", []) if entry.get("region_id") in region_ids]
    owners = {option["id"]: option for option in question.get("options", [])}
    coverage = assess_source_coverage(inventory, blocks, owners=owners)
    structural = fidelity_report(blocks)
    question["coverage"] = coverage
    question["structural_fidelity"] = structural
    question["extraction_status"] = determine_extraction_status(
        question["id"], draft.get("issues", []), question.get("stem", []), question.get("options", []), coverage
    )
    return draft


def apply_ai_response(draft: dict, response: dict) -> dict:
    target = next((pair for pair in iter_candidates(draft) if pair[1].get("candidate_id") == response.get("candidate_id")), None)
    if not target:
        raise ValueError("AI candidate_id was not found in draft")
    question, candidate = target
    validate_ai_response(response, candidate)
    result = copy.deepcopy(response["result"])
    if result["type"] == "image" and not any(
        asset.get("asset_id") == result["asset_id"] for asset in draft.get("assets", [])
    ):
        raise ValueError("AI response references an asset that is not in draft.assets")
    proof = copy.deepcopy(candidate.get("structural_fidelity", {}))
    proof.update({
        "status": "unresolved",
        "reasons": ["ai_response_requires_revalidation"],
        "source_ids": list(result["source_ids"]),
        "representation_type": result["type"],
        "method": "ai_on_demand_pending_deterministic_revalidation_v1",
    })
    result["candidate_id"] = candidate["candidate_id"]
    result["evidence_id"] = candidate.get("evidence_id")
    result["ai_evidence_id"] = candidate.get("ai_evidence_id")
    result["structural_fidelity"] = proof
    if response["action"] == "retain_unresolved":
        result = copy.deepcopy(candidate)
        result["ai_on_demand"] = {"status": "retained", "task": "manual_review_or_retry"}
    blocks = question.get("stem", [])
    blocks.extend(block for option in question.get("options", []) for block in option.get("blocks", []))
    if not _replace_candidate(blocks, candidate["candidate_id"], result):
        raise ValueError("Unable to replace candidate in its owner")
    issues = draft.setdefault("issues", [])
    issues[:] = [
        issue for issue in issues
        if not (issue.get("target_id") == question["id"] and issue.get("code") in {
            "PENDING_MATH_RECONSTRUCTION", "PENDING_VISUAL_RECONSTRUCTION", "STRUCTURAL_FIDELITY_UNPROVEN"
        })
    ]
    issues.append({
        "id": "issue-ai-" + candidate["candidate_id"],
        "code": "AI_RESPONSE_REVALIDATION_PENDING",
        "severity": "warning",
        "target_id": question["id"],
        "region_ids": list(question.get("region_ids", [])),
        "evidence_ids": [value for value in [candidate.get("ai_evidence_id"), candidate.get("evidence_id")] if value],
        "blocks_completion": True,
        "message": "AI output was applied but requires deterministic fidelity and human review.",
    })
    intervention_id = "ai-" + hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest()[:16]
    draft.setdefault("extraction", {}).setdefault("ai_interventions", []).append({
        "id": intervention_id,
        "cli": response["agent"]["cli"],
        "model": response["agent"]["model"],
        "target_id": candidate["candidate_id"],
        "question_id": question["id"],
        "candidate_type": candidate.get("candidate_type"),
        "evidence_ids": [value for value in [candidate.get("ai_evidence_id"), candidate.get("evidence_id")] if value],
        "source_ids": list(candidate.get("source_ids", [])),
        "action": response["action"],
        "result_type": result.get("type"),
        "validation": "schema_source_owner_revalidated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    recalculate_draft(draft, question)
    draft.setdefault("extraction", {})["status"] = "partial"
    return draft


def main():
    parser = argparse.ArgumentParser(description="Prepare or apply Etapa 1 AI-on-demand candidates")
    sub = parser.add_subparsers(dest="command", required=True)
    request = sub.add_parser("request")
    request.add_argument("--draft", type=Path, required=True)
    request.add_argument("--candidate", required=True)
    request.add_argument("--output", type=Path, required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("--draft", type=Path, required=True)
    apply.add_argument("--response", type=Path, required=True)
    apply.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    draft = json.loads(args.draft.read_text(encoding="utf-8"))
    if args.command == "request":
        candidate = next((block for _, block in iter_candidates(draft) if block.get("candidate_id") == args.candidate), None)
        if not candidate:
            raise SystemExit("Candidate not found")
        request = build_ai_request(candidate, draft.get("evidence", []))
        args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        response = json.loads(args.response.read_text(encoding="utf-8"))
        updated = apply_ai_response(draft, response)
        args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

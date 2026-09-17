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
    "$defs": {
        "table_rows": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["cells"],
                "properties": {
                    "cells": {
                        "type": "array",
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["blocks"],
                            "properties": {
                                "blocks": {
                                    "type": "array",
                                    "items": {"$ref": "#/$defs/block"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "block": {
            "oneOf": [
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "text"],
                    "properties": {"type": {"const": "text"}, "text": {"type": "string"}},
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "latex", "display"],
                    "properties": {
                        "type": {"const": "math"},
                        "latex": {"type": "string", "minLength": 1},
                        "display": {"type": "boolean"},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "asset_id"],
                    "properties": {
                        "type": {"const": "image"},
                        "asset_id": {"type": "string", "minLength": 1},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "reason"],
                    "properties": {
                        "type": {"const": "unresolved"},
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
                {
                    "type": "object", "additionalProperties": False,
                    "required": ["type", "rows"],
                    "properties": {
                        "type": {"const": "table"},
                        "rows": {"$ref": "#/$defs/table_rows"},
                    },
                },
            ],
        },
    },
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
                        "rows": {"$ref": "#/$defs/table_rows"},
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
    evidence_id = candidate.get("ai_evidence_id")
    selected = next((entry for entry in evidence if entry.get("id") == evidence_id), None)
    if not evidence_id or not selected:
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
    generated_codes = {
        "AMBIGUOUS_ASSOCIATION", "PENDING_MATH_RECONSTRUCTION",
        "PENDING_VISUAL_RECONSTRUCTION", "STRUCTURAL_COVERAGE_GAP",
        "OWNER_MISMATCH", "DUPLICATE_SOURCE_CONSUMPTION",
        "STRUCTURAL_FIDELITY_UNPROVEN",
    }
    issues = draft.setdefault("issues", [])
    issues[:] = [
        issue for issue in issues
        if not (issue.get("target_id") == question["id"] and issue.get("code") in generated_codes)
    ]

    def add_issue(code, suffix, message, **extra):
        issue = {
            "id": f"issue-{question['id']}-{suffix}",
            "code": code,
            "severity": "warning",
            "target_id": question["id"],
            "region_ids": list(question.get("region_ids", [])),
            "blocks_completion": True,
            "message": message,
        }
        issue.update(extra)
        issues.append(issue)

    unresolved = [block for block in iter_blocks(blocks) if block.get("type") == "unresolved"]
    if unresolved:
        if any(block.get("reason") == "ambiguous_association" for block in unresolved):
            code = "AMBIGUOUS_ASSOCIATION"
        elif any(block.get("candidate_type") == "math" for block in unresolved):
            code = "PENDING_MATH_RECONSTRUCTION"
        else:
            code = "PENDING_VISUAL_RECONSTRUCTION"
        add_issue(code, "coverage", "A detected content candidate remains unresolved.")
    if coverage.get("uncovered"):
        add_issue(
            "STRUCTURAL_COVERAGE_GAP", "coverage-gap",
            "Relevant source objects remain unresolved.", evidence_ids=[],
        )
    if coverage.get("misowned"):
        add_issue("OWNER_MISMATCH", "owner", "A source object is consumed by the wrong structural owner.")
    if coverage.get("duplicated"):
        add_issue("DUPLICATE_SOURCE_CONSUMPTION", "duplicate-source", "A source object was consumed more than once.")
    if not structural["complete"]:
        add_issue(
            "STRUCTURAL_FIDELITY_UNPROVEN", "fidelity",
            "Source coverage does not prove expression type, grouping or reading order.",
            failures=copy.deepcopy(structural["failures"]),
        )
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
        result["ai_on_demand"] = {
            "status": "retained", "task": "manual_review_or_retry",
            "reason": response["result"]["reason"],
        }
    containers = [question.get("stem", [])] + [
        option.get("blocks", []) for option in question.get("options", [])
    ]
    if not any(_replace_candidate(blocks, candidate["candidate_id"], result) for blocks in containers):
        raise ValueError("Unable to replace candidate in its owner")
    issues = draft.setdefault("issues", [])
    issue_id = "issue-ai-" + candidate["candidate_id"]
    issues[:] = [issue for issue in issues if issue.get("id") != issue_id]
    issues.append({
        "id": issue_id,
        "code": (
            "AI_RESPONSE_REVALIDATION_PENDING"
            if response["action"] == "replace"
            else "AI_RESPONSE_RETAINED_UNRESOLVED"
        ),
        "severity": "warning",
        "target_id": question["id"],
        "region_ids": list(question.get("region_ids", [])),
        "evidence_ids": [value for value in [candidate.get("ai_evidence_id"), candidate.get("evidence_id")] if value],
        "blocks_completion": True,
        "message": (
            "AI output was applied but requires deterministic fidelity and human review."
            if response["action"] == "replace"
            else "AI output was retained as unresolved and requires manual review or retry."
        ),
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
        "response": copy.deepcopy(response),
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
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        response = json.loads(args.response.read_text(encoding="utf-8"))
        updated = apply_ai_response(draft, response)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

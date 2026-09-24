"""Read legacy drafts and validate the independent Stage 1 draft v1 contract.

This module never extracts PDFs or writes draft files. Artifact verification is
optional so structural validation can run without private files in CI.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker
from structural_fidelity import fidelity_report


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "draft.v1.schema.json"
AI_SCHEMA_PATH = SCHEMA_PATH.with_name("ai-response.schema.json")


class DraftContractError(ValueError):
    """A v1 draft violates its schema or semantic invariants."""


def read_draft(path: Path) -> dict:
    """Read a draft without rewriting it; legacy 0.1.0 remains accessible."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DraftContractError("Draft must be a JSON object")
    version = data.get("schema_version")
    if version == "1.0.0":
        validate_v1(data)
    elif version != "0.1.0":
        raise DraftContractError(f"Unsupported draft version: {version!r}")
    return data


def _unique(entries: list[dict], key: str, label: str) -> dict[str, dict]:
    ids = [entry[key] for entry in entries]
    if len(ids) != len(set(ids)):
        raise DraftContractError(f"Duplicate {label} ID")
    return dict(zip(ids, entries))


def _references(values: list[str], known: dict, label: str) -> None:
    missing = sorted(set(values) - known.keys())
    if missing:
        raise DraftContractError(f"Unknown {label}: {missing}")


def _blocks(blocks: list[dict]):
    for block in blocks:
        yield block
        if block["type"] == "table":
            for row in block["rows"]:
                for cell in row["cells"]:
                    yield from _blocks(cell["blocks"])


def _check_bbox(box: list[float], width: float, height: float, label: str) -> None:
    x0, y0, x1, y1 = box
    tolerance = 0.5  # Rounding tolerance, never silently clip geometry.
    if x0 > x1 or y0 > y1 or x0 < -tolerance or y0 < -tolerance or x1 > width + tolerance or y1 > height + tolerance:
        raise DraftContractError(f"Invalid {label} bounding box")


def _artifact_path(root: Path, relative: str, folder: str,
                   check_symlinks: bool) -> Path:
    path = PurePosixPath(relative)
    if (path.is_absolute() or relative != path.as_posix() or not path.parts or path.parts[0] != folder
            or any(part in {".", ".."} or ":" in part or "\\" in part for part in path.parts)):
        raise DraftContractError(f"Unsafe {folder} path: {relative}")
    target = root.joinpath(*path.parts)
    if check_symlinks:
        cursor = root
        for part in path.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise DraftContractError(f"Linked artifact path: {relative}")
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def validate_v1(draft: dict, *, artifact_root: Path | None = None,
                check_files: bool = False) -> None:
    """Validate one v1 draft; file verification needs its output directory."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(draft), key=lambda error: str(list(error.path)))
    if errors:
        first = errors[0]
        raise DraftContractError(f"Schema at {list(first.path)}: {first.message}")
    if check_files and artifact_root is None:
        raise DraftContractError("artifact_root is required when check_files=True")

    sources = _unique(draft["sources"], "id", "source")
    pages = _unique(draft["pages"], "id", "page")
    regions = _unique(draft["regions"], "id", "region")
    assets = _unique(draft["assets"], "asset_id", "asset")
    evidence = _unique(draft["evidence"], "id", "evidence")
    objects = _unique(draft["source_objects"], "id", "source object")
    questions = _unique(draft["questions"], "id", "question")
    contexts = _unique(draft["contexts"], "id", "context") if draft["contexts"] else {}
    _unique(draft["issues"], "id", "issue")
    _unique(draft["extraction"]["ai_interventions"], "id", "AI intervention")

    page_pairs = set()
    for page in pages.values():
        _references([page["source_id"]], sources, "source")
        pair = (page["source_id"], page["page_number"])
        if pair in page_pairs or page["page_number"] > sources[page["source_id"]]["page_count"]:
            raise DraftContractError("Duplicate or out-of-range source page")
        page_pairs.add(pair)
    for region in regions.values():
        _references([region["page_id"]], pages, "page")
        page = pages[region["page_id"]]
        _check_bbox(region["bbox"], page["width"], page["height"], "region")
    for entry in objects.values():
        _references([entry["region_id"]], regions, "region")
        if entry.get("parent_id"):
            _references([entry["parent_id"]], objects, "parent source object")

    for group, folder in ((draft["assets"], "assets"), (draft["evidence"], "evidence")):
        paths = [entry["path"] for entry in group]
        if len(paths) != len(set(paths)):
            raise DraftContractError(f"Duplicate {folder} path")
        for entry in group:
            _references(entry["region_ids"], regions, "region")
            _references(entry.get("source_ids", []), objects, "source object")
            target = _artifact_path(artifact_root or Path("."), entry["path"], folder,
                                    check_symlinks=check_files)
            if check_files:
                if not target.is_file() or _sha256(target) != entry["sha256"].lower():
                    raise DraftContractError(f"Missing or changed artifact: {entry['path']}")
    for item in evidence.values():
        if item.get("parent_evidence_id"):
            _references([item["parent_evidence_id"]], evidence, "parent evidence")

    for group in (draft["contexts"], draft["unassigned_fragments"]):
        for entry in group:
            _references(entry["region_ids"], regions, "region")
            for block in _blocks(entry["blocks"]):
                _references(block["source_ids"], objects, "source object")
                _references([block["asset_id"]] if block["type"] == "image" else [], assets, "asset")
                _references([block["evidence_id"]] if block.get("evidence_id") else [], evidence, "evidence")

    for question in questions.values():
        _references(question["region_ids"], regions, "region")
        _references(question["context_ids"], contexts, "context")
        if not question["region_ids"]:
            raise DraftContractError(f"Question {question['id']} has no region")
        question_sources = {
            pages[regions[region_id]["page_id"]]["source_id"]
            for region_id in question["region_ids"]
        }
        if len(question_sources) != 1:
            raise DraftContractError(f"Question spans multiple PDFs: {question['id']}")
        for context_id in question["context_ids"]:
            context_sources = {
                pages[regions[region_id]["page_id"]]["source_id"]
                for region_id in contexts[context_id]["region_ids"]
            }
            if context_sources != question_sources:
                raise DraftContractError(f"Context belongs to another PDF: {context_id}")
        option_ids = [option["id"] for option in question["options"]]
        if len(option_ids) != len(set(option_ids)):
            raise DraftContractError(f"Duplicate option ID in {question['id']}")
        if any(option["owner"] != f"option:{option['id']}" for option in question["options"]):
            raise DraftContractError(f"Option owner differs from ID in {question['id']}")
        region_set = set(question["region_ids"])
        relevant_objects = {key: item for key, item in objects.items() if item["region_id"] in region_set}
        counts = Counter()
        owners = {}
        for owner, blocks, marker_ids in [
            ("stem", question["stem"], []),
            *((f"option:{option['id']}", option["blocks"], option["source_ids"])
              for option in question["options"]),
        ]:
            _references(marker_ids, objects, "source object")
            for source_id in marker_ids:
                counts[source_id] += 1
                owners.setdefault(source_id, set()).add(owner)
            for block in _blocks(blocks):
                if block.get("owner", owner) != owner:
                    raise DraftContractError(f"Block owner differs from container in {question['id']}")
                _references(block["source_ids"], objects, "source object")
                _references([block["asset_id"]] if block["type"] == "image" else [], assets, "asset")
                _references([block["evidence_id"]] if block.get("evidence_id") else [], evidence, "evidence")
                _references([block["ai_evidence_id"]] if block.get("ai_evidence_id") else [], evidence, "evidence")
                if block["type"] == "math" and any(
                        char == "$" and (index == 0 or block["latex"][index - 1] != "\\")
                        for index, char in enumerate(block["latex"])):
                    raise DraftContractError("Math LaTeX contains an unescaped dollar delimiter")
                if block.get("structural_fidelity"):
                    _references(block["structural_fidelity"]["source_ids"], objects, "source object")
                    if set(block["structural_fidelity"]["source_ids"]) != set(block["source_ids"]):
                        raise DraftContractError("Block proof source IDs differ from the block")
                for source_id in block["source_ids"]:
                    counts[source_id] += 1
                    owners.setdefault(source_id, set()).add(owner)
        if question["extraction_status"] == "complete":
            for context_id in question["context_ids"]:
                context = contexts[context_id]
                context_blocks = list(_blocks(context["blocks"]))
                context_objects = {
                    key: item for key, item in objects.items()
                    if item["region_id"] in context["region_ids"]
                }
                context_counts = Counter(
                    source_id for block in context_blocks for source_id in block["source_ids"]
                )
                if (not context_blocks or
                        any(block["type"] == "unresolved" for block in context_blocks) or
                        not fidelity_report(context["blocks"])["complete"] or
                        set(context_counts) != set(context_objects) or
                        any(count != 1 for count in context_counts.values()) or
                        any(item["owner"] != f"context:{context_id}"
                            for item in context_objects.values())):
                    raise DraftContractError(f"Unproven shared context: {context_id}")
            all_blocks = list(_blocks(question["stem"])) + [
                block for option in question["options"] for block in _blocks(option["blocks"])
            ]
            if (not all_blocks or not relevant_objects or
                    any(block["type"] == "unresolved" for block in all_blocks) or
                    any(not block["source_ids"] for block in all_blocks) or
                    any(block.get("structural_fidelity", {}).get("status") == "unresolved"
                        for block in all_blocks) or
                    any(block.get("structural_fidelity", {}).get("reasons")
                        for block in all_blocks) or
                    not question["structural_fidelity"]["complete"] or
                    question["structural_fidelity"]["failures"] or
                    any(issue["target_id"] == question["id"] and issue["blocks_completion"]
                        for issue in draft["issues"])):
                raise DraftContractError(f"Unproven complete status: {question['id']}")
            flat_blocks = question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ]
            if not fidelity_report(flat_blocks)["complete"]:
                raise DraftContractError(f"Structural fidelity failed: {question['id']}")
            if set(counts) != set(relevant_objects) or any(count != 1 for count in counts.values()):
                raise DraftContractError(f"Incomplete or duplicate source coverage: {question['id']}")
            if any(owners.get(key) != {item["owner"]} for key, item in relevant_objects.items()):
                raise DraftContractError(f"Wrong structural owner: {question['id']}")
        elif question["extraction_status"] == "failed" and (
                question["stem"] or any(option["blocks"] for option in question["options"])):
            raise DraftContractError(f"Failed question contains usable blocks: {question['id']}")

    for issue in draft["issues"]:
        _references([issue["target_id"]], questions, "issue target")
        _references(issue["region_ids"], regions, "region")
        _references(issue.get("evidence_ids", []), evidence, "evidence")
        _references(issue.get("source_ids", []), objects, "source object")
    ai_schema = json.loads(AI_SCHEMA_PATH.read_text(encoding="utf-8"))
    ai_validator = Draft202012Validator(ai_schema)
    for event in draft["extraction"]["ai_interventions"]:
        _references([event["question_id"]], questions, "AI question")
        _references(event["evidence_ids"], evidence, "evidence")
        _references(event["source_ids"], objects, "source object")
        errors = list(ai_validator.iter_errors(event["response"]))
        if errors:
            raise DraftContractError(f"Invalid embedded AI response: {event['id']}")
        response = event["response"]
        if (response["candidate_id"] != event["target_id"] or
                response["action"] != event["action"] or
                response["agent"]["cli"] != event["cli"] or
                response["agent"]["model"] != event["model"] or
                response["result"]["type"] != event["result_type"] or
                set(response["result"]["source_ids"]) != set(event["source_ids"])):
            raise DraftContractError(f"AI event and response disagree: {event['id']}")

    statuses = [question["extraction_status"] for question in questions.values()]
    expected = "failed" if not statuses or all(status == "failed" for status in statuses) else (
        "complete" if all(status == "complete" for status in statuses) else "partial")
    if draft["extraction"]["status"] != expected:
        raise DraftContractError(f"Extraction status should be {expected}")
    if (any(question["needs_manual_audit"] for question in questions.values()) and
            not draft["extraction"]["needs_manual_audit"]):
        raise DraftContractError("Global needs_manual_audit must include question audits")

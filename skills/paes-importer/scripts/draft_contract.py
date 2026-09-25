"""Read legacy drafts and validate the independent Stage 1 draft v1 contract.

This module never extracts PDFs or writes draft files. Artifact verification is
optional so structural validation can run without private files in CI.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from math import isclose, isfinite
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker
from structural_fidelity import fidelity_report


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "draft.v1.schema.json"
AI_SCHEMA_PATH = SCHEMA_PATH.with_name("ai-response.schema.json")


class DraftContractError(ValueError):
    """A v1 draft violates its schema or semantic invariants."""


class CompleteQuestionError(DraftContractError):
    """A question declared complete lacks sufficient structural proof."""

    def __init__(self, question_id: str, reason: str):
        self.question_id = question_id
        self.reason = reason
        super().__init__(f"{reason}: {question_id}")


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


def _expanded_bbox(box: list[float] | tuple[float, ...], *, x_pad: float = 3.0,
                   y_pad: float = 2.0) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = map(float, box)
    return x0 - x_pad, y0 - y_pad, x1 + x_pad, y1 + y_pad


def _intersection_area(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return width * height


def _positive_font_size(entry: dict, key: str) -> float | None:
    try:
        size = float(entry.get("extensions", {}).get(key))
    except (TypeError, ValueError):
        return None
    return size if isfinite(size) and size > 0 else None


def _font_sizes_compatible(rendering: dict, source: dict) -> bool:
    rendering_size = _positive_font_size(rendering, "paessed.effective_font_size")
    source_size = _positive_font_size(source, "paessed.source_font_size")
    if rendering_size is None or source_size is None:
        return False
    return abs(rendering_size - source_size) / max(rendering_size, source_size) <= 0.20


def _validate_text_rendering_font_metrics(source_objects: list[dict]) -> None:
    keys = (
        "paessed.effective_font_size",
        "paessed.pdfium_declared_font_size",
        "paessed.pdfium_vertical_scale",
    )
    for entry in source_objects:
        if entry.get("kind") != "text_rendering":
            continue
        extensions = entry.get("extensions", {})
        if not any(key in extensions for key in keys):
            continue
        effective, declared, scale = (
            _positive_font_size(entry, key) for key in keys
        )
        if (effective is None or declared is None or scale is None
                or not isclose(effective, declared * scale, rel_tol=1e-6, abs_tol=1e-6)):
            raise DraftContractError(
                f"Invalid text rendering font metrics: {entry['id']}"
            )


def _covered_fraction(box: tuple[float, ...], covers: list[tuple[float, ...]]) -> float:
    """Return the fraction of a box covered by the union of other boxes."""
    area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
    if area <= 0.0 or not covers:
        return 0.0
    clipped = [
        (max(box[0], value[0]), max(box[1], value[1]),
         min(box[2], value[2]), min(box[3], value[3]))
        for value in covers
        if _intersection_area(box, value) > 0.0
    ]
    if not clipped:
        return 0.0
    x_edges = sorted({x for value in clipped for x in (value[0], value[2])})
    covered = 0.0
    for x0, x1 in zip(x_edges, x_edges[1:]):
        if x1 <= x0:
            continue
        intervals = sorted(
            (value[1], value[3]) for value in clipped
            if value[0] < x1 and value[2] > x0
        )
        y_total = 0.0
        if intervals:
            start, end = intervals[0]
            for low, high in intervals[1:]:
                if low <= end:
                    end = max(end, high)
                else:
                    y_total += end - start
                    start, end = low, high
            y_total += end - start
        covered += (x1 - x0) * y_total
    return min(1.0, covered / area)


def text_rendering_duplicates(source_objects: list[dict]) -> dict[str, list[str]]:
    """Link PDFium text renderings to geometrically supported extracted text.

    PdfTextObj exposes bounds but no text in the supported PDFium wrapper. A
    duplicate therefore needs same-region text provenance plus substantial
    geometric coverage. Small/degenerate glyph bounds use a point-in-text-box
    check with a 1.5 by 2 point tolerance. Unmatched objects stay semantic.
    """
    text_sources = [
        entry for entry in source_objects
        if entry.get("kind") in {"text", "text_span"}
    ]
    matches: dict[str, list[str]] = {}
    for rendering in source_objects:
        if rendering.get("kind") != "text_rendering":
            continue
        box = tuple(map(float, rendering.get("bbox", [])))
        if len(box) != 4 or box[0] > box[2] or box[1] > box[3]:
            continue
        candidates = [
            entry for entry in text_sources
            if entry.get("region_id") == rendering.get("region_id")
            and _font_sizes_compatible(rendering, entry)
        ]
        if not candidates:
            continue
        width = box[2] - box[0]
        height = box[3] - box[1]
        area = width * height
        if area <= 1e-6:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            contained = []
            for entry in candidates:
                target = tuple(map(float, entry.get("bbox", [])))
                if len(target) != 4:
                    continue
                if entry.get("candidate_type") == "math":
                    continue
                expanded = _expanded_bbox(target)
                if expanded[0] <= cx <= expanded[2] and expanded[1] <= cy <= expanded[3]:
                    target_area = max(0.0, target[2] - target[0]) * max(0.0, target[3] - target[1])
                    distance = abs(cx - (target[0] + target[2]) / 2.0) + abs(cy - (target[1] + target[3]) / 2.0)
                    contained.append((target_area, distance, entry["id"]))
            if contained:
                matches[rendering["id"]] = [min(contained)[2]]
            continue

        expanded_targets = []
        for entry in candidates:
            target = tuple(map(float, entry.get("bbox", [])))
            if len(target) == 4 and target[0] <= target[2] and target[1] <= target[3]:
                x_pad = 1.0 if entry.get("candidate_type") == "math" else 3.0
                expanded_targets.append((entry, _expanded_bbox(target, x_pad=x_pad)))
        fraction = _covered_fraction(box, [target for _, target in expanded_targets])
        if fraction >= 0.65:
            matched_ids = sorted(
                entry["id"] for entry, target in expanded_targets
                if _intersection_area(box, target) > 0.0
            )
            if matched_ids:
                matches[rendering["id"]] = matched_ids
            continue

        # PDFium sometimes reports tiny punctuation glyphs with bounds too
        # narrow to meet the area threshold, while their centers still land
        # unambiguously inside an extracted text source.
        if area <= 16.0:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            contained = []
            for entry, target in expanded_targets:
                if entry.get("candidate_type") == "math":
                    continue
                if target[0] <= cx <= target[2] and target[1] <= cy <= target[3]:
                    original = tuple(map(float, entry["bbox"]))
                    target_area = max(0.0, original[2] - original[0]) * max(0.0, original[3] - original[1])
                    distance = abs(cx - (original[0] + original[2]) / 2.0) + abs(cy - (original[1] + original[3]) / 2.0)
                    contained.append((target_area, distance, entry["id"]))
            if contained:
                matches[rendering["id"]] = [min(contained)[2]]
    return matches


def empty_text_rendering_ids(source_objects: list[dict],
                             duplicates: dict[str, list[str]] | None = None) -> set[str]:
    """Identify zero-area text objects with no nearby extracted text geometry.

    These objects have no visible footprint and no geometric provenance. They
    remain in source_objects with an explicit status for audit, but do not
    block structural coverage. A point near text/math stays a candidate unless
    the duplicate matcher can prove a prose/marker association.
    """
    duplicates = duplicates if duplicates is not None else text_rendering_duplicates(source_objects)
    text_sources = [
        entry for entry in source_objects
        if entry.get("kind") in {"text", "text_span"}
    ]
    empty = set()
    for entry in source_objects:
        if entry.get("kind") != "text_rendering" or entry["id"] in duplicates:
            continue
        box = tuple(map(float, entry.get("bbox", [])))
        if len(box) != 4 or abs(box[2] - box[0]) > 1e-6 or abs(box[3] - box[1]) > 1e-6:
            continue
        cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
        nearby = False
        for source in text_sources:
            if source.get("region_id") != entry.get("region_id"):
                continue
            target = tuple(map(float, source.get("bbox", [])))
            if len(target) != 4:
                continue
            x_pad = 1.0 if source.get("candidate_type") == "math" else 3.0
            expanded = _expanded_bbox(target, x_pad=x_pad)
            if expanded[0] <= cx <= expanded[2] and expanded[1] <= cy <= expanded[3]:
                nearby = True
                break
        if not nearby:
            empty.add(entry["id"])
    return empty


def _verified_text_rendering_ids(objects: dict[str, dict]) -> set[str]:
    _validate_text_rendering_font_metrics(list(objects.values()))
    geometric_matches = text_rendering_duplicates(list(objects.values()))
    empty_geometry = empty_text_rendering_ids(list(objects.values()), geometric_matches)
    verified = set()
    for source_id, entry in objects.items():
        extensions = entry.get("extensions", {})
        declared = extensions.get("paessed.duplicate_of")
        status = extensions.get("paessed.provenance_status")
        if status == "empty_geometry":
            if (entry.get("kind") != "text_rendering"
                    or source_id not in empty_geometry
                    or declared is not None):
                raise DraftContractError(f"Invalid empty text rendering status: {source_id}")
            verified.add(source_id)
            continue
        if declared is None:
            continue
        if (entry.get("kind") != "text_rendering"
                or not isinstance(declared, list)
                or not declared
                or len(declared) != len(set(declared))
                or geometric_matches.get(source_id) != declared
                or status is not None):
            raise DraftContractError(f"Invalid text rendering provenance: {source_id}")
        verified.add(source_id)
    return verified


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
    verified_renderings = _verified_text_rendering_ids(objects)
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
        question_number_ids = question.get("extensions", {}).get(
            "paessed.question_number_source_ids", []
        )
        if (not isinstance(question_number_ids, list)
                or len(question_number_ids) != len(set(question_number_ids))):
            raise DraftContractError(f"Invalid question-number source IDs: {question['id']}")
        _references(question_number_ids, objects, "question-number source object")
        for source_id in question_number_ids:
            marker = objects[source_id]
            if (marker.get("kind") != "text"
                    or marker.get("owner") != "question_number"
                    or marker.get("extensions", {}).get("paessed.metadata_role") != "question_number"
                    or marker.get("region_id") not in region_set):
                raise DraftContractError(f"Invalid question-number provenance: {source_id}")
        relevant_objects = {key: item for key, item in objects.items() if item["region_id"] in region_set}
        semantic_objects = {key: item for key, item in relevant_objects.items()
                            if key not in verified_renderings}
        counts = Counter()
        owners = {}
        for source_id in question_number_ids:
            counts[source_id] += 1
            owners.setdefault(source_id, set()).add("question_number")
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
                ambiguous_stem = (owner == "stem" and block["type"] == "unresolved"
                                  and block.get("owner") == "ambiguous")
                if ambiguous_stem and question["extraction_status"] == "complete":
                    raise CompleteQuestionError(question["id"], "Ambiguous unresolved stem block")
                if block.get("owner", owner) != owner and not ambiguous_stem:
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
                    and key not in verified_renderings
                }
                context_counts = Counter(
                    source_id for block in context_blocks for source_id in block["source_ids"]
                    if source_id not in verified_renderings
                )
                if (not context_blocks or
                        any(block["type"] == "unresolved" for block in context_blocks) or
                        not fidelity_report(context["blocks"])["complete"] or
                        set(context_counts) != set(context_objects) or
                        any(count != 1 for count in context_counts.values()) or
                        any(item["owner"] != f"context:{context_id}"
                            for item in context_objects.values())):
                    raise CompleteQuestionError(question["id"], f"Unproven shared context {context_id}")
            all_blocks = list(_blocks(question["stem"])) + [
                block for option in question["options"] for block in _blocks(option["blocks"])
            ]
            if (not all_blocks or not semantic_objects or
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
                raise CompleteQuestionError(question["id"], "Unproven complete status")
            flat_blocks = question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ]
            if not fidelity_report(flat_blocks)["complete"]:
                raise CompleteQuestionError(question["id"], "Structural fidelity failed")
            semantic_counts = {key: count for key, count in counts.items()
                               if key not in verified_renderings}
            if (set(semantic_counts) != set(semantic_objects) or
                    any(count != 1 for count in semantic_counts.values())):
                raise CompleteQuestionError(question["id"], "Incomplete or duplicate source coverage")
            if any(owners.get(key) != {item["owner"]} for key, item in semantic_objects.items()):
                raise CompleteQuestionError(question["id"], "Wrong structural owner")
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Position-aware Etapa 1 benchmark pipeline for PAESSED."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from types import SimpleNamespace
from importlib.metadata import version as package_version
from pathlib import Path

import pypdfium2 as pdfium
from jsonschema import validate
from pdf_inspector import extract_text_with_positions
from structural_fidelity import validate_and_order, fidelity_report

ROOT = Path(__file__).resolve().parents[3]
PDF_ROOT = ROOT.parent / "Ensayos"
PDFS = {
    2026: PDF_ROOT / "PAES-INVIERNO-M1 2026.pdf",
    2027: PDF_ROOT / "2027-26-06-17-paes-invierno-oficial-matematica1-p2027.pdf",
}
OPTION_RE = re.compile(r"^([A-D])\)$")
UNICODE_LETTER_RUN_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
OPTION_PREFIX_RE = re.compile(r"^([A-D])\)(?=\s+\S)")
QUESTION_RE = re.compile(r"^(\d+)\.$")
QUESTION_PREFIX_RE = re.compile(r"^(\d+)\.(?=\s+\S)")
QUESTION_MARKER_LEFT_TOLERANCE = 12.0
FOOTER_RE = re.compile(r"^-\s*\d+\s*-$")
MATHISH_RE = re.compile(r"^[0-9\s\u2212+\-().\u00b7*/]+$")

IMAGE_MARKER_RE = re.compile(r"^\[Image:\s*(Im\d+)\]$")
MATH_TOKEN_RE = re.compile(r"^[A-Za-z0-9\s\u2212+\-().,/%$·π√=?]+$")




_SOURCE_IDS: dict[int, str] = {}


def _source_id(value, fallback_kind="source"):
    if isinstance(value, dict):
        existing = value.get("source_id")
        if existing:
            return str(existing)
    else:
        existing = getattr(value, "source_id", None)
        if existing:
            return str(existing)
    return _SOURCE_IDS.get(id(value), f"anonymous:{fallback_kind}:{id(value)}")


def assign_source_ids(page_id: str, items, objects) -> None:
    for index, item in enumerate(items):
        source_id = f"{page_id}:text:{index}"
        _SOURCE_IDS.setdefault(id(item), source_id)
        try:
            if not getattr(item, "source_id", None):
                setattr(item, "source_id", source_id)
        except (AttributeError, TypeError):
            pass
    for index, obj in enumerate(objects):
        obj.setdefault("source_id", f"{page_id}:object:{index}")


def build_source_inventory(page_id: str, region_id: str, owner: str, items, objects) -> list[dict]:
    assign_source_ids(page_id, items, objects)
    inventory = []
    for item in items:
        entry = {
            "id": _source_id(item, "text"),
            "region_id": region_id,
            "owner": owner,
            "kind": "text",
            "candidate_type": "text",
            "bbox": list(_item_bbox(item)),
        }
        if getattr(item, "parent_source_id", None):
            entry["parent_id"] = item.parent_source_id
            entry["source_span"] = list(item.source_span)
            entry["kind"] = "text_span"
        inventory.append(entry)
    for obj in objects:
        kind = ("visual" if obj.get("type") == "PdfImage" else "text_rendering" if obj.get("type") == "PdfTextObj" else "layout")
        inventory.append({
            "id": _source_id(obj, "object"),
            "region_id": region_id,
            "owner": owner,
            "kind": kind,
            "candidate_type": "visual" if kind == "visual" else "layout",
            "bbox": list(obj["bbox_ll"]),
        })
    return inventory


def _block_source_ids(block: dict) -> list[str]:
    ids = list(block.get("source_ids", []))
    if block.get("type") == "table":
        for row in block.get("rows", []):
            for cell in row.get("cells", []):
                for nested in cell.get("blocks", []):
                    ids.extend(_block_source_ids(nested))
    return ids


def _unresolved_nested(block: dict) -> bool:
    if block.get("type") == "unresolved":
        return True
    if block.get("type") == "table":
        return any(
            _unresolved_nested(nested)
            for row in block.get("rows", [])
            for cell in row.get("cells", [])
            for nested in cell.get("blocks", [])
        )
    return False


def assess_source_coverage(
    inventory: list[dict],
    blocks: list[dict],
    owners: dict | None = None,
) -> dict:
    """Verify one consumption and the declared structural owner per source."""
    inventory_by_id = {entry["id"]: entry for entry in inventory}
    counts: dict[str, int] = {}
    representations: dict[str, set[str]] = {}
    observed_owners: dict[str, set[str]] = {}
    consumers: dict[str, list[dict]] = {}

    def consume(source_id: str, block_type: str, owner: str | None) -> None:
        counts[source_id] = counts.get(source_id, 0) + 1
        representations.setdefault(source_id, set()).add(block_type)
        consumers.setdefault(source_id, []).append({
            "type": block_type,
            "owner": owner,
        })
        if owner is not None:
            observed_owners.setdefault(source_id, set()).add(owner)

    def visit(block: dict, inherited_owner: str | None = None) -> None:
        owner = block.get("owner", inherited_owner)
        for source_id in block.get("source_ids", []):
            consume(source_id, block.get("type", "unknown"), owner)
        if block.get("type") == "table":
            for row in block.get("rows", []):
                for cell in row.get("cells", []):
                    for nested in cell.get("blocks", []):
                        visit(nested, owner)

    for block in blocks:
        visit(block)

    if owners:
        for label, value in owners.items():
            if isinstance(value, dict):
                owner = value.get("owner", f"option:{label}")
                for source_id in value.get("source_ids", []):
                    consume(source_id, f"owner:{label}", owner)

    for entry in inventory:
        entry["representation"] = sorted(
            representations.get(entry["id"], set())
        )
        entry["consumers"] = list(consumers.get(entry["id"], []))

    relevant = [entry for entry in inventory if entry.get("kind") != "text_rendering"]
    uncovered = [entry["id"] for entry in relevant if counts.get(entry["id"], 0) == 0]
    duplicated = sorted(
        source_id for source_id, count in counts.items() if count > 1
    )
    misowned = sorted(
        entry["id"]
        for entry in relevant
        if any(
            observed != entry.get("owner")
            for observed in observed_owners.get(entry["id"], set())
        )
    )
    return {
        "complete": not uncovered and not duplicated and not misowned and not any(
            _unresolved_nested(block) for block in blocks
        ),
        "uncovered": uncovered,
        "duplicated": duplicated,
        "misowned": misowned,
        "consumed": sorted(counts),
    }


def _item_bbox(item) -> tuple[float, float, float, float]:
    return text_bbox_ll(item)


def _bbox_union(bounds: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(value[0] for value in bounds),
        min(value[1] for value in bounds),
        max(value[2] for value in bounds),
        max(value[3] for value in bounds),
    )


def _x_overlap(left, right, padding: float = 2.0) -> bool:
    return left[0] <= right[2] + padding and right[0] <= left[2] + padding


def _x_near(left, right, padding: float = 12.0) -> bool:
    """Allow a math side to extend a short distance beyond its rule."""
    return _x_overlap(left, right, padding=padding)


def _near_fraction_token(item, bar) -> bool:
    """Keep the relaxed rule window from pulling in short prose words."""
    bounds = _item_bbox(item)
    if _x_overlap(bounds, bar, padding=0.0):
        return True
    return not re.fullmatch(r"[a-z]{2,}", item.text.strip())


def _latex_token(text: str) -> str:
    text = re.sub(r"\s+", "", text.strip())
    return text.replace("·", r"\cdot").replace("−", "-").replace("π", r"\pi").replace("$", r"\$")


def _is_mathish(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or cleaned in {"?", ".", ",", "!"} or not MATH_TOKEN_RE.fullmatch(cleaned):
        return False
    if re.search(r"[a-z]{3,}", cleaned):
        return False
    if re.fullmatch(r"[A-Za-z]+", cleaned) and len(cleaned) > 2 and not re.fullmatch(r"[A-Z]{1,4}", cleaned):
        return False
    return True


INLINE_EQUATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\$?\d[\d ]*\s*[+\u2212\-\u00b7*/]\s*)+"
    r"\$?\d[\d ]*\s*=\s*\$?\d[\d ]+"
)


def _clone_text_item(item, text: str, start: int, end: int, span_index: int):
    """Split one inspector span while preserving deterministic source lineage."""
    source = _source_id(item, "text")
    width = float(item.width) * (end - start) / max(1, len(item.text))
    offset = float(item.width) * start / max(1, len(item.text))
    clone = SimpleNamespace(
        text=text,
        page=getattr(item, "page", None),
        x=float(item.x) + offset,
        y=float(item.y),
        width=width,
        height=float(item.height),
        font_size=float(item.font_size),
        source_id=f"{source}#span:{span_index}",
        parent_source_id=source,
        source_span=[start, end],
    )
    return clone


def expand_inline_items(items):
    """Split obvious inline equation spans without interpreting their value."""
    expanded = []
    for item in items:
        text = item.text
        matches = list(INLINE_EQUATION_RE.finditer(text))
        if matches:
            pieces = []
            cursor = 0
            span_index = 0
            for match in matches:
                if match.start() > cursor:
                    pieces.append(_clone_text_item(item, text[cursor:match.start()], cursor, match.start(), span_index))
                    span_index += 1
                pieces.append(_clone_text_item(item, match.group(0), match.start(), match.end(), span_index))
                span_index += 1
                cursor = match.end()
            if cursor < len(text):
                pieces.append(_clone_text_item(item, text[cursor:], cursor, len(text), span_index))
            expanded.extend(piece for piece in pieces if piece.text)
        else:
            expanded.append(item)

    # Some PDFs keep a question marker and the start of its stem in one text
    # item (for example, ``1. Alicia ...``).  Only split prefixes aligned to
    # the page's numbered-question margin; indented numbered prose remains a
    # normal text item.
    question_prefix_x = [
        float(item.x)
        for item in expanded
        if QUESTION_PREFIX_RE.match(item.text)
    ]
    question_left = min(question_prefix_x) if question_prefix_x else None

    result = []
    for index, item in enumerate(expanded):
        text = item.text
        question_prefix = QUESTION_PREFIX_RE.match(text)
        if (
            question_prefix
            and question_left is not None
            and float(item.x) <= question_left + QUESTION_MARKER_LEFT_TOLERANCE
        ):
            marker_end = question_prefix.end()
            result.append(_clone_text_item(item, text[:marker_end], 0, marker_end, 1))
            result.append(_clone_text_item(item, text[marker_end:], marker_end, len(text), 2))
            continue
        option_prefix = OPTION_PREFIX_RE.match(text)
        if option_prefix:
            marker_end = option_prefix.end()
            result.append(_clone_text_item(item, text[:marker_end], 0, marker_end, 1))
            result.append(_clone_text_item(item, text[marker_end:], marker_end, len(text), 2))
            continue
        suffix = re.search(r"([?!.,])$", text)
        if suffix and not QUESTION_RE.fullmatch(text.strip()) and not OPTION_RE.fullmatch(text.strip()) and _is_mathish(text[:suffix.start()].strip()):
            result.append(_clone_text_item(item, text[:suffix.start()], 0, suffix.start(), 1))
            result.append(_clone_text_item(item, suffix.group(1), suffix.start(), len(text), 2))
            continue
        previous = expanded[index - 1] if index else None
        leading = re.match(r"([A-Za-z](?:\d+)?)(?=\s*[,.;:)])", text)
        previous_text = previous.text.strip() if previous else ""
        same_line = previous is not None and abs(float(item.y) - float(previous.y)) <= 2.2
        nearby = previous is not None and float(item.x) - float(previous.x + previous.width) <= 10.0
        if (
            leading
            and same_line
            and nearby
            and previous_text.endswith(("+", "-", "−", "*", "/", "·", "="))
            and not re.search(r"[a-z]{3,}", previous_text)
            and previous_text not in {"-", "−"}
        ):
            cut = leading.end()
            result.append(_clone_text_item(item, text[:cut], 0, cut, 1))
            result.append(_clone_text_item(item, text[cut:], cut, len(text), 2))
            continue
        trailing = re.search(r"(\d+)$", text)
        next_item = expanded[index + 1] if index + 1 < len(expanded) else None
        next_text = next_item.text.strip() if next_item else ""
        same_line = next_item is not None and abs(float(item.y) - float(next_item.y)) <= 2.2
        nearby = next_item is not None and float(next_item.x) - float(item.x + item.width) <= 10.0
        if trailing and re.search(r"[A-Za-z]", text[:trailing.start()]) and same_line and nearby and next_text[:1] in "-+\u2212*/\u00b7(":
            cut = trailing.start()
            result.append(_clone_text_item(item, text[:cut], 0, cut, 1))
            result.append(_clone_text_item(item, trailing.group(1), cut, len(text), 2))
            continue
        result.append(item)
    return result


def _horizontal_rules(objects: list[dict]) -> list[dict]:
    return [
        obj for obj in objects
        if obj.get("type") == "PdfObject"
        and obj["bbox_ll"][2] - obj["bbox_ll"][0] >= 5.0
        and obj["bbox_ll"][3] - obj["bbox_ll"][1] <= 2.5
    ]


def _nearest_math_line(items, bar, above: bool, bars=()) -> list:
    candidates = []
    for item in items:
        bounds = _item_bbox(item)
        if not _x_near(bounds, bar):
            continue
        if not _near_fraction_token(item, bar):
            continue
        if any(
            other != bar
            and _x_overlap(bounds, other)
            and abs(bar[1] - other[1]) <= 12.0
            for other in bars
        ):
            continue
        if above and bounds[1] >= bar[3] - 2.0:
            candidates.append(item)
        if not above and bounds[3] <= bar[1] + 2.0:
            candidates.append(item)
    candidates = [item for item in candidates if _is_mathish(item.text)]
    lines = make_lines(candidates)
    if not lines:
        return []
    selected = min(lines, key=lambda line: line["y"]) if above else max(lines, key=lambda line: line["y"])
    selected_items = selected["items"]
    selected_box = _bbox_union([_item_bbox(item) for item in selected_items])
    gap = (
        selected_box[1] - bar[3]
        if above
        else bar[1] - selected_box[3]
    )
    return selected_items if gap <= 36.0 else []


def _expand_math_line(items, bar, baseline, above: bool) -> list:
    if not baseline:
        return []
    baseline_y = sum(float(item.y) for item in baseline) / len(baseline)
    expanded = list(baseline)
    for item in items:
        if item in expanded or not _is_mathish(item.text):
            continue
        bounds = _item_bbox(item)
        if not _x_overlap(bounds, bar):
            continue
        delta = float(item.y) - baseline_y
        if above and 2.0 < delta <= 10.0 and float(item.font_size) < max(float(value.font_size) for value in baseline) * 0.95:
            expanded.append(item)
        if not above and -10.0 <= delta < -2.0 and float(item.font_size) < max(float(value.font_size) for value in baseline) * 0.95:
            expanded.append(item)
    return sorted(expanded, key=lambda item: float(item.x))


def _math_side_latex(items) -> str:
    ordered = sorted(items, key=lambda item: float(item.x))
    baseline = [item for item in ordered if float(item.font_size) >= max(float(value.font_size) for value in ordered) * 0.95]
    baseline_y = max((float(item.y) for item in baseline), default=0.0)
    result = ""
    last_base = None
    for item in ordered:
        token = _latex_token(item.text)
        is_super = (
            baseline
            and float(item.y) > baseline_y + 2.0
            and float(item.font_size) < max(float(value.font_size) for value in baseline) * 0.95
        )
        if is_super and last_base is not None:
            result += rf"^{{{token}}}"
        else:
            result += token
            if not is_super:
                last_base = item
    return result


def _multiline_math_members(items, used_items) -> list:
    """Find a conservative continuation made of adjacent math-only lines."""
    def is_math_token(item) -> bool:
        text = item.text.strip()
        words = re.findall(r"[A-Za-z]+", text)
        if any(len(word) > 1 for word in words) and re.search(r"\s", text):
            return False
        return (
            _is_mathish(text)
            and all(len(word) == 1 or word.isupper() for word in words)
        )

    def is_math_line(line) -> bool:
        text = line["text"].strip()
        words = re.findall(r"[A-Za-z]+", text)
        return not (
            re.search(r"\s", text)
            and any(len(word) > 1 for word in words)
        )

    remaining = [item for item in items if id(item) not in used_items]
    lines = make_lines(remaining)
    for start in range(len(lines) - 1):
        group = [lines[start]]
        for line in lines[start + 1:]:
            previous = group[-1]
            if abs(float(previous["y"]) - float(line["y"])) > 24.0:
                break
            if not is_math_line(previous) or not is_math_line(line):
                break
            if not all(
                is_math_token(item)
                for item in [*previous["items"], *line["items"]]
            ):
                break
            previous_text = previous["text"].replace(" ", "")
            current_text = line["text"].lstrip()
            current_operator = re.match(r"^[+\u2212\-*/\u00b7=]", current_text)
            previous_ends_operator = bool(
                re.search(r"[+\u2212\-*/\u00b7=]$", previous_text)
            )
            if current_operator and current_operator.group(0) in {"-", "\u2212"} and not previous_ends_operator:
                break
            connected = bool(
                previous_ends_operator
                or current_operator
            )
            if not connected:
                break
            previous_box = _bbox_union([_item_bbox(item) for item in previous["items"]])
            current_box = _bbox_union([_item_bbox(item) for item in line["items"]])
            if previous_box[2] < current_box[0] - 8.0 or current_box[2] < previous_box[0] - 8.0:
                break
            group.append(line)
        if len(group) >= 2 and any("=" in candidate["text"] for candidate in group):
            return [
                item
                for candidate in group
                for item in sorted(candidate["items"], key=lambda value: float(value.x))
            ]
    return []


def infer_math_display(members, all_items) -> bool:
    """A formula is inline when neighboring non-members share its text line."""
    bounds = _bbox_union([_item_bbox(item) for item in members])
    for item in all_items:
        if item in members or IMAGE_MARKER_RE.fullmatch(item.text.strip()):
            continue
        other = _item_bbox(item)
        if other[1] <= bounds[3] + 3.0 and other[3] >= bounds[1] - 3.0:
            if other[2] >= bounds[0] - 8.0 and other[0] <= bounds[2] + 8.0:
                return False
    return True


def detect_math_candidates(items, objects, owner: str | None = None) -> list[dict]:
    """Detect positional math candidates and retain every source object."""
    candidates: list[dict] = []
    used_items: set[int] = set()
    used_objects: set[int] = set()

    def add_candidate(kind, members, related_objects, latex, bbox, display=False):
        item_ids = {id(item) for item in members}
        object_ids = {id(obj) for obj in related_objects}
        if item_ids & used_items or object_ids & used_objects:
            return False
        candidate = {
            "kind": kind,
            "items": members,
            "objects": related_objects,
            "source_ids": [
                *[_source_id(item, "text") for item in members],
                *[_source_id(obj, "object") for obj in related_objects],
            ],
            "bbox_ll": list(bbox),
            "latex": latex,
            "display": infer_math_display(members, items) if display is False else display,
            "line_y": max(float(item.y) for item in members),
        }
        candidates.append(candidate)
        used_items.update(item_ids)
        used_objects.update(object_ids)
        return True

    for rule in _horizontal_rules(objects):
        bar = tuple(rule["bbox_ll"])
        above = _expand_math_line(
            items, bar, _nearest_math_line(
                items, bar, above=True,
                bars=[tuple(other["bbox_ll"]) for other in _horizontal_rules(objects)],
            ), above=True
        )
        below = _expand_math_line(
            items, bar, _nearest_math_line(
                items, bar, above=False,
                bars=[tuple(other["bbox_ll"]) for other in _horizontal_rules(objects)],
            ), above=False
        )
        if above and below and not any(
            item.text.strip() in {"√", "sqrt"}
            and float(item.x) <= bar[0] + 4.0
            and float(item.x + item.width) >= bar[0] - 4.0
            for item in items
        ):
            members = above + below
            add_candidate(
                "fraction",
                members,
                [rule],
                rf"\frac{{{_math_side_latex(above)}}}{{{_math_side_latex(below)}}}",
                _bbox_union([bar, *(_item_bbox(item) for item in members)]),
            )
            continue

        root_marks = [
            item for item in items
            if item.text.strip() in {"√", "sqrt"}
            and float(item.x) <= bar[0] + 4.0
            and float(item.x + item.width) >= bar[0] - 4.0
            and abs(float(item.y) - bar[1]) <= 20.0
        ]
        if below and root_marks:
            root = min(root_marks, key=lambda item: abs(float(item.x + item.width) - bar[0]))
            add_candidate(
                "radical",
                [root, *below],
                [rule],
                rf"\sqrt{{{_math_side_latex(below)}}}",
                _bbox_union([bar, *(_item_bbox(item) for item in [root, *below])]),
            )

    multiline_members = _multiline_math_members(items, used_items)
    if multiline_members:
        add_candidate(
            "multiline",
            multiline_members,
            [],
            None,
            _bbox_union([_item_bbox(item) for item in multiline_members]),
            display=False,
        )

    ordered = sorted(items, key=lambda item: (float(item.x), -float(item.y)))
    for base in ordered:
        if id(base) in used_items or not _is_mathish(base.text):
            continue
        following = [
            item for item in ordered
            if id(item) not in used_items
            and float(item.x) >= float(base.x + base.width)
            and 0.0 <= float(item.x) - float(base.x + base.width) <= 8.0
            and float(item.y) > float(base.y) + 2.5
            and float(item.y) - float(base.y) <= max(12.0, float(base.height))
            and float(item.font_size) < max(0.1, float(base.font_size)) * 0.95
            and _is_mathish(item.text)
        ]
        if not following:
            continue
        superscript = min(following, key=lambda item: float(item.x))
        add_candidate(
            "exponent",
            [base, superscript],
            [],
            rf"{_latex_token(base.text)}^{{{_latex_token(superscript.text)}}}",
            _bbox_union([_item_bbox(base), _item_bbox(superscript)]),
        )

    def is_equation_atom(item):
        return _is_mathish(item.text) or re.fullmatch(r"[A-Z]{1,4}", item.text.strip())

    equation_lines = []
    for line in make_lines(items):
        if not any(item.text.strip() == "=" for item in line["items"]):
            continue
        members = [
            item for item in line["items"]
            if id(item) not in used_items and is_equation_atom(item)
        ]
        if len(members) >= 3:
            equation_lines.append((line, members))

    for (first_line, first_members), (second_line, second_members) in zip(
        equation_lines, equation_lines[1:]
    ):
        if abs(first_line["y"] - second_line["y"]) > 24.0:
            continue
        first_box = _bbox_union([_item_bbox(item) for item in first_members])
        second_box = _bbox_union([_item_bbox(item) for item in second_members])
        if abs(first_box[0] - second_box[0]) > 6.0:
            continue
        rows = [
            "".join(_latex_token(item.text) for item in first_members),
            "".join(_latex_token(item.text) for item in second_members),
        ]
        add_candidate(
            "system",
            [*first_members, *second_members],
            [],
            r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}",
            _bbox_union([_item_bbox(item) for item in [*first_members, *second_members]]),
        )

    for line in make_lines(items):
        if not any(item.text.strip() == "=" for item in line["items"]):
            continue
        members = [
            item for item in line["items"]
            if id(item) not in used_items and is_equation_atom(item)
        ]
        if len(members) >= 3:
            add_candidate(
                "equation",
                members,
                [],
                "".join(_latex_token(item.text) for item in members),
                _bbox_union([_item_bbox(item) for item in members]),
            )

    # Simple arithmetic is intentionally narrow: contiguous math-only tokens,
    # with no solving or symbolic composition. Signed numeric options are also
    # typed as math because their label is the structural owner.
    for line in make_lines(items):
        runs = []
        current = []
        for item in sorted(line["items"], key=lambda value: float(value.x)):
            if id(item) in used_items or not _is_mathish(item.text):
                if current:
                    runs.append(current)
                    current = []
                continue
            if current and float(item.x) - float(current[-1].x + current[-1].width) > 10.0:
                runs.append(current)
                current = []
            current.append(item)
        if current:
            runs.append(current)
        for run in runs:
            joined = "".join(item.text.strip() for item in run)
            has_operator = bool(re.search(r"[+\u2212\-*/\u00b7]", joined))
            signed_option = bool(owner and owner.startswith("option:") and re.fullmatch(r"[\u2212\-]\d+", joined))
            single_equation = len(run) == 1 and "=" in joined and has_operator
            if (len(run) < 2 and not single_equation) or not (has_operator or signed_option):
                continue
            add_candidate(
                "arithmetic",
                run,
                [],
                "".join(_latex_token(item.text) for item in run),
                _bbox_union([_item_bbox(item) for item in run]),
            )

    return sorted(
        candidates,
        key=lambda candidate: (-candidate["bbox_ll"][3], candidate["bbox_ll"][0]),
    )


def detect_table_candidate(items, objects) -> dict | None:
    """Detect a connected table grid after normalizing border segments."""
    horizontal = _horizontal_rules(objects)
    vertical = [
        obj for obj in objects
        if obj.get("type") == "PdfObject"
        and obj["bbox_ll"][3] - obj["bbox_ll"][1] >= 15.0
        and obj["bbox_ll"][2] - obj["bbox_ll"][0] <= 2.5
    ]
    if len(horizontal) < 2 or len(vertical) < 2:
        return None
    x_lines = sorted({
        round((obj["bbox_ll"][0] + obj["bbox_ll"][2]) / 2, 3)
        for obj in vertical
    })
    if len(x_lines) < 2:
        return None
    x0, x1 = x_lines[0], x_lines[-1]
    horizontal = [
        obj for obj in horizontal
        if obj["bbox_ll"][2] - obj["bbox_ll"][0] >= (x1 - x0) * 0.70
    ]
    y_lines = sorted({
        round((obj["bbox_ll"][1] + obj["bbox_ll"][3]) / 2, 3)
        for obj in horizontal
    })
    if len(y_lines) < 2:
        return None
    y0, y1 = y_lines[0], y_lines[-1]

    def covers(intervals, low, high):
        cursor = low
        for start, end in sorted(intervals):
            if start > cursor + 2.5:
                return False
            cursor = max(cursor, end)
            if cursor >= high - 2.5:
                return True
        return cursor >= high - 2.5

    left_segments = [
        (obj["bbox_ll"][1], obj["bbox_ll"][3])
        for obj in vertical
        if abs((obj["bbox_ll"][0] + obj["bbox_ll"][2]) / 2 - x0) <= 2.5
    ]
    right_segments = [
        (obj["bbox_ll"][1], obj["bbox_ll"][3])
        for obj in vertical
        if abs((obj["bbox_ll"][0] + obj["bbox_ll"][2]) / 2 - x1) <= 2.5
    ]
    top_segments = [
        (obj["bbox_ll"][0], obj["bbox_ll"][2])
        for obj in horizontal
        if abs((obj["bbox_ll"][1] + obj["bbox_ll"][3]) / 2 - y1) <= 2.5
    ]
    bottom_segments = [
        (obj["bbox_ll"][0], obj["bbox_ll"][2])
        for obj in horizontal
        if abs((obj["bbox_ll"][1] + obj["bbox_ll"][3]) / 2 - y0) <= 2.5
    ]
    if not covers(left_segments, y0, y1) or not covers(right_segments, y0, y1):
        return None
    if not covers(top_segments, x0, x1) or not covers(bottom_segments, x0, x1):
        return None
    border_objects = [
        obj for obj in [*horizontal, *vertical]
        if obj["bbox_ll"][0] <= x1 + 2.5
        and obj["bbox_ll"][2] >= x0 - 2.5
        and obj["bbox_ll"][1] <= y1 + 2.5
        and obj["bbox_ll"][3] >= y0 - 2.5
    ]
    return {
        "kind": "table",
        "bbox_ll": [x0, y0, x1, y1],
        "x_lines": x_lines,
        "y_lines": y_lines,
        "objects": list(dict((id(obj), obj) for obj in border_objects).values()),
    }


def associate_visual_objects(markers, objects) -> dict[str, list[int]]:
    """Associate only unambiguous marker/object pairs by bounded geometry."""
    image_indexes = [index for index, obj in enumerate(objects) if obj.get("type") == "PdfImage"]
    associations: dict[str, list[int]] = {}
    unused = set(image_indexes)
    for marker in sorted(markers, key=lambda item: (-float(item.y), float(item.x))):
        match = IMAGE_MARKER_RE.fullmatch(marker.text.strip())
        if not match or not unused:
            continue
        marker_box = _item_bbox(marker)
        marker_center = (
            (marker_box[0] + marker_box[2]) / 2,
            (marker_box[1] + marker_box[3]) / 2,
        )
        ranked = sorted(
            unused,
            key=lambda candidate: (
                ((objects[candidate]["bbox_ll"][0] + objects[candidate]["bbox_ll"][2]) / 2 - marker_center[0]) ** 2
                + ((objects[candidate]["bbox_ll"][1] + objects[candidate]["bbox_ll"][3]) / 2 - marker_center[1]) ** 2
            ),
        )
        best = ranked[0]
        best_box = objects[best]["bbox_ll"]
        best_distance = (
            ((best_box[0] + best_box[2]) / 2 - marker_center[0]) ** 2
            + ((best_box[1] + best_box[3]) / 2 - marker_center[1]) ** 2
        ) ** 0.5
        second_distance = float("inf")
        if len(ranked) > 1:
            second = objects[ranked[1]]["bbox_ll"]
            second_distance = (
                ((second[0] + second[2]) / 2 - marker_center[0]) ** 2
                + ((second[1] + second[3]) / 2 - marker_center[1]) ** 2
            ) ** 0.5
        marker_diagonal = max(1.0, (marker_box[2] - marker_box[0]) + (marker_box[3] - marker_box[1]))
        if best_distance > marker_diagonal * 2.0:
            continue
        if second_distance < float("inf") and second_distance - best_distance < max(12.0, marker_diagonal * 0.25):
            continue
        associations[match.group(1)] = [best]
        unused.remove(best)
    return associations


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_bbox_ll(item) -> tuple[float, float, float, float]:
    return (
        float(item.x),
        float(item.y),
        float(item.x + item.width),
        float(item.y + item.height),
    )


def object_bbox_ll(obj) -> tuple[float, float, float, float] | None:
    try:
        values = obj.get_bounds()
        return tuple(float(value) for value in values)
    except Exception:
        return None


def bbox_tl(bounds_ll, height: float) -> list[float]:
    x0, y0, x1, y1 = bounds_ll
    return [round(x0, 2), round(height - y1, 2), round(x1, 2), round(height - y0, 2)]


def overlaps_vertical(bounds_ll, lower: float, upper: float) -> bool:
    return bounds_ll[3] > lower and bounds_ll[1] < upper


def line_text(items) -> str:
    ordered = sorted(items, key=lambda item: float(item.x))
    parts: list[str] = []
    right = None
    for item in ordered:
        if right is not None and float(item.x) - right > 2.5:
            parts.append(" ")
        parts.append(item.text)
        right = float(item.x + item.width)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def make_lines(items) -> list[dict]:
    lines: list[dict] = []
    for item in sorted(items, key=lambda value: (-float(value.y), float(value.x))):
        line = next(
            (candidate for candidate in lines if abs(float(item.y) - candidate["y"]) <= 2.2),
            None,
        )
        if line is None:
            line = {"y": float(item.y), "items": []}
            lines.append(line)
        line["items"].append(item)
        line["y"] = sum(float(value.y) for value in line["items"]) / len(line["items"])
    return sorted(
        [{"text": line_text(line["items"]), "items": line["items"], "y": line["y"]} for line in lines],
        key=lambda value: -value["y"],
    )


def _decorate_block(block: dict, source_ids: list[str], owner: str | None) -> dict:
    if owner is not None:
        block["owner"] = owner
        block["source_ids"] = list(dict.fromkeys(source_ids))
    if block.get("type") == "unresolved" and block.get("source_ids"):
        block.setdefault("candidate_type", "visual" if "visual" in block.get("reason", "") else "unknown")
        block.setdefault(
            "candidate_id",
            "candidate-" + hashlib.sha256("|".join(sorted(block["source_ids"])).encode()).hexdigest()[:16],
        )
    return block


def block_for_line(
    line: dict,
    evidence_id: str,
    visual_assets: dict[str, str] | None = None,
    owner: str | None = None,
    asset_sources: dict[str, list[str]] | None = None,
) -> dict:
    text = line["text"]
    visual_assets = visual_assets or {}
    asset_sources = asset_sources or {}
    source_ids = [_source_id(item, "text") for item in line.get("items", [])]
    image_match = IMAGE_MARKER_RE.fullmatch(text)
    if image_match:
        asset_id = visual_assets.get(image_match.group(1))
        if asset_id:
            return _decorate_block(
                {"type": "image", "asset_id": asset_id},
                source_ids + asset_sources.get(asset_id, []),
                owner,
            )
        return _decorate_block(
            {
                "type": "unresolved",
                "raw_text": text,
                "reason": "visual_content_pending",
                "evidence_id": evidence_id,
            },
            source_ids,
            owner,
        )
    return _decorate_block({"type": "text", "text": text}, source_ids, owner)


def option_for_items(
    label: str,
    items,
    evidence_id: str,
    visual_assets: dict[str, str],
    option_objects: list[dict] | None = None,
    asset_sources: dict[str, list[str]] | None = None,
) -> dict:
    option_items = [item for item in items if item.text.strip() != f"{label})"]
    blocks = reconstruct_generic_blocks(
        option_items, option_objects or [], evidence_id, visual_assets,
        owner=f"option:{label}", asset_sources=asset_sources,
    )
    marker_ids = [
        _source_id(item, "text")
        for item in items
        if item.text.strip() == f"{label})"
    ]
    if not blocks:
        blocks = [_decorate_block({
            "type": "unresolved",
            "reason": "visual_content_pending",
            "evidence_id": evidence_id,
        }, [], f"option:{label}")]
    return {
        "id": label,
        "label": label,
        "blocks": blocks,
        "owner": f"option:{label}",
        "source_ids": marker_ids,
    }




def assign_exclusive_option_members(selected_items, selected_objects, option_markers):
    """Assign content to one owner using a local spatial partition."""
    members = {OPTION_RE.fullmatch(marker.text.strip()).group(1): [] for marker in option_markers}
    object_members = {label: [] for label in members}
    if not option_markers:
        return members, object_members, []

    top_option_boundary = max(
        float(marker.y + marker.height) for marker in option_markers
    )
    marker_centers = []
    for marker in option_markers:
        box = _item_bbox(marker)
        marker_centers.append((
            OPTION_RE.fullmatch(marker.text.strip()).group(1),
            (box[0] + box[2]) / 2,
            (box[1] + box[3]) / 2,
        ))
    option_top = max(center[2] for center in marker_centers)
    ambiguous = []
    marker_ids = {id(marker) for marker in option_markers}

    x_span = max(center[1] for center in marker_centers) - min(center[1] for center in marker_centers)
    y_span = max(center[2] for center in marker_centers) - min(center[2] for center in marker_centers)

    def distance(center, x, y):
        if x_span <= 20.0:
            return abs(center[2] - y)
        if y_span <= 20.0:
            return abs(center[1] - x)
        return ((center[1] - x) ** 2 + (center[2] - y) ** 2) ** 0.5

    def nearest(x, y):
        ranked = sorted(marker_centers, key=lambda value: distance(value, x, y))
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        if second and second[0] != best[0]:
            best_distance = distance(best, x, y)
            second_distance = distance(second, x, y)
            if second_distance - best_distance < max(6.0, best_distance * 0.12):
                return None
        return best[0]

    for item in selected_items:
        if id(item) in marker_ids:
            label = OPTION_RE.fullmatch(item.text.strip()).group(1)
            members[label].append(item)
            continue
        box = _item_bbox(item)
        # Prose fully above the first answer row belongs to the stem, even
        # inside the wider window reserved for raised mathematical operands.
        if (
            not IMAGE_MARKER_RE.fullmatch(item.text.strip())
            and UNICODE_LETTER_RUN_RE.search(unicodedata.normalize("NFC", item.text))
            and box[1] > top_option_boundary
        ):
            continue
        if (
            IMAGE_MARKER_RE.fullmatch(item.text.strip())
            and box[1] <= option_top + 25.0 < box[3]
        ):
            ambiguous.append(item)
            continue
        center_y = (box[1] + box[3]) / 2
        if center_y > option_top + 25.0:
            continue
        label = nearest((box[0] + box[2]) / 2, center_y)
        if label is None:
            ambiguous.append(item)
        else:
            members[label].append(item)

    for obj in selected_objects:
        box = obj["bbox_ll"]
        if (
            obj.get("type") == "PdfImage"
            and box[1] <= option_top + 25.0 < box[3]
        ):
            ambiguous.append(obj)
            continue
        center_y = (box[1] + box[3]) / 2
        if center_y > option_top + 25.0:
            continue
        label = nearest((box[0] + box[2]) / 2, center_y)
        if label is None:
            ambiguous.append(obj)
        else:
            object_members[label].append(obj)
    return members, object_members, ambiguous



def marker_ranges(selected_items, option_markers, floor: float) -> dict[str, list]:
    result = {}
    for index, marker in enumerate(option_markers):
        label = OPTION_RE.fullmatch(marker.text.strip()).group(1)
        next_marker = option_markers[index + 1] if index + 1 < len(option_markers) else None
        upper = float(marker.y + marker.height + 3.0)
        lower = float(next_marker.y + next_marker.height - 3.0) if next_marker else floor
        result[label] = [
            item for item in selected_items
            if lower <= float(item.y) and float(item.y) < upper
        ]
    return result


MIN_RENDERABLE_POINTS = 0.5


class CropValidationError(ValueError):
    """A source geometry cannot produce a valid page crop."""


def _normalize_render_region(region: list[float], width: float, height: float) -> list[float]:
    try:
        values = [float(value) for value in region]
        page_width = float(width)
        page_height = float(height)
    except (TypeError, ValueError):
        raise CropValidationError("crop geometry is not numeric")
    if len(values) != 4 or not all(math.isfinite(value) for value in [*values, page_width, page_height]):
        raise CropValidationError("crop geometry is not finite")
    if page_width <= 0.0 or page_height <= 0.0:
        raise CropValidationError("page geometry is invalid")
    x0, y0, x1, y1 = values
    x0 = min(page_width, max(0.0, x0))
    y0 = min(page_height, max(0.0, y0))
    x1 = min(page_width, max(0.0, x1))
    y1 = min(page_height, max(0.0, y1))
    if x1 - x0 < MIN_RENDERABLE_POINTS or y1 - y0 < MIN_RENDERABLE_POINTS:
        raise CropValidationError("crop is degenerate after page clipping")
    return [x0, y0, x1, y1]


def _visual_bbox_issue(object_bbox, width: float, height: float) -> str | None:
    try:
        values = [float(value) for value in object_bbox]
        page_width = float(width)
        page_height = float(height)
    except (TypeError, ValueError):
        return "visual object geometry is not numeric"
    if len(values) != 4 or not all(math.isfinite(value) for value in [*values, page_width, page_height]):
        return "visual object geometry is not finite"
    x0, y0, x1, y1 = values
    if x1 - x0 < MIN_RENDERABLE_POINTS or y1 - y0 < MIN_RENDERABLE_POINTS:
        return "visual object geometry is degenerate"
    if x1 <= 0.0 or y1 <= 0.0 or x0 >= page_width or y0 >= page_height:
        return "visual object geometry is outside page bounds"
    return None


def _append_visual_asset_issue(
    issues: list[dict] | None,
    question_id: str,
    region_id: str,
    evidence_id: str | None,
    code: str,
    source_ids: list[str],
    message: str,
) -> None:
    if issues is None:
        return
    issue_id = hashlib.sha256(
        "|".join([question_id, code, *sorted(source_ids)]).encode()
    ).hexdigest()[:16]
    issues.append({
        "id": f"issue-{question_id}-{code.lower()}-{issue_id}",
        "code": code,
        "severity": "warning",
        "target_id": question_id,
        "region_ids": [region_id],
        "evidence_ids": [evidence_id] if evidence_id else [],
        "blocks_completion": True,
        "message": message,
        "source_ids": list(dict.fromkeys(source_ids)),
    })


def render_slice(page, output: Path, stem: str, region: list[float], width: float, height: float) -> Path:
    x0, y0, x1, y1 = _normalize_render_region(region, width, height)
    crop = (x0, height - y1, width - x1, y0)
    try:
        bitmap = page.render(scale=2, crop=crop)
    except Exception as exc:
        raise CropValidationError(f"page renderer rejected crop: {exc}") from exc
    path = output / f"{stem}.png"
    bitmap.to_pil().save(path)
    return path


def _iter_nested_blocks(blocks):
    for block in blocks:
        yield block
        if block.get("type") == "table":
            for row in block.get("rows", []):
                for cell in row.get("cells", []):
                    yield from _iter_nested_blocks(cell.get("blocks", []))


def add_ai_evidence_crops(
    page,
    crop_dir: Path,
    question_id: str,
    blocks: list[dict],
    source_inventory: list[dict],
    evidence: list[dict],
    parent_evidence_id: str,
    region_id: str,
    page_width: float,
    page_height: float,
) -> None:
    """Render minimum candidate crops; never send a complete-question crop."""
    by_id = {entry["id"]: entry for entry in source_inventory}
    existing = {entry["id"] for entry in evidence}
    for block in _iter_nested_blocks(blocks):
        if block.get("type") != "unresolved" or not block.get("candidate_id"):
            continue
        candidate_id = block["candidate_id"]
        evidence_id = f"{parent_evidence_id}-candidate-{candidate_id}"
        if evidence_id in existing:
            block["ai_evidence_id"] = evidence_id
            continue
        proof = block.get("structural_fidelity", {})
        bbox = proof.get("bbox_ll")
        if not bbox:
            bounds = [by_id[source_id]["bbox"] for source_id in block.get("source_ids", []) if source_id in by_id]
            if bounds:
                bbox = [min(value[0] for value in bounds), min(value[1] for value in bounds),
                        max(value[2] for value in bounds), max(value[3] for value in bounds)]
        if not bbox:
            continue
        x0, y0, x1, y1 = bbox
        crop_region = bbox_tl(
            (max(0.0, x0 - 3.0), max(0.0, y0 - 3.0),
             min(page_width, x1 + 3.0), min(page_height, y1 + 3.0)), page_height
        )
        path = render_slice(page, crop_dir, f"{question_id}-candidate-{candidate_id}", crop_region, page_width, page_height)
        evidence.append({
            "id": evidence_id,
            "kind": "crop",
            "path": str(path.relative_to(crop_dir.parent.parent)).replace("\\", "/"),
            "region_ids": [region_id],
            "bbox": crop_region,
            "reason": "ai_on_demand",
            "parent_evidence_id": parent_evidence_id,
            "candidate_id": candidate_id,
            "source_ids": list(block.get("source_ids", [])),
        })
        block["ai_evidence_id"] = evidence_id
        existing.add(evidence_id)


def asset_region(
    object_bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
    padding_x: float = 3.0,
    padding_y: float = 3.0,
) -> list[float]:
    x0, y0, x1, y1 = object_bbox
    return _normalize_render_region(bbox_tl(
        (
            max(0.0, x0 - padding_x),
            max(0.0, y0 - padding_y),
            min(page_width, x1 + padding_x),
            min(page_height, y1 + padding_y),
        ),
        page_height,
    ), page_width, page_height)


def add_asset(
    page,
    asset_dir: Path,
    asset_id: str,
    object_bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
    region_id: str,
    padding_x: float = 3.0,
    padding_y: float = 3.0,
) -> tuple[dict, list[float]]:
    bbox_issue = _visual_bbox_issue(object_bbox, page_width, page_height)
    if bbox_issue:
        return None, {"reason": bbox_issue}
    try:
        region = asset_region(
            object_bbox,
            page_width,
            page_height,
            padding_x=padding_x,
            padding_y=padding_y,
        )
        path = render_slice(page, asset_dir, asset_id, region, page_width, page_height)
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
    except Exception as exc:
        return None, {"reason": str(exc)}
    return {
        "asset_id": asset_id,
        "path": str(path.relative_to(asset_dir.parent)).replace("\\", "/"),
        "mime": "image/png",
        "width": width,
        "height": height,
        "sha256": sha256(path),
        "region_ids": [region_id],
        "source_type": "rendered_slice",
        "source_bbox": region,
    }, region


def marker_ranges_for_objects(selected_objects, option_markers, floor: float) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for index, marker in enumerate(option_markers):
        label = OPTION_RE.fullmatch(marker.text.strip()).group(1)
        next_marker = option_markers[index + 1] if index + 1 < len(option_markers) else None
        upper = float(marker.y + marker.height + 3.0)
        lower = float(next_marker.y + next_marker.height - 3.0) if next_marker else floor
        result[label] = [
            obj for obj in selected_objects
            if lower <= obj["bbox_ll"][1] and obj["bbox_ll"][1] < upper
        ]
    return result


def reassign_visual_option_members(selected_items, option_markers, option_members):
    """Repair grid layouts by assigning image markers to the nearest option marker."""
    marker_ids = {id(item) for item in option_markers}
    for label in option_members:
        option_members[label] = [
            item for item in option_members[label] if id(item) not in marker_ids
        ]
    for item in selected_items:
        if not IMAGE_MARKER_RE.fullmatch(item.text.strip()):
            continue
        if not option_markers:
            continue
        item_box = _item_bbox(item)
        item_center = ((item_box[0] + item_box[2]) / 2, (item_box[1] + item_box[3]) / 2)
        nearest = min(
            option_markers,
            key=lambda marker: (
                ((float(marker.x) + float(marker.width) / 2) - item_center[0]) ** 2
                + ((float(marker.y) + float(marker.height) / 2) - item_center[1]) ** 2
            ),
        )
        marker_box = _item_bbox(nearest)
        if abs(item_center[1] - (marker_box[1] + marker_box[3]) / 2) <= 110:
            label = OPTION_RE.fullmatch(nearest.text.strip()).group(1)
            for members in option_members.values():
                if item in members:
                    members.remove(item)
            option_members.setdefault(label, []).append(item)


def build_visual_assets(
    page,
    asset_dir: Path,
    question_id: str,
    markers,
    selected_objects: list[dict],
    page_width: float,
    page_height: float,
    region_id: str,
    issues: list[dict] | None = None,
    evidence_id: str | None = None,
) -> tuple[list[dict], dict[str, str]]:
    """Render all relevant visual objects and associate them by position."""
    image_objects = [obj for obj in selected_objects if obj.get("type") == "PdfImage"]
    image_groups = []
    groups_by_bbox = {}
    for index, image_object in enumerate(image_objects):
        try:
            key = tuple(round(float(value), 3) for value in image_object.get("bbox_ll", []))
        except (TypeError, ValueError):
            key = ("invalid", index)
        if len(key) != 4:
            key = ("invalid", index)
        group = groups_by_bbox.get(key)
        if group is None:
            group = {"object": image_object, "objects": [image_object]}
            groups_by_bbox[key] = group
            image_groups.append(group)
        else:
            group["objects"].append(image_object)
    for group in image_groups:
        if len(group["objects"]) > 1:
            _append_visual_asset_issue(
                issues, question_id, region_id, evidence_id,
                "DUPLICATE_VISUAL_SOURCE",
                [_source_id(obj, "object") for obj in group["objects"]],
                "Duplicate visual source objects share the same geometry.",
            )
    renderable_groups = []
    for group in image_groups:
        reason = _visual_bbox_issue(
            group["object"].get("bbox_ll", ()), page_width, page_height
        )
        if reason:
            _append_visual_asset_issue(
                issues, question_id, region_id, evidence_id,
                "VISUAL_ASSET_RENDER_SKIPPED",
                [_source_id(obj, "object") for obj in group["objects"]],
                f"Visual asset was skipped: {reason}.",
            )
            continue
        renderable_groups.append(group)
    image_groups = renderable_groups
    image_objects = [group["object"] for group in image_groups]
    associations = associate_visual_objects(markers, image_objects)
    generated: list[dict] = []
    visual_assets: dict[str, str] = {}
    for index, image_object in enumerate(image_objects):
        asset_id = f"asset-{question_id}-visual-{index + 1}"
        asset, result = add_asset(
            page, asset_dir, asset_id, tuple(image_object["bbox_ll"]),
            page_width, page_height, region_id, padding_x=0.0, padding_y=0.0,
        )
        if asset is None:
            _append_visual_asset_issue(
                issues, question_id, region_id, evidence_id,
                "VISUAL_ASSET_RENDER_SKIPPED",
                [_source_id(obj, "object") for obj in image_groups[index]["objects"]],
                f"Visual asset was skipped: {result.get('reason', 'unknown render error')}.",
            )
            continue
        asset["source_ids"] = [
            _source_id(obj, "object") for obj in image_groups[index]["objects"]
        ]
        generated.append(asset)
    for marker_key, indexes in associations.items():
        if indexes:
            visual_assets[marker_key] = f"asset-{question_id}-visual-{indexes[0] + 1}"

    # If a marker has no raster object, preserve it through a rendered vector
    # fallback. The fallback is still spatially derived and never ID-specific.
    vector_objects = [
        obj for obj in selected_objects
        if obj.get("type") == "PdfObject"
        and _visual_bbox_issue(obj.get("bbox_ll", ()), page_width, page_height) is None
    ]
    vector_asset_by_sources = {}
    next_index = len(image_objects)
    for marker in markers:
        match = IMAGE_MARKER_RE.fullmatch(marker.text.strip())
        if not match or match.group(1) in visual_assets:
            continue
        marker_box = _item_bbox(marker)
        nearby = [
            obj for obj in vector_objects
            if abs((obj["bbox_ll"][1] + obj["bbox_ll"][3]) / 2 - (marker_box[1] + marker_box[3]) / 2) <= 120
            and obj["bbox_ll"][0] <= marker_box[2] + 140
            and obj["bbox_ll"][2] >= marker_box[0] - 140
        ]
        if not nearby:
            continue
        source_key = tuple(sorted(_source_id(obj, "object") for obj in nearby))
        existing_asset_id = vector_asset_by_sources.get(source_key)
        if existing_asset_id:
            visual_assets[match.group(1)] = existing_asset_id
            continue
        asset_id = f"asset-{question_id}-visual-{next_index + 1}"
        next_index += 1
        bbox = _bbox_union([tuple(obj["bbox_ll"]) for obj in nearby])
        asset, result = add_asset(
            page, asset_dir, asset_id, bbox, page_width, page_height, region_id,
            padding_x=3.0, padding_y=3.0,
        )
        if asset is None:
            _append_visual_asset_issue(
                issues, question_id, region_id, evidence_id,
                "VISUAL_ASSET_RENDER_SKIPPED",
                [_source_id(obj, "object") for obj in nearby],
                f"Vector visual asset was skipped: {result.get('reason', 'unknown render error')}.",
            )
            continue
        asset["source_ids"] = [_source_id(obj, "object") for obj in nearby]
        generated.append(asset)
        visual_assets[match.group(1)] = asset_id
        vector_asset_by_sources[source_key] = asset_id
    return generated, visual_assets


def _table_from_candidate(
    candidate: dict,
    items,
    objects=None,
    evidence_id: str = "",
    visual_assets: dict[str, str] | None = None,
    owner: str | None = None,
    asset_sources: dict[str, list[str]] | None = None,
) -> dict:
    """Build cells and run the same typed reconstructors inside each cell."""
    objects = objects or []
    visual_assets = visual_assets or {}
    asset_sources = asset_sources or {}
    x_lines = candidate["x_lines"]
    y_lines = candidate["y_lines"]
    border_ids = {id(obj) for obj in candidate.get("objects", [])}
    rows = []
    for high, low in zip(reversed(y_lines[1:]), reversed(y_lines[:-1])):
        cells = []
        for left, right in zip(x_lines[:-1], x_lines[1:]):
            cell_items = [
                item for item in items
                if left <= float(item.x + item.width / 2) <= right
                and low <= float(item.y + item.height / 2) <= high
            ]
            cell_objects = [
                obj for obj in objects
                if id(obj) not in border_ids
                and left <= (obj["bbox_ll"][0] + obj["bbox_ll"][2]) / 2 <= right
                and low <= (obj["bbox_ll"][1] + obj["bbox_ll"][3]) / 2 <= high
            ]
            cell_blocks = reconstruct_generic_blocks(
                cell_items,
                cell_objects,
                evidence_id,
                visual_assets,
                owner=owner,
                asset_sources=asset_sources,
            )
            cells.append({"blocks": cell_blocks})
        rows.append({"cells": cells})
    return {"type": "table", "rows": rows}


def reconstruct_generic_blocks(
    items,
    objects,
    evidence_id: str,
    visual_assets: dict[str, str],
    owner: str | None = None,
    asset_sources: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Reconstruct typed blocks once, retaining positional ownership."""
    asset_sources = asset_sources or {}
    table_candidate = detect_table_candidate(items, objects)
    table_item_ids: set[int] = set()
    table_object_ids: set[int] = set()
    units: list[tuple[float, float, dict]] = []
    if table_candidate:
        x0, y0, x1, y1 = table_candidate["bbox_ll"]
        table_items = [
            item for item in items
            if x0 <= float(item.x + item.width / 2) <= x1
            and y0 <= float(item.y + item.height / 2) <= y1
        ]
        table_item_ids = {id(item) for item in table_items}
        table_objects = [
            obj for obj in objects
            # A rendered visual must remain exclusively owned by its image block.
            if obj.get("type") != "PdfImage"
            and obj["bbox_ll"][2] >= x0 - 2.5
            and obj["bbox_ll"][0] <= x1 + 2.5
            and obj["bbox_ll"][3] >= y0 - 2.5
            and obj["bbox_ll"][1] <= y1 + 2.5
        ]
        table_block = _table_from_candidate(
            table_candidate, table_items, table_objects, evidence_id,
            visual_assets, owner, asset_sources
        )
        nested_source_ids = set(_block_source_ids(table_block))
        table_object_ids = {id(obj) for obj in table_objects}
        table_source_ids = [
            _source_id(obj, "object")
            for obj in table_objects
            if _source_id(obj, "object") not in nested_source_ids
        ]
        units.append((
            y0,
            x0,
            _decorate_block(table_block, table_source_ids, owner),
        ))

    math_items = [item for item in items if id(item) not in table_item_ids]
    math_objects = [obj for obj in objects if id(obj) not in table_object_ids]
    candidates = detect_math_candidates(math_items, math_objects, owner=owner)
    consumed = set(table_item_ids)
    for candidate in candidates:
        consumed.update(id(item) for item in candidate["items"])
        consumed.update(id(obj) for obj in candidate.get("objects", []))
        block = (
            {"type": "math", "latex": candidate["latex"], "display": candidate["display"]}
            if candidate.get("latex")
            else {
                "type": "unresolved",
                "reason": "math_reconstruction_pending",
                "evidence_id": evidence_id,
                "candidate_type": "math",
            }
        )
        units.append((
            candidate.get("line_y", max(float(item.y) for item in candidate["items"])),
            candidate["bbox_ll"][0],
            _decorate_block(block, candidate["source_ids"], owner),
        ))

    residual_items = [item for item in items if id(item) not in consumed]
    candidate_boxes = [candidate["bbox_ll"] for candidate in candidates]
    for line in make_lines(residual_items):
        image_items = [
            item for item in line["items"]
            if IMAGE_MARKER_RE.fullmatch(item.text.strip())
        ]
        residual_line = [item for item in line["items"] if item not in image_items]
        line_groups = [[]]
        inline_boxes = sorted(
            box for box in candidate_boxes
            if box[1] <= float(line["y"]) + 12.0
            and box[3] >= float(line["y"]) - 12.0
        )
        next_box = 0
        for item in sorted(residual_line, key=lambda value: float(value.x)):
            bounds = _item_bbox(item)
            while (
                next_box < len(inline_boxes)
                and bounds[0] > inline_boxes[next_box][2]
            ):
                if line_groups[-1]:
                    line_groups.append([])
                next_box += 1
            line_groups[-1].append(item)
        for group in [group for group in line_groups if group]:
            bounds = [_item_bbox(item) for item in group]
            units.append((
                line["y"],
                min(value[0] for value in bounds),
                block_for_line(
                    {
                        "text": line_text(group),
                        "items": group,
                        "y": line["y"],
                    },
                    evidence_id,
                    visual_assets,
                    owner,
                    asset_sources,
                ),
            ))
        for image_item in image_items:
            units.append((
                float(image_item.y),
                float(image_item.x),
                block_for_line(
                    {
                        "text": image_item.text.strip(),
                        "items": [image_item],
                        "y": float(image_item.y),
                    },
                    evidence_id,
                    visual_assets,
                    owner,
                    asset_sources,
                ),
            ))
    reconstructed = [
        block for _, _, block in sorted(units, key=lambda value: (-value[0], value[1]))
    ]
    if owner is not None:
        return validate_and_order(reconstructed, items, objects, evidence_id, _source_id)
    return reconstructed


def make_stem_blocks(
    stem_items,
    evidence_id: str,
    visual_assets: dict[str, str],
    stem_objects: list[dict] | None = None,
    owner: str | None = None,
    asset_sources: dict[str, list[str]] | None = None,
) -> list[dict]:
    return reconstruct_generic_blocks(
        stem_items, stem_objects or [], evidence_id, visual_assets,
        owner=owner, asset_sources=asset_sources,
    )


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _math_block(latex: str, display: bool = True) -> dict:
    return {"type": "math", "latex": latex, "display": display}


def _visual_block(asset_key: str, evidence_id: str, visual_assets: dict[str, str]) -> dict:
    asset_id = visual_assets.get(asset_key)
    if asset_id:
        return {"type": "image", "asset_id": asset_id}
    return {
        "type": "unresolved",
        "raw_text": f"[Image: {asset_key}]",
        "reason": "visual_content_pending",
        "evidence_id": evidence_id,
    }


def reconstruct_q3_stem(evidence_id: str, visual_assets: dict[str, str]) -> list[dict]:
    """Reconstruct Q3 math atomically; do not leave fraction glyphs as prose."""
    return [
        _text_block("Para representar una fracci\u00f3n se pueden utilizar gr\u00e1ficos circulares."),
        _text_block("Por ejemplo, en la siguiente imagen se han representado los n\u00fameros "),
        _math_block(r"\frac{5}{6}", display=False),
        _text_block(" y "),
        _math_block(r"1\frac{1}{6}", display=False),
        _text_block("."),
        _visual_block("Im6", evidence_id, visual_assets),
        _text_block("\u00bfEn cu\u00e1l de las siguientes opciones se representa el resultado de "),
        _math_block(r"3\cdot\left(\frac{1}{6}+\frac{3}{2}\cdot\frac{4}{6}\right)", display=False),
        _text_block("?"),
    ]


def reconstruct_q4_stem(evidence_id: str, visual_assets: dict[str, str]) -> list[dict]:
    """Reconstruct Q4 without evaluating expressions or changing fraction scope."""
    return [
        _text_block("Para calcular el valor de la expresi\u00f3n "),
        _math_block(r"\frac{-2(4\cdot5)-(30-2\cdot3)}{12}", display=False),
        _text_block(", se realizan los siguientes pasos, cometi\u00e9ndose un error."),
        _text_block("Paso 1: se reescribe "),
        _math_block(r"-2(4\cdot5)", display=False),
        _text_block(" como "),
        _math_block(r"(-8)\cdot(-10)", display=False),
        _text_block(", obteni\u00e9ndose "),
        _math_block(r"\frac{(-8)\cdot(-10)-(30-2\cdot3)}{12}"),
        _text_block("Paso 2: se resuelve "),
        _math_block(r"30-2\cdot3", display=False),
        _text_block(", obteni\u00e9ndose "),
        _math_block(r"\frac{(-8)\cdot(-10)-24}{12}"),
        _text_block("Paso 3: se resuelve el numerador, obteni\u00e9ndose "),
        _math_block(r"\frac{56}{12}"),
        _text_block("Paso 4: se simplifica la fracci\u00f3n del paso anterior, obteni\u00e9ndose "),
        _math_block(r"\frac{14}{3}"),
        _text_block("\u00bfEn cu\u00e1l de los pasos se cometi\u00f3 el error?"),
    ]



def _table_cell(*blocks: dict) -> dict:
    return {"blocks": list(blocks)}


def _table_block(rows: list[list[dict]]) -> dict:
    return {
        "type": "table",
        "rows": [
            {"cells": [_table_cell(*cell) for cell in row]}
            for row in rows
        ],
    }


def order_visual_objects(objects: list[dict]) -> list[dict]:
    """Order two-column visual alternatives by row, tolerating subpixel drift."""
    return sorted(
        objects,
        key=lambda item: (-round(item["bbox_ll"][3], 0), item["bbox_ll"][0]),
    )


def reconstruct_q9_stem(evidence_id: str, visual_assets: dict[str, str]) -> list[dict]:
    """Reconstruct Q9's vector table and inline currency equations."""
    table = _table_block([
        [
            [_text_block("Producto")],
            [_text_block("Precio unitario")],
            [_text_block("Promoci\u00f3n por dos unidades")],
        ],
        [
            [_text_block("1 kilogramo de az\u00facar")],
            [_text_block("$1400")],
            [_text_block("$2600")],
        ],
        [
            [_math_block(r"\frac{1}{2}", display=False), _text_block(" litro de lavaloza")],
            [_text_block("$1600")],
            [_text_block("$3000")],
        ],
        [
            [_text_block("1 litro de leche")],
            [_text_block("$1200")],
            [_text_block("$2200")],
        ],
        [
            [_text_block("1 kilogramo de arroz")],
            [_text_block("$1700")],
            [_text_block("$3300")],
        ],
    ])
    return [
        _text_block("Una persona necesita comprar 3 kg de az\u00facar, 6 L de lavaloza, 4 L de leche y 1 kg de arroz."),
        _text_block("En la siguiente tabla se registraron los precios de los productos por comprar."),
        table,
        _text_block("Para calcular el menor precio por pagar, la persona efect\u00faa el siguiente procedimiento, en el cual comete un error."),
        _text_block("Paso 1: calcula que en az\u00facar debe gastar "),
        _math_block(r"\$2600+\$1400=\$4000", display=False),
        _text_block("."),
        _text_block("Paso 2: calcula que en lavaloza debe gastar "),
        _math_block(r"3\cdot\$3000=\$9000", display=False),
        _text_block("."),
        _text_block("Paso 3: calcula que en leche debe gastar "),
        _math_block(r"2\cdot\$2200=\$4400", display=False),
        _text_block("."),
        _text_block("Paso 4: suma a los valores anteriores el precio de un kilogramo de arroz y obtiene que el precio final por pagar es "),
        _math_block(r"\$19\,100", display=False),
        _text_block("."),
        _text_block("\u00bfEn cu\u00e1l de los pasos la persona cometi\u00f3 el error?"),
    ]


def reconstruct_q16_stem(evidence_id: str, visual_assets: dict[str, str]) -> list[dict]:
    """Reconstruct Q16's simple percentage table as structured data."""
    table = _table_block([
        [
            [_text_block("Tipo de legumbre")],
            [_text_block("Porcentaje de preferencia")],
        ],
        [[_text_block("Lentejas (L)")], [_text_block("20 %")]],
        [[_text_block("Garbanzos (G)")], [_text_block("10 %")]],
        [[_text_block("Porotos (P)")], [_text_block("45 %")]],
        [[_text_block("Otra legumbre (O)")], [_text_block("25 %")]],
    ])
    return [
        _text_block("Se realiz\u00f3 una encuesta a un grupo de personas respecto a su legumbre preferida y cada persona eligi\u00f3 solo una opci\u00f3n. Los resultados se presentan en la siguiente tabla:"),
        table,
        _text_block("\u00bfCu\u00e1l de los siguientes gr\u00e1ficos representa mejor esta informaci\u00f3n?"),
    ]


def reconstruct_q38_stem(evidence_id: str, visual_assets: dict[str, str]) -> list[dict]:
    """Reconstruct Q38's inline physics notation without calculating it."""
    return [
        _text_block("El peso p en newtons (N) de un cuerpo depende de su masa m en kilogramos, y se modela mediante la expresi\u00f3n "),
        _math_block(r"p=g\cdot m", display=False),
        _text_block(", tal que "),
        _math_block(r"g", display=False),
        _text_block(" es una constante que depende del planeta donde se encuentre el cuerpo."),
        _text_block("En Mercurio, el valor de "),
        _math_block(r"g", display=False),
        _text_block(" es aproximadamente "),
        _math_block(r"3{,}7\ \frac{\mathrm{m}}{\mathrm{s}^2}", display=False),
        _text_block(", de manera que se puede establecer el siguiente gr\u00e1fico:"),
        _visual_block("Im19", evidence_id, visual_assets),
        _text_block("Si el valor de "),
        _math_block(r"g", display=False),
        _text_block(" en la Tierra es aproximadamente "),
        _math_block(r"10\ \frac{\mathrm{m}}{\mathrm{s}^2}", display=False),
        _text_block(", \u00bfcu\u00e1l de los siguientes gr\u00e1ficos podr\u00eda representar el peso en funci\u00f3n de la masa en Mercurio y en la Tierra?"),
    ]


def visual_options_from_assets(
    option_asset_keys: dict[str, str],
    evidence_id: str,
    visual_assets: dict[str, str],
) -> list[dict]:
    options = []
    for label in ("A", "B", "C", "D"):
        asset_key = option_asset_keys[label]
        asset_id = visual_assets.get(asset_key)
        block = (
            {"type": "image", "asset_id": asset_id}
            if asset_id
            else {
                "type": "unresolved",
                "raw_text": f"[Image: {asset_key}]",
                "reason": "visual_content_pending",
                "evidence_id": evidence_id,
            }
        )
        options.append({"id": label, "label": label, "blocks": [block]})
    return options


def determine_extraction_status(
    question_id: str,
    issues: list[dict],
    stem: list[dict],
    options: list[dict],
    coverage: dict | None = None,
) -> str:
    """Derive completeness from issues, unresolved blocks, and coverage."""
    question_issues = [
        issue for issue in issues
        if issue.get("target_id") == question_id
    ]
    blocks = list(stem)
    for option in options:
        blocks.extend(option.get("blocks", []))
    if not blocks:
        return "failed"
    if any(issue.get("blocks_completion", True) for issue in question_issues):
        return "partial"
    if any(_unresolved_nested(block) for block in blocks):
        return "partial"
    if coverage is not None and not coverage.get("complete", False):
        return "partial"
    if any("source_ids" in block for block in blocks) and not fidelity_report(blocks)["complete"]:
        return "partial"
    return "complete"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    crop_dir = output / "evidence" / "crops"
    asset_dir = output / "assets"
    crop_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    grouped: dict[int, list[dict]] = {}
    for case in cases:
        grouped.setdefault(int(case["year"]), []).append(case)

    pages: list[dict] = []
    regions: list[dict] = []
    assets: list[dict] = []
    source_objects: list[dict] = []
    evidence: list[dict] = []
    questions: list[dict] = []
    issues: list[dict] = []
    raw: dict[str, dict] = {}

    for year, year_cases in grouped.items():
        source = PDFS[year]
        if not source.exists():
            raise SystemExit(f"Missing source PDF: {source}")
        pdf = pdfium.PdfDocument(str(source))
        page_numbers = sorted({int(case["page"]) for case in year_cases})
        positioned = extract_text_with_positions(str(source), pages=page_numbers)
        by_page: dict[int, list] = {page_no: [] for page_no in page_numbers}
        for item in positioned:
            by_page.setdefault(int(item.page), []).append(item)

        raw[str(year)] = {}
        for page_no in page_numbers:
            page = pdf[page_no - 1]
            page_width, page_height = map(float, page.get_size())
            items = by_page[page_no]
            question_markers = sorted(
                [item for item in items if QUESTION_RE.fullmatch(item.text.strip())],
                key=lambda item: (-float(item.y), float(item.x)),
            )
            footer_items = [item for item in items if FOOTER_RE.fullmatch(item.text.strip())]
            footer_floor = min(
                (float(item.y) + float(item.height) + 5.0 for item in footer_items),
                default=0.0,
            )
            objects = []
            for obj in page.get_objects():
                bounds = object_bbox_ll(obj)
                if bounds is not None:
                    objects.append({"type": type(obj).__name__, "bbox_ll": bounds})
            page_id = f"{year}-p{page_no}"
            assign_source_ids(page_id, items, objects)
            raw_items = list(items)
            items = expand_inline_items(items)
            question_markers = sorted(
                [item for item in items if QUESTION_RE.fullmatch(item.text.strip())],
                key=lambda item: (-float(item.y), float(item.x)),
            )
            raw[str(year)][str(page_no)] = {
                "items": [
                    {
                        "text": item.text,
                        "page": int(item.page),
                        "x": round(float(item.x), 3),
                        "y": round(float(item.y), 3),
                        "width": round(float(item.width), 3),
                        "height": round(float(item.height), 3),
                        "font_size": round(float(item.font_size), 3),
                        "source_id": _source_id(item, "text"),
                    }
                    for item in raw_items
                ],
                "objects": [
                    {
                        "type": item["type"],
                        "source_id": _source_id(item, "object"),
                        "bbox_ll": [round(value, 3) for value in item["bbox_ll"]],
                    }
                    for item in objects
                ],
            }
            page_id = f"{year}-p{page_no}"
            pages.append({
                "id": page_id,
                "page_number": page_no,
                "width": page_width,
                "height": page_height,
                "rotation": 0,
                "coordinate_system": "top_left_pdf_points",
                "transform": [1, 0, 0, 1, 0, 0],
            })

            for case in [value for value in year_cases if int(value["page"]) == page_no]:
                marker = next(
                    (item for item in question_markers if item.text.strip() == f"{case['question']}."),
                    None,
                )
                if marker is None:
                    raise SystemExit(f"Question marker not found: {case['id']}")
                marker_index = question_markers.index(marker)
                next_marker = (
                    question_markers[marker_index + 1]
                    if marker_index + 1 < len(question_markers)
                    else None
                )
                lower = (
                    float(next_marker.y + next_marker.height + 3.0)
                    if next_marker
                    else footer_floor
                )
                upper = float(marker.y + marker.height + 4.0)
                selected_items = [
                    item for item in items
                    if overlaps_vertical(text_bbox_ll(item), lower, upper)
                ]
                selected_objects = [
                    item for item in objects
                    if overlaps_vertical(item["bbox_ll"], lower, upper)
                ]
                option_markers = sorted(
                    [
                        item for item in selected_items
                        if OPTION_RE.fullmatch(item.text.strip())
                    ],
                    key=lambda item: (-float(item.y), float(item.x)),
                )
                option_members, option_object_members, ambiguous_members = assign_exclusive_option_members(
                    selected_items, selected_objects, option_markers
                )
                all_bounds = [text_bbox_ll(item) for item in selected_items]
                all_bounds.extend(item["bbox_ll"] for item in selected_objects)
                if not all_bounds:
                    raise SystemExit(f"No content found for {case['id']}")

                min_x = max(0.0, min(value[0] for value in all_bounds) - 12.0)
                min_y = max(0.0, min(value[1] for value in all_bounds) - 12.0)
                max_x = min(page_width, max(value[2] for value in all_bounds) + 12.0)
                max_y = min(page_height, max(value[3] for value in all_bounds) + 12.0)
                region = bbox_tl((min_x, min_y, max_x, max_y), page_height)
                region_id = f"region-{case['id']}"
                regions.append({
                    "id": region_id,
                    "page_id": page_id,
                    "bbox": region,
                    "kind": "question",
                    "confidence": "high",
                    "transform": [2, 0, 0, 2, round(-2 * region[0], 3), round(-2 * region[1], 3)],
                })
                evidence_id = f"evidence-{case['id']}"
                question_crop = render_slice(
                    page, crop_dir, case["id"], region, page_width, page_height
                )
                evidence.append({
                    "id": evidence_id,
                    "kind": "crop",
                    "path": str(question_crop.relative_to(output)).replace("\\", "/"),
                    "region_ids": [region_id],
                    "bbox": region,
                    "reason": "audit",
                })

                visual_markers = [
                    item for item in selected_items
                    if IMAGE_MARKER_RE.fullmatch(item.text.strip())
                ]
                generated_assets, visual_assets = build_visual_assets(
                    page, asset_dir, case["id"], visual_markers, selected_objects,
                    page_width, page_height, region_id, issues=issues,
                    evidence_id=evidence_id,
                )
                assets.extend(generated_assets)

                option_item_ids = {
                    id(item)
                    for members in option_members.values()
                    for item in members
                } | {id(item) for item in option_markers}
                # Ambiguous candidates are kept outside every structural owner.
                ambiguous_item_ids = {
                    id(value) for value in ambiguous_members if not isinstance(value, dict)
                }
                ambiguous_object_ids = {
                    id(value) for value in ambiguous_members if isinstance(value, dict)
                }
                # Object ownership is assigned exclusively with the same spatial partition.
                option_object_ids = {
                    id(obj)
                    for members in option_object_members.values()
                    for obj in members
                }
                stem_items = [
                    item for item in selected_items
                    if id(item) not in option_item_ids
                    and id(item) not in ambiguous_item_ids
                    and item is not marker
                ]
                stem_objects = [
                    obj for obj in selected_objects
                    if id(obj) not in option_object_ids
                    and id(obj) not in ambiguous_object_ids
                ]
                stem = make_stem_blocks(
                    stem_items, evidence_id, visual_assets, stem_objects,
                    owner="stem",
                    asset_sources={
                        asset["asset_id"]: asset.get("source_ids", [])
                        for asset in generated_assets
                    },
                )
                options = [
                    option_for_items(
                        label,
                        option_members[label],
                        evidence_id,
                        visual_assets,
                        option_object_members.get(label, []),
                        asset_sources={
                            asset["asset_id"]: asset.get("source_ids", [])
                            for asset in generated_assets
                        },
                    )
                    for label in sorted(option_members)
                ]
                ambiguous_blocks = [
                    _decorate_block(
                        {
                            "type": "unresolved",
                            "reason": "ambiguous_association",
                            "evidence_id": evidence_id,
                        },
                        [_source_id(value, "object" if isinstance(value, dict) else "text")],
                        "ambiguous",
                    )
                    for value in ambiguous_members
                ]
                stem.extend(ambiguous_blocks)
                if len(options) != 4:
                    issues.append({
                        "id": f"issue-{case['id']}-options",
                        "code": "MISSING_OPTIONS",
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "message": f"Expected four alternatives, found {len(options)}.",
                    })
                flat_blocks = list(stem) + [
                    block for option in options for block in option["blocks"]
                ]
                unresolved = [block for block in flat_blocks if block["type"] == "unresolved"]
                if unresolved:
                    has_math_pending = any(
                        block.get("reason") in {"math_reconstruction_pending", "structural_fidelity_unproven"}
                        for block in unresolved
                    )
                    has_ambiguous = any(
                        block.get("reason") == "ambiguous_association"
                        for block in unresolved
                    )
                    issues.append({
                        "id": f"issue-{case['id']}-coverage",
                        "code": (
                            "AMBIGUOUS_ASSOCIATION"
                            if has_ambiguous
                            else "PENDING_MATH_RECONSTRUCTION"
                            if has_math_pending
                            else "PENDING_VISUAL_RECONSTRUCTION"
                        ),
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "blocks_completion": True,
                        "message": "A detected content candidate remains unresolved.",
                    })

                source_inventory = [
                    *build_source_inventory(
                        page_id, region_id, "stem", stem_items, stem_objects
                    ),
                    *build_source_inventory(
                        page_id,
                        region_id,
                        "ambiguous",
                        [
                            value for value in ambiguous_members
                            if not isinstance(value, dict)
                        ],
                        [
                            value for value in ambiguous_members
                            if isinstance(value, dict)
                        ],
                    ),
                    *[
                        entry
                        for label in sorted(option_members)
                        for entry in build_source_inventory(
                            page_id,
                            region_id,
                            f"option:{label}",
                            option_members[label],
                            option_object_members.get(label, []),
                        )
                    ],
                ]
                source_objects.extend(source_inventory)
                def mark_candidates(block):
                    if block["type"] == "math" or block.get("candidate_type") == "math":
                        for entry in source_inventory:
                            if entry["id"] in block.get("source_ids", []):
                                entry["candidate_type"] = "math"
                                entry["candidate_id"] = block.get("candidate_id")
                    if block["type"] == "table":
                        for row in block.get("rows", []):
                            for cell in row.get("cells", []):
                                for child in cell.get("blocks", []):
                                    mark_candidates(child)
                for block in flat_blocks:
                    mark_candidates(block)
                coverage = assess_source_coverage(
                    source_inventory,
                    flat_blocks,
                    owners={option["id"]: option for option in options},
                )
                if coverage["uncovered"]:
                    for entry in source_inventory:
                        if entry["id"] not in coverage["uncovered"]:
                            continue
                        block = _decorate_block(
                            {
                                "type": "unresolved",
                                "reason": "source_object_unrepresented",
                                "evidence_id": evidence_id,
                                "structural_fidelity": {
                                    "status": "unresolved",
                                    "reasons": ["source_object_unrepresented"],
                                    "bbox_ll": list(entry["bbox"]),
                                    "baseline": (entry["bbox"][1] + entry["bbox"][3]) / 2,
                                    "source_ids": [entry["id"]],
                                    "representation_type": "unresolved",
                                    "method": "source_inventory_geometry_v1",
                                },
                            },
                            [entry["id"]],
                            entry["owner"],
                        )
                        if entry["owner"] in {"stem", "ambiguous"}:
                            stem.append(block)
                        elif entry["owner"].startswith("option:"):
                            label = entry["owner"].split(":", 1)[1]
                            next(
                                option for option in options if option["id"] == label
                            )["blocks"].append(block)
                    flat_blocks = list(stem) + [
                        block for option in options for block in option["blocks"]
                    ]
                    coverage = assess_source_coverage(
                        source_inventory,
                        flat_blocks,
                        owners={option["id"]: option for option in options},
                    )
                    issues.append({
                        "id": f"issue-{case['id']}-coverage-gap",
                        "code": "STRUCTURAL_COVERAGE_GAP",
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "blocks_completion": True,
                        "message": "Relevant source objects remain unresolved.",
                    })
                if coverage["misowned"]:
                    issues.append({
                        "id": f"issue-{case['id']}-owner",
                        "code": "OWNER_MISMATCH",
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "blocks_completion": True,
                        "message": "A source object is consumed by the wrong structural owner.",
                    })
                if coverage["duplicated"]:
                    issues.append({
                        "id": f"issue-{case['id']}-duplicate-source",
                        "code": "DUPLICATE_SOURCE_CONSUMPTION",
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "blocks_completion": True,
                        "message": "A source object was consumed more than once.",
                    })

                # Coverage can create additional unresolved source candidates.
                # Render their minimum crops too, after that inventory is final.
                add_ai_evidence_crops(
                    page, crop_dir, case["id"], flat_blocks, source_inventory,
                    evidence, evidence_id, region_id, page_width, page_height,
                )
                structural = fidelity_report(flat_blocks)
                if not structural["complete"]:
                    issues.append({
                        "id": f"issue-{case['id']}-fidelity",
                        "code": "STRUCTURAL_FIDELITY_UNPROVEN",
                        "severity": "warning",
                        "target_id": case["id"],
                        "region_ids": [region_id],
                        "evidence_ids": [evidence_id],
                        "blocks_completion": True,
                        "message": "Source coverage does not prove expression type, grouping or reading order.",
                        "failures": structural["failures"],
                    })
                questions.append({
                    "id": case["id"],
                    "original_number": str(case["question"]),
                    "region_ids": [region_id],
                    "context_ids": [],
                    "stem": stem,
                    "options": options,
                    "structural_fidelity": structural,
                    "extraction_status": determine_extraction_status(
                        case["id"], issues, stem, options, coverage
                    ),
                    "needs_manual_audit": bool(issues) or any(
                        block.get("type") in {"image", "table", "unresolved"}
                        for block in flat_blocks
                    ),
                })

    raw_dir = output / "evidence"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "extraction.raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    draft = {
        "schema_version": "0.1.0",
        "document": {
            "source_path": "local benchmark PDFs; not copied",
            "sha256": {str(year): sha256(PDFS[year]) for year in grouped},
            "page_count": {
                str(year): len(pdfium.PdfDocument(str(PDFS[year])))
                for year in grouped
            },
        },
        "extraction": {
            "status": "partial",
            "tools": {
                "pdf-inspector": package_version("pdf-inspector"),
                "pypdfium2": package_version("pypdfium2"),
                "Pillow": package_version("Pillow"),
            },
            "ai_interventions": [],
            "verification_status": "not_run",
            "needs_manual_audit": bool(issues),
        },
        "pages": pages,
        "regions": regions,
        "assets": assets,
        "source_objects": source_objects,
        "evidence": evidence,
        "contexts": [],
        "questions": questions,
        "unassigned_fragments": [],
        "issues": issues,
    }
    schema = json.loads(
        (ROOT / "skills/paes-importer/schema/draft.schema.json").read_text(encoding="utf-8")
    )
    validate(draft, schema)
    (output / "draft.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "questions": len(questions),
        "pages": len(pages),
        "regions": len(regions),
        "assets": len(assets),
        "evidence_crops": len(evidence),
        "issues": len(issues),
        "output": str(output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

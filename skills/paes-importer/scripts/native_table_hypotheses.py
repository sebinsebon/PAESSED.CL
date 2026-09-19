#!/usr/bin/env python3
"""Create auditable native table hypotheses without changing draft.json.

The adapter deliberately stops before typed-table reconstruction.  It records
what pdf-inspector saw and joins only source objects that can be matched inside
the question region.  Unmatched or reused source ids remain ambiguous.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pdf_inspector


TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bbox(values: Sequence[float] | None) -> tuple[float, float, float, float] | None:
    if values is None or len(values) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(value) for value in values)
    except (TypeError, ValueError):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _round_bbox(values: Sequence[float] | None) -> list[float] | None:
    bounds = _bbox(values)
    return [round(value, 3) for value in bounds] if bounds else None


def _union(boxes: Iterable[Sequence[float]]) -> tuple[float, float, float, float] | None:
    valid = [_bbox(box) for box in boxes]
    valid = [box for box in valid if box is not None]
    if not valid:
        return None
    return (
        min(box[0] for box in valid),
        min(box[1] for box in valid),
        max(box[2] for box in valid),
        max(box[3] for box in valid),
    )


def _contains(outer: Sequence[float], inner: Sequence[float], tolerance: float = 0.0) -> bool:
    outer_box = _bbox(outer)
    inner_box = _bbox(inner)
    if outer_box is None or inner_box is None:
        return False
    return (
        inner_box[0] >= outer_box[0] - tolerance
        and inner_box[1] >= outer_box[1] - tolerance
        and inner_box[2] <= outer_box[2] + tolerance
        and inner_box[3] <= outer_box[3] + tolerance
    )


def _intersects(left: Sequence[float], right: Sequence[float]) -> bool:
    left_box = _bbox(left)
    right_box = _bbox(right)
    if left_box is None or right_box is None:
        return False
    return (
        left_box[0] < right_box[2]
        and right_box[0] < left_box[2]
        and left_box[1] < right_box[3]
        and right_box[1] < left_box[3]
    )


def _expand(bounds: Sequence[float], padding: float) -> list[float]:
    x0, y0, x1, y1 = _bbox(bounds)  # type: ignore[misc]
    return [x0 - padding, y0 - padding, x1 + padding, y1 + padding]


def _normal_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", str(value))
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("\\", "")
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = [cell.strip() for cell in stripped.split("|")]
    return cells if len(cells) >= 2 else None


def _is_separator_row(row: Sequence[str]) -> bool:
    return bool(row) and all(TABLE_SEPARATOR_RE.fullmatch(cell.strip()) for cell in row)


def parse_markdown_tables(markdown: str) -> list[dict]:
    """Return only explicit Markdown grids; never pad missing cells."""
    tables: list[dict] = []
    current: list[list[str]] = []

    def flush() -> None:
        nonlocal current
        if current:
            has_separator = any(_is_separator_row(row) for row in current)
            rows = [row for row in current if not _is_separator_row(row)]
            if has_separator and rows and max(map(len, rows), default=0) >= 2:
                tables.append(
                    {
                        "rows": rows,
                        "columns": max(map(len, rows)),
                        "separator_row_present": True,
                    }
                )
        current = []

    for line in str(markdown or "").splitlines():
        row = _split_markdown_row(line)
        if row is None:
            flush()
        else:
            current.append(row)
    flush()
    return tables


def _source_in_region(entry: Mapping, region_bbox: Sequence[float]) -> bool:
    bbox = _bbox(entry.get("bbox"))
    region = _bbox(region_bbox)
    if bbox is None or region is None:
        return False
    center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    return (
        region[0] <= center[0] <= region[2]
        and region[1] <= center[1] <= region[3]
    )


def _is_table_visual(entry: Mapping) -> bool:
    kind = str(entry.get("kind", ""))
    source_type = str(entry.get("type", ""))
    if source_type not in {"PdfObject", ""} and kind != "layout":
        return False
    bounds = _bbox(entry.get("bbox"))
    if bounds is None:
        return False
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    return (
        (width >= 8.0 and height <= 4.0)
        or (height >= 8.0 and width <= 4.0)
        or (width >= 8.0 and height >= 8.0)
    )


def _table_visual_window(
    visual_entries: Sequence[Mapping], content_bbox: Sequence[float]
) -> list[float] | None:
    """Prefer a demonstrable line grid over a permissive proximity window."""
    content = _bbox(content_bbox)
    if content is None:
        return None
    vertical_x: list[float] = []
    horizontal_y: list[float] = []
    for entry in visual_entries:
        if not _is_table_visual(entry):
            continue
        bounds = _bbox(entry.get("bbox"))
        if bounds is None:
            continue
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        if height >= 8.0 and width <= 4.0:
            vertical_x.append(round((bounds[0] + bounds[2]) / 2, 3))
        if width >= 8.0 and height <= 4.0:
            horizontal_y.append(round((bounds[1] + bounds[3]) / 2, 3))
    vertical_x = sorted(set(vertical_x))
    horizontal_y = sorted(set(horizontal_y))
    left = [value for value in vertical_x if value <= content[0] + 3.0]
    right = [value for value in vertical_x if value >= content[2] - 3.0]
    bottom = [value for value in horizontal_y if value <= content[1] + 3.0]
    top = [value for value in horizontal_y if value >= content[3] - 3.0]
    if left and right and bottom and top:
        return [max(left), max(bottom), min(right), min(top)]
    # Synthetic or partially rendered tables may expose only one border class.
    # Keep the fallback bounded and leave ambiguous objects unresolved.
    return _expand(content_bbox, padding=72.0)


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _source_records(source_ids: Iterable[str], source_entries: Sequence[Mapping]) -> list[dict]:
    by_id = {str(entry.get("id")): entry for entry in source_entries}
    records = []
    for source_id in _unique(source_ids):
        entry = by_id.get(source_id)
        if entry is None:
            continue
        records.append(
            {
                "id": source_id,
                "owner": entry.get("owner"),
                "kind": entry.get("kind"),
                "type": entry.get("type"),
                "bbox_ll": _round_bbox(entry.get("bbox")),
                "text": entry.get("text", ""),
            }
        )
    return records


def _map_table_sources(
    table: Mapping,
    source_entries: Sequence[Mapping],
    region_bbox: Sequence[float],
    consumed_source_ids: set[str],
) -> dict:
    candidates = [
        entry for entry in source_entries
        if entry.get("id") and _source_in_region(entry, region_bbox)
    ]
    text_entries = [
        entry for entry in candidates
        if entry.get("text") and str(entry.get("kind", "text")) in {"text", "text_span"}
    ]
    mapped: list[str] = []
    ambiguous: list[str] = []
    unmapped_cells: list[dict] = []
    observed_empty_cells: list[dict] = []
    matched_counts: dict[str, int] = {}

    for row_index, row in enumerate(table["rows"]):
        for column_index, value in enumerate(row):
            if not value:
                observed_empty_cells.append({"row": row_index, "column": column_index})
                continue
            normalized = _normal_text(value)
            matches = [
                entry for entry in text_entries
                if _normal_text(str(entry.get("text", ""))) == normalized
            ]
            if len(matches) != 1:
                if matches:
                    ambiguous.extend(str(entry["id"]) for entry in matches)
                unmapped_cells.append(
                    {"row": row_index, "column": column_index, "text": value}
                )
                continue
            source_id = str(matches[0]["id"])
            matched_counts[source_id] = matched_counts.get(source_id, 0) + 1

    for source_id, count in matched_counts.items():
        if count > 1 or source_id in consumed_source_ids:
            ambiguous.append(source_id)
        else:
            mapped.append(source_id)

    mapped_text_boxes = [
        entry["bbox"] for entry in text_entries if str(entry.get("id")) in mapped
    ]
    content_bbox = _union(mapped_text_boxes)
    visual_ambiguous: list[str] = []
    if content_bbox is not None:
        visual_entries = [
            entry for entry in candidates
            if not entry.get("text") and _is_table_visual(entry)
        ]
        visual_window = _table_visual_window(visual_entries, content_bbox)
        for entry in candidates:
            source_id = str(entry["id"])
            if source_id in mapped or source_id in ambiguous:
                continue
            if entry.get("text") or not _is_table_visual(entry):
                continue
            entry_bbox = entry.get("bbox")
            if not _intersects(entry_bbox, visual_window):
                continue
            if source_id in consumed_source_ids:
                visual_ambiguous.append(source_id)
            elif _contains(visual_window, entry_bbox, tolerance=1.0):
                mapped.append(source_id)
            else:
                visual_ambiguous.append(source_id)

    mapped = _unique(mapped)
    ambiguous = _unique([*ambiguous, *visual_ambiguous])
    # A source cannot be both mapped and ambiguous.
    ambiguous = [source_id for source_id in ambiguous if source_id not in mapped]
    table_bbox = _union(
        [entry["bbox"] for entry in candidates if str(entry.get("id")) in mapped]
    )
    return {
        "rows": table["rows"],
        "columns": table["columns"],
        "separator_row_present": bool(table.get("separator_row_present")),
        "bbox_ll": _round_bbox(table_bbox),
        "mapped_source_ids": mapped,
        "ambiguous_source_ids": ambiguous,
        "mapped_sources": _source_records(mapped, source_entries),
        "ambiguous_sources": _source_records(ambiguous, source_entries),
        "unmapped_cells": unmapped_cells,
        "observed_empty_cells": observed_empty_cells,
    }


def build_hypothesis(
    *,
    pdf_sha256: str,
    pdf_inspector_version: str,
    page_number: int,
    question_id: str,
    region_id: str | Sequence[str],
    region_bbox_ll: Sequence[float] | None,
    markdown: str,
    source_entries: Sequence[Mapping],
    page_has_table: bool,
    consumed_source_ids: set[str] | None = None,
    elapsed_ms: float | None = None,
) -> dict:
    """Build one sidecar hypothesis without mutating any draft structure."""
    consumed_source_ids = consumed_source_ids if consumed_source_ids is not None else set()
    region_ids = [region_id] if isinstance(region_id, str) else list(region_id)
    hypothesis = {
        "id": f"{question_id}-native-table",
        "detector": "pdf-inspector",
        "pdf_inspector_version": str(pdf_inspector_version),
        "pdf_sha256": str(pdf_sha256),
        "coordinate_system": "pdf_bbox_ll",
        "geometry_source": "pypdfium2_bbox_ll_and_pdf_inspector_positions",
        "page": int(page_number),
        "question_id": str(question_id),
        "region_ids": region_ids,
        "region_bbox_ll": _round_bbox(region_bbox_ll),
        "native_page_has_table": bool(page_has_table),
        "tables": [],
        "mapped_source_ids": [],
        "ambiguous_source_ids": [],
        "mapped_sources": [],
        "ambiguous_sources": [],
        "warnings": [],
        "question_status": "partial",
        "blocks_completion": True,
    }
    if elapsed_ms is not None:
        hypothesis["elapsed_ms"] = round(float(elapsed_ms), 2)
    if region_bbox_ll is None or _bbox(region_bbox_ll) is None:
        hypothesis.update(
            {
                "status": "insufficient_geometry",
                "warnings": ["question region geometry is missing or invalid"],
            }
        )
        return hypothesis

    tables = parse_markdown_tables(markdown)
    if not page_has_table or not tables:
        hypothesis.update(
            {
                "status": "not_detected",
                "warnings": ["pdf-inspector did not expose an explicit table on this page"],
            }
        )
        return hypothesis

    mapped: list[str] = []
    ambiguous: list[str] = []
    table_consumed_source_ids = set(consumed_source_ids)
    for table in tables:
        mapped_table = _map_table_sources(
            table, source_entries, region_bbox_ll, table_consumed_source_ids
        )
        hypothesis["tables"].append(mapped_table)
        mapped.extend(mapped_table["mapped_source_ids"])
        ambiguous.extend(mapped_table["ambiguous_source_ids"])
        table_consumed_source_ids.update(mapped_table["mapped_source_ids"])

    hypothesis["mapped_source_ids"] = _unique(mapped)
    hypothesis["ambiguous_source_ids"] = [
        source_id for source_id in _unique(ambiguous)
        if source_id not in hypothesis["mapped_source_ids"]
    ]
    hypothesis["mapped_sources"] = _source_records(
        hypothesis["mapped_source_ids"], source_entries
    )
    hypothesis["ambiguous_sources"] = _source_records(
        hypothesis["ambiguous_source_ids"], source_entries
    )
    if not hypothesis["mapped_source_ids"]:
        hypothesis["status"] = "out_of_region"
        hypothesis["warnings"].append(
            "native table rows could not be joined to source ids inside the question region"
        )
    elif hypothesis["ambiguous_source_ids"] or any(
        table["unmapped_cells"] for table in hypothesis["tables"]
    ):
        hypothesis["status"] = "candidate_ambiguous"
        hypothesis["warnings"].append(
            "some cells or visual sources remain ambiguous; no source was promoted"
        )
    else:
        hypothesis["status"] = "candidate"
    return hypothesis


def _visual_source(entry: Mapping) -> bool:
    source_type = str(entry.get("type", ""))
    kind = str(entry.get("kind", ""))
    return source_type in {"PdfObject", "PdfImage"} or kind in {"layout", "visual"}


def _native_anchor_entries(
    hypothesis: Mapping, source_entries: Sequence[Mapping]
) -> list[Mapping]:
    values: list[str] = []
    for table in hypothesis.get("tables", []):
        for row in table.get("rows", []):
            values.extend(str(value) for value in row if value)
    exact = {_normal_text(value) for value in values if _normal_text(value)}
    token_values = {
        _normal_text(token)
        for value in values
        for token in re.findall(r"[\wÀ-ÿ]+", str(value), flags=re.UNICODE)
        if _normal_text(token)
    }
    anchors = []
    for entry in source_entries:
        if not entry.get("text") or str(entry.get("kind", "text")) not in {"text", "text_span"}:
            continue
        normalized = _normal_text(str(entry.get("text", "")))
        if normalized in exact or normalized in token_values:
            anchors.append(entry)
    return anchors


def _grid_from_geometry(
    hypothesis: Mapping, source_entries: Sequence[Mapping]
) -> tuple[dict | None, list[str]]:
    region_bbox = hypothesis.get("region_bbox_ll")
    if _bbox(region_bbox) is None:
        return None, ["missing_region_geometry"]
    anchors = _native_anchor_entries(hypothesis, source_entries)
    anchor_bbox = _union(entry.get("bbox", []) for entry in anchors)
    if anchor_bbox is None:
        return None, ["no_text_anchor_geometry"]
    visuals = [
        entry for entry in source_entries
        if _source_in_region(entry, region_bbox) and _visual_source(entry)
    ]
    vertical_x: list[float] = []
    horizontal: list[tuple[float, tuple[float, float]]] = []
    for entry in visuals:
        bounds = _bbox(entry.get("bbox"))
        if bounds is None:
            continue
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        if height >= 8.0 and width <= 4.0:
            vertical_x.append(round((bounds[0] + bounds[2]) / 2, 3))
        if width >= 8.0 and height <= 4.0:
            horizontal.append(
                (round((bounds[1] + bounds[3]) / 2, 3), (bounds[0], bounds[2]))
            )
    vertical_x = sorted(set(vertical_x))
    left = [value for value in vertical_x if value <= anchor_bbox[0] + 24.0]
    right = [value for value in vertical_x if value >= anchor_bbox[2] - 24.0]
    if not left or not right:
        return None, ["insufficient_vertical_grid_geometry"]
    x0, x1 = max(left), min(right)
    x_lines = [value for value in vertical_x if x0 - 1.0 <= value <= x1 + 1.0]
    y_low = anchor_bbox[1] - 60.0
    y_high = anchor_bbox[3] + 8.0
    y_lines = sorted({
        y for y, (line_x0, line_x1) in horizontal
        if y_low <= y <= y_high
        and line_x1 >= x0 + 8.0
        and line_x0 <= x1 - 8.0
    })
    if len(x_lines) < 2:
        return None, ["insufficient_vertical_grid_geometry"]
    if len(y_lines) < 2:
        return None, ["insufficient_horizontal_grid_geometry"]
    return {
        "x_lines": x_lines,
        "y_lines": y_lines,
        "bbox_ll": [x_lines[0], y_lines[0], x_lines[-1], y_lines[-1]],
    }, []


def _geometry_cell(grid: Mapping, entry: Mapping) -> tuple[int, int] | None:
    bounds = _bbox(entry.get("bbox"))
    if bounds is None:
        return None
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    x_lines = list(grid["x_lines"])
    y_lines = list(grid["y_lines"])
    column = next(
        (index for index in range(len(x_lines) - 1)
         if x_lines[index] <= center_x <= x_lines[index + 1]),
        None,
    )
    interval = next(
        (index for index in range(len(y_lines) - 1)
         if y_lines[index] <= center_y <= y_lines[index + 1]),
        None,
    )
    if column is None or interval is None:
        return None
    return len(y_lines) - 2 - interval, column


def _native_cell_matches(
    hypothesis: Mapping,
    geometry_rows: Sequence[Sequence[dict]],
    text_entries: Sequence[Mapping],
) -> tuple[list[dict], list[str]]:
    by_row: dict[int, list[Mapping]] = {}
    for entry in text_entries:
        cell = _geometry_cell(hypothesis["_geometry"], entry)
        if cell is not None:
            by_row.setdefault(cell[0], []).append(entry)
    for row in by_row.values():
        row.sort(key=lambda entry: float(_bbox(entry["bbox"])[0]))
    links: list[dict] = []
    reasons: list[str] = []
    native_tables = hypothesis.get("tables", [])
    if len(native_tables) != 1:
        return links, ["native_table_count_not_exactly_one"]
    native_rows = native_tables[0].get("rows", [])
    for native_row_index, row in enumerate(native_rows):
        for native_column_index, value in enumerate(row):
            if not value:
                continue
            normalized = _normal_text(value)
            candidate_sequences: list[tuple[int, list[Mapping]]] = []
            preferred_rows = [native_row_index]
            if native_row_index > 0:
                preferred_rows.append(native_row_index - 1)
            preferred_rows.append(native_row_index + 1)
            for geometry_row_index in preferred_rows:
                entries = by_row.get(geometry_row_index, [])
                for start in range(len(entries)):
                    combined = ""
                    selected: list[Mapping] = []
                    for end in range(start, min(len(entries), start + 4)):
                        combined += _normal_text(str(entries[end].get("text", "")))
                        selected.append(entries[end])
                        if combined == normalized:
                            candidate_sequences.append((geometry_row_index, list(selected)))
                        if len(combined) >= len(normalized):
                            break
            unique_sequences = {
                (row_index, tuple(str(entry["id"]) for entry in selected))
                for row_index, selected in candidate_sequences
            }
            if len(unique_sequences) != 1:
                reasons.append(
                    "ambiguous_native_cell" if unique_sequences else "unmapped_native_cell"
                )
                continue
            geometry_row_index, source_ids = next(iter(unique_sequences))
            selected = next(
                selected for row_index, selected in candidate_sequences
                if row_index == geometry_row_index
                and tuple(str(entry["id"]) for entry in selected) == source_ids
            )
            links.append(
                {
                    "native_row": native_row_index,
                    "native_column": native_column_index,
                    "text": value,
                    "geometry_row": geometry_row_index,
                    "geometry_columns": [
                        _geometry_cell(hypothesis["_geometry"], entry)[1]
                        for entry in selected
                    ],
                    "source_ids": list(source_ids),
                }
            )
    return links, reasons


def resolve_table_geometry(
    hypothesis: Mapping, source_entries: Sequence[Mapping]
) -> dict:
    """Resolve a native hypothesis against explicit PDF geometry only."""
    result = {
        "eligible": False,
        "reasons": [],
        "mapped_source_ids": [],
        "ambiguous_source_ids": [],
        "unresolved_source_ids": [],
        "rows": [],
        "native_cell_links": [],
        "visual_source_ids": [],
        "grid_bbox_ll": None,
        "x_lines": [],
        "y_lines": [],
    }
    if not hypothesis.get("native_page_has_table") or not hypothesis.get("tables"):
        result["reasons"].append("native_table_not_detected")
        return result
    grid, grid_reasons = _grid_from_geometry(hypothesis, source_entries)
    if grid is None:
        result["reasons"].extend(grid_reasons)
        return result
    working = dict(hypothesis)
    working["_geometry"] = grid
    result.update(
        {
            "grid_bbox_ll": _round_bbox(grid["bbox_ll"]),
            "x_lines": grid["x_lines"],
            "y_lines": grid["y_lines"],
        }
    )
    region_bbox = hypothesis["region_bbox_ll"]
    in_region = [
        entry for entry in source_entries
        if entry.get("id") and _source_in_region(entry, region_bbox)
    ]
    text_entries = [
        entry for entry in in_region
        if entry.get("text") and str(entry.get("kind", "text")) in {"text", "text_span"}
    ]
    geometry_text: list[tuple[Mapping, tuple[int, int]]] = []
    for entry in text_entries:
        cell = _geometry_cell(grid, entry)
        if cell is not None:
            geometry_text.append((entry, cell))
    row_count = len(grid["y_lines"]) - 1
    column_count = len(grid["x_lines"]) - 1
    rows = [
        [
            {"text": "", "source_ids": [], "bbox_ll": None}
            for _ in range(column_count)
        ]
        for _ in range(row_count)
    ]
    duplicate_ids: set[str] = set()
    seen_ids: set[str] = set()
    for entry, (row_index, column_index) in geometry_text:
        source_id = str(entry["id"])
        if source_id in seen_ids:
            duplicate_ids.add(source_id)
            continue
        seen_ids.add(source_id)
        cell = rows[row_index][column_index]
        if cell["text"]:
            cell["text"] += " " + str(entry["text"])
        else:
            cell["text"] = str(entry["text"])
        cell["source_ids"].append(source_id)
        cell["bbox_ll"] = _round_bbox(
            _union([cell["bbox_ll"] or entry["bbox"], entry["bbox"]])
        )
    result["rows"] = rows
    if duplicate_ids:
        result["reasons"].append("duplicate_source_id")
        result["ambiguous_source_ids"].extend(sorted(duplicate_ids))
    links, link_reasons = _native_cell_matches(working, rows, text_entries)
    result["native_cell_links"] = links
    result["reasons"].extend(link_reasons)
    linked_ids = {
        source_id for link in links for source_id in link.get("source_ids", [])
    }
    mapped_text_ids = {source_id for entry, _ in geometry_text for source_id in [str(entry["id"])]}
    if mapped_text_ids - linked_ids:
        result["reasons"].append("unlinked_text_source")
        result["ambiguous_source_ids"].extend(sorted(mapped_text_ids - linked_ids))

    visual_ids: list[str] = []
    for entry in in_region:
        if not _visual_source(entry):
            continue
        entry_bbox = entry.get("bbox")
        if not _intersects(entry_bbox, grid["bbox_ll"]):
            continue
        source_id = str(entry["id"])
        if (
            str(entry.get("type", "")) == "PdfObject"
            and _contains(grid["bbox_ll"], entry_bbox, tolerance=1.0)
        ):
            visual_ids.append(source_id)
        else:
            result["reasons"].append("unconsumed_visual_source")
            result["ambiguous_source_ids"].append(source_id)
    result["visual_source_ids"] = _unique(visual_ids)
    result["mapped_source_ids"] = _unique([*linked_ids, *visual_ids])
    result["ambiguous_source_ids"] = [
        source_id for source_id in _unique(result["ambiguous_source_ids"])
        if source_id not in result["mapped_source_ids"]
    ]
    result["unresolved_source_ids"] = list(result["ambiguous_source_ids"])
    owners = {
        entry.get("owner")
        for entry in in_region
        if str(entry.get("id")) in result["mapped_source_ids"]
    }
    expected_owner = hypothesis.get("owner", "stem")
    if owners != {expected_owner}:
        result["reasons"].append("owner_mismatch")
    if result["ambiguous_source_ids"]:
        result["reasons"].append("ambiguous_source_id")
    result["reasons"] = _unique(result["reasons"])
    result["eligible"] = not result["reasons"]
    return result


def promote_hypothesis(
    hypothesis: Mapping,
    source_entries: Sequence[Mapping],
    *,
    expected_owner: str = "stem",
) -> dict:
    """Return a typed table only when geometry proves every source relation."""
    working = dict(hypothesis)
    working["owner"] = expected_owner
    resolved = resolve_table_geometry(working, source_entries)
    result = {
        "eligible": resolved["eligible"],
        "reasons": list(resolved["reasons"]),
        "resolved": resolved,
        "unresolved_source_ids": list(resolved.get("unresolved_source_ids", [])),
        "block": None,
    }
    if not resolved["eligible"]:
        return result
    rows = []
    for row in resolved["rows"]:
        cells = []
        for cell in row:
            blocks = []
            if cell["text"]:
                blocks.append(
                    {
                        "type": "text",
                        "text": cell["text"],
                        "source_ids": list(cell["source_ids"]),
                        "owner": expected_owner,
                    }
                )
            cells.append({"blocks": blocks})
        rows.append({"cells": cells})
    result["block"] = {
        "type": "table",
        "rows": rows,
        "source_ids": list(resolved["visual_source_ids"]),
        "owner": expected_owner,
        "evidence_id": hypothesis.get("id"),
    }
    return result


def _region_bbox_ll(region: Mapping, page_height: float) -> list[float] | None:
    bbox = _bbox(region.get("bbox"))
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    return [x0, page_height - y1, x1, page_height - y0]


def _build_source_entries(
    question: Mapping,
    draft: Mapping,
    raw_page: Mapping,
) -> list[dict]:
    region_ids = set(question.get("region_ids", []))
    inventory = [
        entry for entry in draft.get("source_objects", [])
        if entry.get("region_id") in region_ids
    ]
    inventory_by_id = {str(entry["id"]): entry for entry in inventory}
    entries: list[dict] = []
    for item in raw_page.get("items", []):
        source_id = str(item.get("source_id", ""))
        if source_id not in inventory_by_id:
            continue
        entries.append(
            {
                **inventory_by_id[source_id],
                "text": item.get("text", ""),
                "bbox": [
                    float(item["x"]),
                    float(item["y"]),
                    float(item["x"]) + float(item["width"]),
                    float(item["y"]) + float(item["height"]),
                ],
            }
        )
    for obj in raw_page.get("objects", []):
        source_id = str(obj.get("source_id", ""))
        if source_id not in inventory_by_id:
            continue
        entries.append(
            {
                **inventory_by_id[source_id],
                "type": obj.get("type", ""),
                "bbox": list(obj.get("bbox_ll", [])),
                "text": "",
            }
        )
    return entries


def _question_region(question: Mapping, draft: Mapping, pages: Mapping[str, Mapping]):
    regions = {
        region["id"]: region
        for region in draft.get("regions", [])
        if region.get("id") in set(question.get("region_ids", []))
    }
    if not regions:
        return None, None, None
    page_ids = {region.get("page_id") for region in regions.values()}
    if len(page_ids) != 1:
        return None, None, "question regions span multiple pages"
    page_id = next(iter(page_ids))
    page = pages.get(page_id)
    if not page:
        return None, None, "question page metadata is missing"
    page_height = float(page["height"])
    boxes = [_region_bbox_ll(region, page_height) for region in regions.values()]
    region_bbox = _union(box for box in boxes if box is not None)
    return page_id, region_bbox, None


def generate_hypotheses(pdf: Path, draft_path: Path, extraction_path: Path) -> dict:
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    raw = json.loads(extraction_path.read_text(encoding="utf-8"))
    source_hash = file_sha256(pdf)
    try:
        inspector_version = package_version("pdf-inspector")
    except Exception:
        inspector_version = "unknown"
    pages = {page["id"]: page for page in draft.get("pages", [])}
    native_by_page: dict[int, dict] = {}
    hypotheses: list[dict] = []
    consumed_source_ids: set[str] = set()

    for question in draft.get("questions", []):
        page_id, region_bbox, region_error = _question_region(question, draft, pages)
        if region_error:
            hypotheses.append(
                build_hypothesis(
                    pdf_sha256=source_hash,
                    pdf_inspector_version=inspector_version,
                    page_number=0,
                    question_id=str(question["id"]),
                    region_id=question.get("region_ids", []),
                    region_bbox_ll=None,
                    markdown="",
                    source_entries=[],
                    page_has_table=False,
                )
            )
            hypotheses[-1]["warnings"].append(region_error)
            continue
        page_number = int(pages[page_id]["page_number"])
        if page_number not in native_by_page:
            started = time.perf_counter()
            try:
                result = pdf_inspector.extract_pages_markdown(
                    str(pdf), pages=[page_number - 1]
                )
                page_result = result.pages[0]
                native_by_page[page_number] = {
                    "markdown": page_result.markdown,
                    "page_has_table": page_number in result.pages_with_tables,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                }
            except Exception as exc:  # pragma: no cover - runtime boundary
                native_by_page[page_number] = {
                    "markdown": "",
                    "page_has_table": False,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        native = native_by_page[page_number]
        year = str(page_id).split("-p", 1)[0]
        source_entries = _build_source_entries(
            question, draft, raw.get(year, {}).get(str(page_number), {})
        )
        hypothesis = build_hypothesis(
            pdf_sha256=source_hash,
            pdf_inspector_version=inspector_version,
            page_number=page_number,
            question_id=str(question["id"]),
            region_id=question.get("region_ids", []),
            region_bbox_ll=region_bbox,
            markdown=native["markdown"],
            source_entries=source_entries,
            page_has_table=native["page_has_table"],
            consumed_source_ids=consumed_source_ids,
            elapsed_ms=native.get("elapsed_ms"),
        )
        if native.get("error"):
            hypothesis["status"] = "native_detection_error"
            hypothesis["warnings"].append(native["error"])
        promotion = promote_hypothesis(
            hypothesis, source_entries, expected_owner="stem"
        )
        hypothesis["promotion"] = {
            "eligible": promotion["eligible"],
            "reasons": promotion["reasons"],
            "resolved": promotion["resolved"],
            "block_preview": promotion["block"],
        }
        consumed_source_ids.update(hypothesis["mapped_source_ids"])
        hypotheses.append(hypothesis)

    return {
        "schema_version": "0.1.0",
        "source_pdf": pdf.name,
        "pdf_sha256": source_hash,
        "detector": "pdf-inspector",
        "pdf_inspector_version": inspector_version,
        "hypotheses": hypotheses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate_hypotheses(
        args.pdf.resolve(), args.draft.resolve(), args.extraction.resolve()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "hypotheses": len(result["hypotheses"]),
                "candidate_tables": sum(
                    bool(hypothesis["tables"]) for hypothesis in result["hypotheses"]
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

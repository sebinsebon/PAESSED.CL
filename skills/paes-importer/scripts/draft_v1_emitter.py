"""Assemble and safely publish v1 metadata around the existing reconstruction."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path

from draft_contract import (
    CompleteQuestionError, DraftContractError, _artifact_path,
    empty_text_rendering_ids, text_rendering_duplicates, validate_v1,
)


SOURCE_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")


def source_key(case: dict) -> str:
    key = case.get("source", case.get("year"))
    if key is None or not SOURCE_KEY.fullmatch(str(key)):
        raise ValueError(f"Invalid case source key: {key!r}")
    return str(key)


def source_paths_from_manifest(path: Path) -> dict[str, Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Source manifest must be a nonempty key-to-path object")
    result = {}
    for key, value in data.items():
        if not SOURCE_KEY.fullmatch(key) or not isinstance(value, str) or not value:
            raise ValueError("Source manifest has an invalid key or path")
        candidate = Path(value)
        result[key] = (candidate if candidate.is_absolute() else path.parent / candidate).absolute()
    return result


def source_records(grouped: dict[str, list[dict]], paths: dict[str, Path],
                   sha256_file) -> list[dict]:
    """Hash only PDFs selected by the frozen cases, never sibling files."""
    from pypdfium2 import PdfDocument

    records = []
    hashes = {}
    for key in grouped:
        if key not in paths:
            raise ValueError(f"No PDF mapped to source key {key!r}")
        path = paths[key]
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".pdf":
            raise ValueError(f"Invalid mapped PDF for {key!r}: {path}")
        digest = sha256_file(path)
        if digest in hashes:
            raise ValueError(f"Same PDF mapped to two source IDs: {hashes[digest]!r}, {key!r}")
        hashes[digest] = key
        with PdfDocument(str(path)) as pdf:
            records.append({"id": key, "sha256": digest,
                            "page_count": len(pdf), "origin": path.name,
                            "local_path": str(path)})
    return records


def _global_status(questions: list[dict]) -> str:
    statuses = [question["extraction_status"] for question in questions]
    if not statuses or all(status == "failed" for status in statuses):
        return "failed"
    return "complete" if all(status == "complete" for status in statuses) else "partial"


def assemble_v1(legacy_shape: dict, *, sources: list[dict],
                selection_sha256: str, artifact_root: Path, sha256_file) -> dict:
    """Change envelope metadata only; retain question reconstruction verbatim."""
    draft = deepcopy(legacy_shape)
    draft.pop("document", None)
    draft["schema_version"] = "1.0.0"
    draft["sources"] = sources
    draft["run"] = {"purpose": "benchmark", "selection_sha256": selection_sha256}
    source_ids = {source["id"] for source in sources}
    for page in draft["pages"]:
        if page.get("source_id") not in source_ids:
            raise DraftContractError(f"Page lacks mapped source: {page.get('id')}")
    object_ids = {entry["id"] for entry in draft["source_objects"]}
    for entry in draft["source_objects"]:
        representations = entry.pop("representation", None)
        if isinstance(representations, list):
            entry.setdefault("extensions", {})["paessed.representation_types"] = representations
        elif representations is not None:
            entry["representation"] = representations
        if entry.get("parent_id") not in object_ids and entry.get("parent_id"):
            entry.setdefault("extensions", {})["paessed.raw_parent_source_id"] = entry.pop("parent_id")
    duplicate_renderings = text_rendering_duplicates(draft["source_objects"])
    empty_renderings = empty_text_rendering_ids(draft["source_objects"], duplicate_renderings)
    for entry in draft["source_objects"]:
        if entry.get("kind") != "text_rendering":
            continue
        extensions = entry.setdefault("extensions", {})
        declared = extensions.get("paessed.duplicate_of")
        status = extensions.get("paessed.provenance_status")
        expected = duplicate_renderings.get(entry["id"])
        if declared is not None and declared != expected:
            raise DraftContractError(f"Invalid text rendering provenance: {entry['id']}")
        if expected:
            if status is not None:
                raise DraftContractError(f"Conflicting text rendering status: {entry['id']}")
            extensions["paessed.duplicate_of"] = expected
        elif entry["id"] in empty_renderings:
            if status not in (None, "empty_geometry"):
                raise DraftContractError(f"Invalid empty text rendering status: {entry['id']}")
            extensions["paessed.provenance_status"] = "empty_geometry"
        else:
            if status == "empty_geometry":
                raise DraftContractError(f"Invalid empty text rendering status: {entry['id']}")
        if not expected:
            extensions.pop("paessed.duplicate_of", None)
        if not extensions:
            entry.pop("extensions", None)
    for entry in draft["evidence"]:
        path = _artifact_path(artifact_root, entry["path"], "evidence", True)
        if not path.is_file():
            raise DraftContractError(f"Missing evidence crop: {entry['path']}")
        entry["sha256"] = sha256_file(path)
    for issue in draft["issues"]:
        issue.setdefault("blocks_completion", True)
    draft["extraction"]["needs_manual_audit"] = (
        draft["extraction"].get("needs_manual_audit", False)
        or bool(draft["issues"])
        or any(q.get("needs_manual_audit", False) for q in draft["questions"])
    )
    questions_by_id = {question["id"]: question for question in draft["questions"]}
    if len(questions_by_id) != len(draft["questions"]):
        raise DraftContractError("Duplicate question IDs")
    for _ in range(len(draft["questions"]) + 1):
        draft["extraction"]["status"] = _global_status(draft["questions"])
        try:
            validate_v1(draft, artifact_root=artifact_root, check_files=True)
            return draft
        except CompleteQuestionError as exc:
            question = questions_by_id[exc.question_id]
            question["extraction_status"] = "partial"
            question["needs_manual_audit"] = True
            draft["extraction"]["needs_manual_audit"] = True
            issue_id = f"issue-{exc.question_id}-v1-completeness"
            if any(issue["id"] == issue_id for issue in draft["issues"]):
                raise DraftContractError(f"Repeated v1 completeness failure: {exc.question_id}") from exc
            region_ids = set(question["region_ids"])
            evidence_ids = [item["id"] for item in draft["evidence"]
                            if region_ids.intersection(item["region_ids"])]
            draft["issues"].append({
                "id": issue_id, "code": "V1_STRUCTURAL_INCOMPLETE",
                "severity": "warning", "target_id": exc.question_id,
                "region_ids": question["region_ids"], "evidence_ids": evidence_ids,
                "blocks_completion": True, "message": exc.reason,
            })
    raise DraftContractError("Unable to settle v1 question statuses")


@contextmanager
def staging_directory(target: Path):
    """Yield a private sibling directory and remove only our own failed stage."""
    target = target.absolute()
    if target.is_symlink():
        raise DraftContractError(f"Linked output directory rejected: {target}")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise FileExistsError(f"Output already contains files: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / f".{target.name}.stage-{uuid.uuid4().hex}"
    stage.mkdir()
    try:
        yield stage
    finally:
        if (stage.exists() and stage.resolve().parent == target.parent.resolve()
                and stage.name.startswith(f".{target.name}.stage-")):
            shutil.rmtree(stage)


def publish_verified(stage: Path, target: Path) -> None:
    """Revalidate then rename; existing nonempty outputs are never replaced."""
    target = target.absolute()
    if target.is_symlink():
        raise DraftContractError(f"Linked output directory rejected: {target}")
    if stage.resolve().parent != target.parent.resolve():
        raise DraftContractError("Stage and output must share a parent directory")
    draft_path = stage / "draft.json"
    if not draft_path.is_file():
        raise DraftContractError("Validated draft.json is missing from stage")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    validate_v1(draft, artifact_root=stage, check_files=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir() or any(target.iterdir()):
            raise FileExistsError(f"Output already contains files: {target}")
        target.rmdir()
    os.rename(stage, target)

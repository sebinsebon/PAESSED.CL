"""Local inventory and guarded lifecycle for private essay PDFs.

All paths in registro.json are relative to the directory containing it. Mutating
commands are simulations unless --apply is supplied. This tool never reads PDF
pages; it only hashes file bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class RegistryError(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"Cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError(f"Expected JSON object: {path}")
    return value


def load(root: Path) -> dict:
    path = root / "registro.json"
    data = read_json(path) if path.exists() else {
        "schema_version": 1, "essays": [], "solutionarios": []
    }
    if data.get("schema_version") != 1:
        raise RegistryError("Unsupported registry schema version")
    essays = data.get("essays")
    support = data.get("solutionarios")
    if not isinstance(essays, list) or not isinstance(support, list):
        raise RegistryError("Malformed registry collections")
    for entry in essays + support:
        if not isinstance(entry, dict):
            raise RegistryError("Malformed registry entry")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
                char not in "0123456789ABCDEF" for char in digest):
            raise RegistryError("Malformed registry SHA-256")
    hashes = [entry.get("sha256") for entry in essays]
    if len(hashes) != len(set(hashes)):
        raise RegistryError("Duplicate essay SHA-256 in registry")
    support_hashes = [entry.get("sha256") for entry in support]
    if len(support_hashes) != len(set(support_hashes)) or set(hashes) & set(support_hashes):
        raise RegistryError("Duplicate SHA-256 across essay and solutionario records")
    return data


def save(root: Path, data: dict) -> None:
    path = root / "registro.json"
    temp = root / f"registro.json.{uuid.uuid4().hex}.tmp"
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.exists():
        backup_registry(root, True)
    try:
        with temp.open("xb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def backup_registry(root: Path, apply: bool) -> dict:
    source = root / "registro.json"
    if not source.is_file() or source.is_symlink():
        raise RegistryError("No regular registro.json to back up")
    load(root)
    digest = sha256(source)
    backups = root / "respaldos"
    if backups.is_symlink():
        raise RegistryError("Linked backup directory rejected")
    target = backups / f"registro-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{uuid.uuid4().hex[:8]}.json"
    if apply:
        backups.mkdir(parents=True, exist_ok=True)
        temp = backups / f".{target.name}.tmp"
        try:
            with source.open("rb") as reader, temp.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
            if sha256(temp) != digest:
                raise RegistryError("Backup hash mismatch; registry retained")
            os.link(temp, target)
            if sha256(target) != digest:
                raise RegistryError("Backup verification failed; registry retained")
        finally:
            temp.unlink(missing_ok=True)
    return {"path": str(target), "sha256": digest, "applied": apply}


@contextmanager
def locked(root: Path):
    lock = root / "registro.json.lock"
    with lock.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RegistryError(f"Registry locked by another process: {lock}") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def within(root: Path, path: Path, directory: str) -> Path:
    base = root / directory
    if not base.is_dir() or base.is_symlink():
        raise RegistryError(f"Missing or linked directory: {base}")
    candidate = path.absolute()
    try:
        relative = candidate.relative_to(base.absolute())
    except ValueError as exc:
        raise RegistryError(f"Path outside {directory}: {candidate}") from exc
    if not relative.parts or ".." in relative.parts or candidate.suffix.lower() != ".pdf":
        raise RegistryError("Expected a PDF inside nuevos/")
    cursor = base
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RegistryError(f"Linked path rejected: {cursor}")
    if not candidate.is_file():
        raise RegistryError(f"Missing PDF: {candidate}")
    return relative


def relative_artifact(root: Path, path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise RegistryError(f"Missing or linked artifact: {path}")
    return os.path.relpath(path.absolute(), root.absolute()).replace("\\", "/")


def essay_for(data: dict, digest: str) -> dict | None:
    return next((entry for entry in data["essays"] if entry["sha256"] == digest), None)


def inventory(root: Path) -> list[dict]:
    data = load(root)
    support_hashes = {item["sha256"] for item in data["solutionarios"]}
    rows = []
    for path in sorted((root / "nuevos").rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        relative = within(root, path, "nuevos")
        digest = sha256(path)
        essay = essay_for(data, digest)
        state = "used_copy" if essay and essay["uses"] else (
            "prepared" if essay else (
                "solutionario" if digest in support_hashes else (
                    "unregistered_solutionario" if "solucionario" in path.name.casefold()
                    else "virgin_candidate"
                )
            )
        )
        rows.append({"path": (Path("nuevos") / relative).as_posix(),
                     "sha256": digest, "status": state})
    return rows


def timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RegistryError(f"Invalid execution timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RegistryError("Execution timestamp must include a UTC offset")
    return value


def preparation(root: Path, pdf: Path, cases: Path, test_type: str,
                origin: str, apply: bool) -> dict:
    relative = within(root, pdf, "nuevos")
    if "solucionario" in pdf.name.casefold():
        raise RegistryError("Solutionarios must be registered separately")
    if not test_type.strip() or not origin.strip():
        raise RegistryError("Test type and origin are required")
    cases_data = read_json(cases)
    selected = cases_data.get("cases")
    if not isinstance(selected, list) or len(selected) != 8:
        raise RegistryError("The frozen selection must contain eight cases")
    ids = [case.get("id") for case in selected if isinstance(case, dict)]
    if len(ids) != 8 or len(set(ids)) != 8 or any(not value for value in ids):
        raise RegistryError("The eight cases need distinct IDs")
    if not cases_data.get("evaluation_criteria"):
        raise RegistryError("Freeze evaluation_criteria with the eight cases")
    digest = sha256(pdf)
    cases_hash = sha256(cases)
    data = load(root)
    if essay_for(data, digest):
        raise RegistryError("PDF hash already registered; it cannot be a virgin holdout")
    if any(item["sha256"] == digest for item in data["solutionarios"]):
        raise RegistryError("PDF is registered as a solutionario")
    plan = {"pdf_sha256": digest, "pdf_location": (Path("nuevos") / relative).as_posix(),
            "cases": relative_artifact(root, cases), "cases_sha256": cases_hash,
            "test_type": test_type, "origin": origin,
            "prepared_at": datetime.now(timezone.utc).isoformat()}
    if apply:
        with locked(root):
            data = load(root)
            if essay_for(data, digest):
                raise RegistryError("PDF hash already registered; it cannot be a virgin holdout")
            if any(item["sha256"] == digest for item in data["solutionarios"]):
                raise RegistryError("PDF is registered as a solutionario")
            data["essays"].append({"id": "sha256:" + digest, "sha256": digest,
                                   "origin": origin, "locations": [plan["pdf_location"]],
                                   "preparation": plan, "uses": []})
            save(root, data)
    return plan


def register_solutionario(root: Path, pdf: Path, possible: list[str],
                         reason: str, apply: bool) -> dict:
    relative = within(root, pdf, "nuevos")
    if not reason.strip():
        raise RegistryError("State why each association is only possible")
    digest = sha256(pdf)
    candidates = [value.upper() for value in possible]
    if any(len(value) != 64 or any(c not in "0123456789ABCDEF" for c in value)
           for value in candidates):
        raise RegistryError("Possible essay IDs must be full SHA-256 values")
    data = load(root)
    if essay_for(data, digest) or any(s["sha256"] == digest for s in data["solutionarios"]):
        raise RegistryError("SHA-256 already registered")
    entry = {"id": "sha256:" + digest, "sha256": digest,
             "location": (Path("nuevos") / relative).as_posix(),
             "origin": None, "possible_essay_sha256": candidates,
             "association_status": "unconfirmed", "association_evidence": reason}
    if apply:
        with locked(root):
            data = load(root)
            if essay_for(data, digest) or any(s["sha256"] == digest for s in data["solutionarios"]):
                raise RegistryError("SHA-256 already registered")
            data["solutionarios"].append(entry)
            save(root, data)
    return entry


def target_path(root: Path, relative: Path) -> Path:
    if not relative.parts or ".." in relative.parts or relative.is_absolute():
        raise RegistryError("Invalid relative destination")
    dest = root / "usados" / relative
    cursor = root / "usados"
    if cursor.is_symlink():
        raise RegistryError(f"Linked destination directory: {cursor}")
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RegistryError(f"Linked destination directory: {cursor}")
    return dest


def destination(root: Path, relative: Path) -> Path:
    dest = target_path(root, relative)
    if dest.exists() or dest.is_symlink():
        raise RegistryError(f"Destination exists; refusing overwrite: {dest}")
    return dest


def move_exact(root: Path, source: Path, relative: Path, digest: str) -> str:
    dest = destination(root, relative)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # The exclusive hard link prevents overwrites even if another process creates
    # the destination after the preflight check. Both paths are on one volume.
    os.link(source, dest)
    if sha256(dest) != digest or sha256(source) != digest:
        dest.unlink()
        raise RegistryError("Hash changed during move; source retained")
    source.unlink()
    return (Path("usados") / relative).as_posix()


def archive_file(source: Path, target: Path, expected_hash: str, apply: bool) -> None:
    if target.exists() or target.is_symlink():
        if not target.is_file() or target.is_symlink() or sha256(target) != expected_hash:
            raise RegistryError(f"Existing baseline differs; refusing overwrite: {target}")
        return
    if not apply:
        return
    temp = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        with source.open("rb") as reader, temp.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        if sha256(temp) != expected_hash:
            raise RegistryError("Artifact changed during baseline archival")
        os.link(temp, target)
        if sha256(target) != expected_hash:
            raise RegistryError("Archived baseline hash mismatch")
    finally:
        temp.unlink(missing_ok=True)


def finalize(root: Path, pdf: Path, cases: Path, results: Path,
             execution: Path, apply: bool) -> dict:
    relative = within(root, pdf, "nuevos")
    result_data = read_json(results)
    execution_data = read_json(execution)
    used_at = timestamp(execution_data.get("started_at", ""))
    if not result_data:
        raise RegistryError("Initial result artifact must not be empty")
    digest = sha256(pdf)
    with locked(root) if apply else _no_lock():
        data = load(root)
        essay = essay_for(data, digest)
        if not essay or essay["uses"]:
            raise RegistryError("PDF is unprepared or has already participated in a test")
        plan = essay.get("preparation")
        if not plan or plan["pdf_location"] != (Path("nuevos") / relative).as_posix():
            raise RegistryError("Prepared PDF path differs from current source")
        if plan["cases_sha256"] != sha256(cases) or plan["pdf_sha256"] != digest:
            raise RegistryError("Frozen selection or PDF changed")
        if datetime.fromisoformat(used_at) < datetime.fromisoformat(plan["prepared_at"]):
            raise RegistryError("Execution predates frozen selection")
        dest = destination(root, relative)
        baseline = root / "baselines" / digest
        if (root / "baselines").is_symlink():
            raise RegistryError("Linked baseline directory rejected")
        if baseline.is_symlink() or (baseline.exists() and not baseline.is_dir()):
            raise RegistryError(f"Invalid baseline archive directory: {baseline}")
        result_ref = relative_artifact(root, results)
        execution_ref = relative_artifact(root, execution)
        event = {"used_at": used_at, "test_type": plan["test_type"],
                 "cases": plan["cases"], "cases_sha256": plan["cases_sha256"],
                 "initial_results": {"path": result_ref, "sha256": sha256(results),
                                     "archive": os.path.relpath(baseline / "results.json", root).replace("\\", "/")},
                 "execution": {"path": execution_ref, "sha256": sha256(execution)}}
        archive_items = ((cases, "cases.json", plan["cases_sha256"]),
                         (results, "results.json", event["initial_results"]["sha256"]),
                         (execution, "execution.json", event["execution"]["sha256"]))
        if apply:
            baseline.mkdir(parents=True, exist_ok=True)
        for source, name, expected in archive_items:
            archive_file(source, baseline / name, expected, apply)
        if apply:
            essay["uses"].append(event)
            essay["move_pending"] = plan["pdf_location"]
            save(root, data)
            location = move_exact(root, pdf, relative, digest)
            essay["locations"] = [location if p == plan["pdf_location"] else p
                                  for p in essay["locations"]]
            essay.pop("move_pending", None)
            save(root, data)
        return {"source": plan["pdf_location"], "destination": str(dest),
                "sha256": digest, "use": event, "applied": apply}


@contextmanager
def _no_lock():
    yield


def relocate_used(root: Path, pdf: Path, apply: bool) -> dict:
    relative = within(root, pdf, "nuevos")
    digest = sha256(pdf)
    with locked(root) if apply else _no_lock():
        data = load(root)
        essay = essay_for(data, digest)
        if not essay or not essay["uses"]:
            raise RegistryError("PDF hash has no recorded use")
        location = (Path("nuevos") / relative).as_posix()
        if essay.get("move_pending"):
            raise RegistryError("Pending movement exists; run recover first")
        dest = destination(root, relative)
        if apply:
            if location not in essay["locations"]:
                essay["locations"].append(location)
            essay["move_pending"] = location
            save(root, data)
            moved = move_exact(root, pdf, relative, digest)
            essay["locations"] = [p for p in essay["locations"] if p != location]
            if moved not in essay["locations"]:
                essay["locations"].append(moved)
            essay.pop("move_pending", None)
            save(root, data)
        return {"source": location, "destination": str(dest),
                "sha256": digest, "applied": apply}


def recover(root: Path, apply: bool) -> list[dict]:
    actions = []
    with locked(root) if apply else _no_lock():
        data = load(root)
        for essay in data["essays"]:
            location = essay.get("move_pending")
            if not location:
                continue
            path = Path(location)
            if path.is_absolute() or not path.parts or path.parts[0] != "nuevos" or ".." in path.parts:
                raise RegistryError(f"Invalid pending source path: {location}")
            relative = Path(*path.parts[1:])
            if not relative.parts or relative.suffix.lower() != ".pdf":
                raise RegistryError(f"Invalid pending PDF path: {location}")
            source = root / path
            dest = target_path(root, relative)
            if source.is_symlink() or dest.is_symlink():
                raise RegistryError("Linked pending source or destination rejected")
            source_exists, dest_exists = source.is_file(), dest.is_file()
            if source_exists:
                within(root, source, "nuevos")
            if source_exists and sha256(source) != essay["sha256"]:
                raise RegistryError(f"Pending source hash mismatch: {source}")
            if dest_exists and sha256(dest) != essay["sha256"]:
                raise RegistryError(f"Pending destination hash mismatch: {dest}")
            if source_exists and dest_exists:
                action = "remove_verified_duplicate"
            elif source_exists:
                action = "move_source"
            elif dest_exists:
                action = "update_registry"
            else:
                raise RegistryError(f"Both pending PDF locations are missing: {location}")
            actions.append({"sha256": essay["sha256"], "source": str(source),
                            "destination": str(dest), "action": action,
                            "applied": apply})
            if apply:
                if action == "move_source":
                    move_exact(root, source, relative, essay["sha256"])
                elif action == "remove_verified_duplicate":
                    source.unlink()
                moved = (Path("usados") / relative).as_posix()
                essay["locations"] = [moved if p == location else p
                                      for p in essay["locations"]]
                if moved not in essay["locations"]:
                    essay["locations"].append(moved)
                essay.pop("move_pending", None)
                save(root, data)
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Ensayos directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    backup = sub.add_parser("backup-registry")
    repair = sub.add_parser("recover")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--pdf", type=Path, required=True)
    prepare.add_argument("--cases", type=Path, required=True)
    prepare.add_argument("--type", required=True)
    prepare.add_argument("--origin", required=True)
    support = sub.add_parser("register-solutionario")
    support.add_argument("--pdf", type=Path, required=True)
    support.add_argument("--possible-sha256", action="append", default=[])
    support.add_argument("--reason", required=True)
    finish = sub.add_parser("finalize")
    finish.add_argument("--pdf", type=Path, required=True)
    finish.add_argument("--cases", type=Path, required=True)
    finish.add_argument("--results", type=Path, required=True)
    finish.add_argument("--execution", type=Path, required=True)
    move = sub.add_parser("move-used")
    move.add_argument("--pdf", type=Path, required=True)
    for command in (backup, repair, prepare, support, finish, move):
        command.add_argument("--apply", action="store_true", help="Apply after preview")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "inventory":
            output = inventory(root)
        elif args.command == "backup-registry":
            output = backup_registry(root, args.apply)
        elif args.command == "recover":
            output = recover(root, args.apply)
        elif args.command == "prepare":
            output = preparation(root, args.pdf, args.cases, args.type,
                                 args.origin, args.apply)
        elif args.command == "register-solutionario":
            output = register_solutionario(root, args.pdf, args.possible_sha256,
                                           args.reason, args.apply)
        elif args.command == "finalize":
            output = finalize(root, args.pdf, args.cases, args.results,
                              args.execution, args.apply)
        else:
            output = relocate_used(root, args.pdf, args.apply)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (RegistryError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

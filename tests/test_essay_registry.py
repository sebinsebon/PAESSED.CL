import errno
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import essay_registry as registry


class EssayRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Ensayos"
        (self.root / "nuevos" / "folder").mkdir(parents=True)
        self.pdf = self.root / "nuevos" / "folder" / "exam.pdf"
        self.pdf.write_bytes(b"synthetic PDF bytes")
        self.cases = self.root / "cases.json"
        self.cases.write_text(json.dumps({
            "cases": [{"id": f"q{i}"} for i in range(1, 9)],
            "evaluation_criteria": {"false_complete": 0, "audit": "all complete"},
        }), encoding="utf-8")
        self.results = self.root / "results.json"
        self.results.write_text('{"complete": 2, "partial": 6}', encoding="utf-8")
        self.execution = self.root / "execution.json"
        future = datetime.now(timezone.utc) + timedelta(seconds=5)
        self.execution.write_text(json.dumps({"started_at": future.isoformat()}),
                                  encoding="utf-8")

    def prepare(self):
        return registry.preparation(self.root, self.pdf, self.cases,
                                    "holdout", "test origin", True)

    def test_inventory_detects_used_hash_and_solutionario_separately(self):
        digest = registry.sha256(self.pdf)
        copy = self.root / "nuevos" / "copy.pdf"
        copy.write_bytes(self.pdf.read_bytes())
        solution = self.root / "nuevos" / "Solucionario.pdf"
        solution.write_bytes(b"different synthetic PDF bytes")
        data = {"schema_version": 1,
                "essays": [{"sha256": digest, "uses": [{"test_type": "holdout"}]}],
                "solutionarios": [{"sha256": registry.sha256(solution)}]}
        registry.save(self.root, data)
        statuses = {row["path"]: row["status"] for row in registry.inventory(self.root)}
        self.assertEqual(statuses["nuevos/copy.pdf"], "used_copy")
        self.assertEqual(statuses["nuevos/folder/exam.pdf"], "used_copy")
        self.assertEqual(statuses["nuevos/Solucionario.pdf"], "solutionario")

    def test_prepare_is_dry_run_by_default_and_freezes_eight_cases(self):
        plan = registry.preparation(self.root, self.pdf, self.cases,
                                    "holdout", "test origin", False)
        self.assertEqual(plan["pdf_sha256"], registry.sha256(self.pdf))
        self.assertFalse((self.root / "registro.json").exists())
        self.prepare()
        self.assertEqual(len(registry.load(self.root)["essays"]), 1)
        self.assertEqual(registry.inventory(self.root)[0]["status"], "prepared")
        with self.assertRaises(registry.RegistryError):
            self.prepare()

    def test_prepare_rejects_missing_criteria_and_wrong_count(self):
        self.cases.write_text(json.dumps({"cases": [{"id": "q1"}]}), encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            self.prepare()
        self.cases.write_text(json.dumps({"cases": [{"id": str(i)} for i in range(8)]}),
                              encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            self.prepare()

    def test_finalize_archives_initial_result_before_move(self):
        self.prepare()
        preview = registry.finalize(self.root, self.pdf, self.cases,
                                    self.results, self.execution, False)
        self.assertFalse(preview["applied"])
        self.assertTrue(self.pdf.exists())
        self.assertFalse((self.root / "usados").exists())
        done = registry.finalize(self.root, self.pdf, self.cases,
                                 self.results, self.execution, True)
        self.assertTrue(done["applied"])
        self.assertFalse(self.pdf.exists())
        moved = self.root / "usados" / "folder" / "exam.pdf"
        self.assertEqual(moved.read_bytes(), b"synthetic PDF bytes")
        essay = registry.load(self.root)["essays"][0]
        archived = self.root / essay["uses"][0]["initial_results"]["archive"]
        self.assertEqual(archived.read_bytes(), self.results.read_bytes())
        self.assertEqual(essay["locations"], ["usados/folder/exam.pdf"])

    def test_changed_frozen_cases_block_finalize(self):
        self.prepare()
        self.cases.write_text(self.cases.read_text(encoding="utf-8") + "\n",
                              encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            registry.finalize(self.root, self.pdf, self.cases,
                              self.results, self.execution, True)
        self.assertTrue(self.pdf.exists())
        self.assertEqual(registry.load(self.root)["essays"][0]["uses"], [])

    def test_destination_collision_blocks_move_without_overwrite(self):
        self.prepare()
        target = self.root / "usados" / "folder" / "exam.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing destination")
        with self.assertRaises(registry.RegistryError):
            registry.finalize(self.root, self.pdf, self.cases,
                              self.results, self.execution, True)
        self.assertEqual(target.read_bytes(), b"existing destination")
        self.assertTrue(self.pdf.exists())
        self.assertFalse((self.root / "baselines").exists())

    def test_registered_used_copy_has_safe_preview_and_relocation(self):
        digest = registry.sha256(self.pdf)
        registry.save(self.root, {"schema_version": 1,
            "essays": [{"id": "sha256:" + digest, "sha256": digest,
                        "origin": None, "locations": ["nuevos/folder/exam.pdf"],
                        "uses": [{"used_at": None, "test_type": "legacy"}]}],
            "solutionarios": []})
        registry.relocate_used(self.root, self.pdf, False)
        self.assertTrue(self.pdf.exists())
        registry.relocate_used(self.root, self.pdf, True)
        self.assertFalse(self.pdf.exists())
        self.assertEqual(registry.load(self.root)["essays"][0]["locations"],
                         ["usados/folder/exam.pdf"])

    def test_unregistered_pdf_cannot_be_moved_as_used(self):
        with self.assertRaises(registry.RegistryError):
            registry.relocate_used(self.root, self.pdf, True)
        self.assertTrue(self.pdf.exists())

    def test_used_hash_blocks_a_renamed_duplicate_even_in_preview(self):
        digest = registry.sha256(self.pdf)
        registry.save(self.root, {"schema_version": 1,
            "essays": [{"id": "sha256:" + digest, "sha256": digest,
                        "origin": None, "locations": [],
                        "uses": [{"used_at": None, "test_type": "legacy"}]}],
            "solutionarios": []})
        renamed = self.root / "nuevos" / "folder" / "different-name.pdf"
        renamed.write_bytes(self.pdf.read_bytes())
        with self.assertRaises(registry.RegistryError):
            registry.preparation(self.root, renamed, self.cases,
                                 "holdout", "test origin", False)

    def test_solutionario_is_separate_and_association_stays_unconfirmed(self):
        solution = self.root / "nuevos" / "Solucionario.pdf"
        solution.write_bytes(b"support bytes")
        possible = registry.sha256(self.pdf)
        preview = registry.register_solutionario(
            self.root, solution, [possible], "filename only", False)
        self.assertEqual(preview["association_status"], "unconfirmed")
        self.assertFalse((self.root / "registro.json").exists())
        registry.register_solutionario(self.root, solution, [possible],
                                       "filename only", True)
        self.assertEqual(len(registry.load(self.root)["solutionarios"]), 1)
        with self.assertRaises(registry.RegistryError):
            registry.preparation(self.root, solution, self.cases,
                                 "holdout", "test origin", True)

    def test_retry_after_interruption_during_baseline_archive(self):
        self.prepare()
        with patch.object(registry, "save", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        self.assertTrue(self.pdf.exists())
        self.assertEqual(registry.load(self.root)["essays"][0]["uses"], [])
        registry.finalize(self.root, self.pdf, self.cases,
                          self.results, self.execution, True)
        self.assertFalse(self.pdf.exists())

    def test_recover_link_created_before_source_removed(self):
        self.prepare()
        def interrupted_link(root, source, relative, digest):
            destination = root / "usados" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(source, destination)
            raise OSError("simulated interruption")
        with patch.object(registry, "move_exact", side_effect=interrupted_link):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        self.assertTrue(self.pdf.exists())
        preview = registry.recover(self.root, False)
        self.assertEqual(preview[0]["action"], "remove_verified_duplicate")
        registry.recover(self.root, True)
        self.assertFalse(self.pdf.exists())
        self.assertFalse(registry.load(self.root)["essays"][0].get("move_pending"))

    def test_recover_before_link_created(self):
        self.prepare()
        with patch.object(registry, "move_exact", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        self.assertTrue(self.pdf.exists())
        self.assertEqual(registry.recover(self.root, False)[0]["action"], "move_source")
        registry.recover(self.root, True)
        self.assertFalse(self.pdf.exists())

    def test_cross_device_link_failure_keeps_source_and_pending_recovery(self):
        self.prepare()
        original = self.pdf.read_bytes()
        original_link = os.link
        def link_with_cross_device_move(source, target):
            if Path(target).is_relative_to(self.root / "usados"):
                raise OSError(errno.EXDEV, "different device")
            return original_link(source, target)
        with patch.object(registry.os, "link", side_effect=link_with_cross_device_move):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertFalse((self.root / "usados" / "folder" / "exam.pdf").exists())
        self.assertEqual(registry.recover(self.root, False)[0]["action"], "move_source")

    def test_recover_rejects_different_destination_bytes(self):
        self.prepare()
        with patch.object(registry, "move_exact", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        dest = self.root / "usados" / "folder" / "exam.pdf"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"unrelated destination")
        with self.assertRaises(registry.RegistryError):
            registry.recover(self.root, True)
        self.assertTrue(self.pdf.exists())
        self.assertEqual(dest.read_bytes(), b"unrelated destination")

    def test_recover_move_completed_before_registry_update(self):
        self.prepare()
        original = registry.save
        with patch.object(registry, "save", wraps=registry.save) as save_mock:
            calls = 0
            def fail_second(root, data):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated interruption")
                return original(root, data)
            save_mock.side_effect = fail_second
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        self.assertFalse(self.pdf.exists())
        registry.recover(self.root, True)
        essay = registry.load(self.root)["essays"][0]
        self.assertEqual(essay["locations"], ["usados/folder/exam.pdf"])

    def test_recover_interrupted_relocation_of_used_copy(self):
        digest = registry.sha256(self.pdf)
        registry.save(self.root, {"schema_version": 1,
            "essays": [{"id": "sha256:" + digest, "sha256": digest,
                        "origin": None, "locations": ["nuevos/folder/exam.pdf"],
                        "uses": [{"used_at": None, "test_type": "legacy"}]}],
            "solutionarios": []})
        original = registry.save
        calls = 0
        def fail_second(root, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated interruption")
            return original(root, data)
        with patch.object(registry, "save", side_effect=fail_second):
            with self.assertRaises(OSError):
                registry.relocate_used(self.root, self.pdf, True)
        self.assertFalse(self.pdf.exists())
        registry.recover(self.root, True)
        self.assertEqual(registry.load(self.root)["essays"][0]["locations"],
                         ["usados/folder/exam.pdf"])

    def test_save_keeps_private_verified_backup_of_prior_registry(self):
        self.prepare()
        original = (self.root / "registro.json").read_bytes()
        data = registry.load(self.root)
        data["note"] = "next version"
        registry.save(self.root, data)
        backups = list((self.root / "respaldos").glob("registro-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_stale_lock_file_does_not_block_after_process_exit(self):
        (self.root / "registro.json.lock").write_bytes(b"0")
        self.prepare()
        self.assertEqual(len(registry.load(self.root)["essays"]), 1)

    def test_live_registry_lock_blocks_concurrent_mutation(self):
        with registry.locked(self.root):
            with self.assertRaises(registry.RegistryError):
                self.prepare()
        self.prepare()

    def test_stale_temporary_registry_file_does_not_block_retry(self):
        (self.root / "registro.json.tmp").write_bytes(b"interrupted old write")
        self.prepare()
        self.assertEqual(len(registry.load(self.root)["essays"]), 1)

    def test_registry_rejects_sha_shared_by_essay_and_solutionario(self):
        digest = registry.sha256(self.pdf)
        (self.root / "registro.json").write_text(json.dumps({
            "schema_version": 1,
            "essays": [{"sha256": digest, "uses": []}],
            "solutionarios": [{"sha256": digest}],
        }), encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            registry.load(self.root)

    def test_registry_rejects_malformed_entries_with_registry_error(self):
        (self.root / "registro.json").write_text(json.dumps({
            "schema_version": 1,
            "essays": [None],
            "solutionarios": [],
        }), encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            registry.load(self.root)

    def test_recover_is_available_through_cli(self):
        self.prepare()
        with patch.object(registry, "move_exact", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                registry.finalize(self.root, self.pdf, self.cases,
                                  self.results, self.execution, True)
        script = Path(registry.__file__)
        preview = subprocess.run(
            [sys.executable, str(script), "--root", str(self.root), "recover"],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(preview.stdout)[0]["action"], "move_source")
        applied = subprocess.run(
            [sys.executable, str(script), "--root", str(self.root), "recover", "--apply"],
            capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(applied.stdout)[0]["applied"])
        self.assertFalse(self.pdf.exists())
        self.assertFalse(registry.load(self.root)["essays"][0].get("move_pending"))


if __name__ == "__main__":
    unittest.main()

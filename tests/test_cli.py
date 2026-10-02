import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
import uuid
from pathlib import Path

from isee import cli


def binding(kind: str) -> dict:
    key = "decision_id" if kind == "intent" else "structure_id"
    value = "ADR-SECURITY-GATE" if kind == "intent" else "STR-PRODUCTION-DEPLOYMENT"
    return {
        key: value,
        "record_id": str(uuid.uuid4()),
        "record_version": 1,
        "record_fingerprint": "sha256:" + ("a" * 64 if kind == "intent" else "b" * 64),
    }


def resolution(intent: dict) -> dict:
    return {
        "schema_version": "adrp-resolution/v1",
        "as_of": "2026-10-02T14:00:00Z",
        "requested_scopes": ["this repository"],
        "active": [
            {
                **intent,
                "title": "Require security gate",
                "path": ".github/decisions/ADR-SECURITY-GATE/v001.json",
            }
        ],
        "excluded": [],
        "warnings": [],
        "errors": [],
        "summary": {"active_records": 1},
    }


def manifest(intent: dict, structure: dict) -> dict:
    return {
        "schema_version": "isee-execution-manifest/v1",
        "manifest_id": str(uuid.uuid4()),
        "compiled_at": "2026-10-02T14:00:00Z",
        "scope": "this repository",
        "intent_bindings": [intent],
        "structure_bindings": [structure],
        "entry_point": {
            "entry_point_id": "repository-development",
            "name": "Repository development",
            "runner": "github-copilot",
            "command": None,
            "element_refs": ["copilot"],
            "required_gates": ["tests"],
        },
        "elements": [],
        "gates": [
            {
                "gate_id": "tests",
                "name": "Tests",
                "mode": "blocking",
                "element_refs": [],
                "policy_refs": [],
            }
        ],
        "evidence_requirements": [
            {
                "requirement_id": "TEST-RESULT",
                "evidence_type": "assessment",
                "subject": "tests",
                "required_results": ["passed"],
                "artifact_roles": ["report"],
                "criteria_refs": ["TEST-01"],
                "gate_refs": ["tests"],
            }
        ],
        "artifacts": [],
        "integrity": {"manifest_fingerprint": "sha256:" + ("c" * 64)},
    }


def evidence(intent: dict, structure: dict) -> dict:
    return {
        "schema_version": "aerp-evidence-record/v1",
        "evidence_id": str(uuid.uuid4()),
        "evidence_type": "assessment",
        "subject": {"name": "tests", "uri": None, "digest": None},
        "claim": {
            "statement": "Tests passed",
            "result": "passed",
            "summary": "All required tests passed.",
            "criteria_refs": ["TEST-01"],
        },
        "producer": {"name": "test", "version": "1", "identity": "ci:test", "invocation_id": None},
        "method": {"name": "tests", "version": "1", "parameters_digest": None},
        "timing": {"observed_at": "2026-10-02T14:05:00Z", "valid_from": None, "valid_until": None},
        "environment": {"name": "ci", "target": "repository", "correlation_ids": {}},
        "decision_bindings": [intent],
        "structure_bindings": [structure],
        "policy_refs": [],
        "control_refs": [],
        "artifacts": [
            {
                "name": "test report",
                "path": "reports/tests.json",
                "media_type": "application/json",
                "digest": "sha256:" + ("d" * 64),
                "role": "report",
            }
        ],
        "relationships": {"derived_from": [], "supersedes": [], "revokes": []},
        "integrity": {"record_fingerprint": None},
    }


class CliTest(unittest.TestCase):
    def invoke(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_and_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, _, stderr = self.invoke(["init", "--repository", str(root)])
            self.assertEqual(code, 0, stderr)
            self.assertTrue((root / ".github/instructions/isee.instructions.md").is_file())

            intent = binding("intent")
            structure = binding("structure")
            resolution_path = root / "resolution.json"
            manifest_path = root / "manifest.json"
            resolution_path.write_text(json.dumps(resolution(intent)), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest(intent, structure)), encoding="utf-8")
            code, stdout, stderr = self.invoke(
                [
                    "project",
                    "--intent-resolution",
                    str(resolution_path),
                    "--manifest",
                    str(manifest_path),
                    "--output-dir",
                    str(root / ".github/isee"),
                    "--instructions",
                    str(root / ".github/instructions/isee.instructions.md"),
                ]
            )
            self.assertEqual(code, 0, stderr)
            projected = json.loads(stdout)
            context = Path(projected["context"]).read_text(encoding="utf-8")
            self.assertIn("Require security gate", context)
            self.assertIn("TEST-RESULT", context)

    def test_evaluate_satisfied_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intent = binding("intent")
            structure = binding("structure")
            manifest_path = root / "manifest.json"
            evidence_path = root / "evidence.json"
            manifest_path.write_text(json.dumps(manifest(intent, structure)), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence(intent, structure)), encoding="utf-8")

            fake = root / "aerp"
            fake.write_text("#!/bin/sh\nprintf '{\"valid\":true,\"kind\":\"record\"}\\n'\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            previous = os.environ.get("ISEE_AERP_COMMAND")
            os.environ["ISEE_AERP_COMMAND"] = str(fake)
            try:
                code, stdout, stderr = self.invoke(
                    [
                        "evaluate",
                        "--manifest",
                        str(manifest_path),
                        "--evidence",
                        str(evidence_path),
                    ]
                )
            finally:
                if previous is None:
                    os.environ.pop("ISEE_AERP_COMMAND", None)
                else:
                    os.environ["ISEE_AERP_COMMAND"] = previous
            self.assertEqual(code, 0, stderr)
            result = json.loads(stdout)
            self.assertTrue(result["valid"])
            self.assertTrue(result["requirements"][0]["satisfied"])

    def test_evaluate_rejects_missing_structure_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intent = binding("intent")
            structure = binding("structure")
            manifest_path = root / "manifest.json"
            evidence_value = evidence(intent, structure)
            evidence_value["structure_bindings"] = []
            evidence_path = root / "evidence.json"
            manifest_path.write_text(json.dumps(manifest(intent, structure)), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence_value), encoding="utf-8")
            fake = root / "aerp"
            fake.write_text("#!/bin/sh\nprintf '{\"valid\":true,\"kind\":\"record\"}\\n'\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            previous = os.environ.get("ISEE_AERP_COMMAND")
            os.environ["ISEE_AERP_COMMAND"] = str(fake)
            try:
                code, stdout, _ = self.invoke(
                    ["evaluate", "--manifest", str(manifest_path), "--evidence", str(evidence_path)]
                )
            finally:
                if previous is None:
                    os.environ.pop("ISEE_AERP_COMMAND", None)
                else:
                    os.environ["ISEE_AERP_COMMAND"] = previous
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(stdout)["valid"])


if __name__ == "__main__":
    unittest.main()

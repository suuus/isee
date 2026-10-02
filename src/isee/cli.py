#!/usr/bin/env python3
"""Project ISEE governance into Copilot and orchestrate agentic flow gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
RESOLUTION_SCHEMA = "adrp-resolution/v1"
MANIFEST_SCHEMA = "isee-execution-manifest/v1"
AERP_RECORD_SCHEMA = "aerp-evidence-record/v1"
AERP_BUNDLE_SCHEMA = "aerp-evidence-bundle/v1"


class IseeError(RuntimeError):
    """Raised when ISEE integration cannot complete safely."""


def fail(condition: bool, message: str) -> None:
    if not condition:
        raise IseeError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IseeError(f"file not found: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IseeError(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    fail(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def command_path(name: str) -> str:
    override = os.environ.get(f"ISEE_{name.upper()}_COMMAND")
    if override:
        return override
    resolved = shutil.which(name)
    if not resolved:
        raise IseeError(f"required command not found: {name}")
    return resolved


def run_json(name: str, arguments: list[str]) -> dict[str, Any]:
    process = subprocess.run(
        [command_path(name), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise IseeError(f"{name} failed ({process.returncode}): {detail}")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise IseeError(f"{name} returned invalid JSON: {exc}") from exc
    fail(isinstance(value, dict), f"{name} must return a JSON object")
    return value


def render_context(resolution: dict[str, Any], manifest: dict[str, Any]) -> str:
    active = resolution.get("active", [])
    gates = manifest.get("gates", [])
    requirements = manifest.get("evidence_requirements", [])
    lines = [
        "# Active ISEE context",
        "",
        "> Generated projection. Canonical ADRP and ASRP records remain authoritative.",
        "",
        f"**Scope:** `{manifest['scope']}`",
        f"**Entry point:** `{manifest['entry_point']['entry_point_id']}`",
        f"**Runner:** `{manifest['entry_point']['runner']}`",
        f"**Manifest fingerprint:** `{manifest['integrity']['manifest_fingerprint']}`",
        "",
        "## Intent",
        "",
    ]
    if not active:
        lines.append("- No active Intent resolved. Do not infer permission.")
    for item in active:
        lines.extend(
            [
                f"- **{item['decision_id']} — {item['title']}**",
                f"  - Version: `{item['record_version']}`",
                f"  - Fingerprint: `{item['record_fingerprint']}`",
                f"  - Canonical path: `{item['path']}`",
            ]
        )
    lines.extend(["", "## Structure", ""])
    for item in manifest["structure_bindings"]:
        lines.append(
            f"- `{item['structure_id']}` v{item['record_version']} — `{item['record_fingerprint']}`"
        )
    lines.extend(["", "## Gates", ""])
    if not gates:
        lines.append("- No gates recorded.")
    for gate in gates:
        lines.append(f"- **{gate['name']}** — `{gate['mode']}`")
    lines.extend(["", "## Required Evidence", ""])
    if not requirements:
        lines.append("- No Evidence requirements recorded.")
    for requirement in requirements:
        results = ", ".join(f"`{item}`" for item in requirement["required_results"])
        lines.append(
            f"- **{requirement['requirement_id']}**: "
            f"{requirement['evidence_type']} for `{requirement['subject']}`; "
            f"accepted result: {results}"
        )
    lines.extend(
        [
            "",
            "## Working rules",
            "",
            "1. Preserve the listed ADRP and ASRP fingerprints in plans, approvals, and traces.",
            "2. Do not weaken blocking gates or ADRP autonomy boundaries.",
            "3. Ask before actions whose resolved autonomy is `ALWAYS_ASK` or `UNRESOLVED`.",
            "4. Never perform an action whose resolved autonomy is `NEVER`.",
            "5. Produce and verify the required AERP Evidence.",
            "6. Keep failed, warning, error, and inconclusive Evidence visible.",
            "7. Route material Evidence or drift back to Intent or Structure review.",
            "",
        ]
    )
    return "\n".join(lines)


def render_instructions(context_path: str, manifest_path: str) -> str:
    return "\n".join(
        [
            "---",
            'applyTo: "**"',
            "---",
            "",
            "# ISEE governance",
            "",
            f"Before planning or making a material change, read `{context_path}` and",
            f"`{manifest_path}`.",
            "",
            "- Follow active ADRP Intent and ASRP Structure.",
            "- Preserve their exact fingerprints in plans and execution metadata.",
            "- Do not bypass blocking gates.",
            "- Do not treat missing governance as permission.",
            "- Produce the required AERP Evidence after execution.",
            "- Never report an unexecuted, failed, error, or inconclusive check as passed.",
            "",
            "If these files are stale, missing, contradictory, or cannot be validated, stop",
            "and request ISEE preflight rather than guessing.",
            "",
        ]
    )


def project(
    resolution: dict[str, Any],
    manifest: dict[str, Any],
    output_dir: Path,
    instructions_path: Path,
) -> dict[str, Any]:
    fail(resolution.get("schema_version") == RESOLUTION_SCHEMA, "unsupported ADRP resolution")
    fail(manifest.get("schema_version") == MANIFEST_SCHEMA, "unsupported execution manifest")
    intent_path = output_dir / "active-intent.json"
    manifest_path = output_dir / "execution-manifest.json"
    context_path = output_dir / "context.md"
    atomic_write_json(intent_path, resolution)
    atomic_write_json(manifest_path, manifest)
    atomic_write_text(context_path, render_context(resolution, manifest))
    context_ref = context_path.as_posix()
    manifest_ref = manifest_path.as_posix()
    atomic_write_text(instructions_path, render_instructions(context_ref, manifest_ref))
    return {
        "active_intent": str(intent_path),
        "execution_manifest": str(manifest_path),
        "context": str(context_path),
        "instructions": str(instructions_path),
    }


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repository).resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths = [
        root / ".github/decisions",
        root / ".github/structures",
        root / ".github/isee",
        root / ".github/instructions",
        root / "evidence",
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    instructions = root / ".github/instructions/isee.instructions.md"
    if not instructions.exists():
        atomic_write_text(
            instructions,
            render_instructions(".github/isee/context.md", ".github/isee/execution-manifest.json"),
        )
    readme = root / ".github/isee/README.md"
    if not readme.exists():
        atomic_write_text(
            readme,
            "# ISEE generated context\n\nRun `isee preflight` to refresh this directory.\n",
        )
    return {"repository": str(root), "created": [str(path) for path in paths], "instructions": str(instructions)}


def command_project(args: argparse.Namespace) -> dict[str, Any]:
    resolution = read_json(Path(args.intent_resolution))
    manifest = read_json(Path(args.manifest))
    return project(
        resolution,
        manifest,
        Path(args.output_dir),
        Path(args.instructions),
    )


def command_preflight(args: argparse.Namespace) -> dict[str, Any]:
    as_of = args.as_of or utc_now()
    run_json("adrp", ["verify-set", *args.decisions])
    resolution = run_json(
        "adrp",
        ["resolve", *args.decisions, "--scope", args.scope, "--as-of", as_of],
    )
    fail(resolution.get("active"), "no active ADRP Intent resolved")
    autonomy = run_json(
        "adrp",
        [
            "autonomy",
            *args.decisions,
            "--scope",
            args.scope,
            "--action",
            args.action,
            "--as-of",
            as_of,
        ],
    )
    manifest_output = Path(args.output_dir) / "execution-manifest.json"
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    run_json(
        "asrp",
        [
            "compile",
            *args.structures,
            "--scope",
            args.scope,
            "--entry-point",
            args.entry_point,
            "--as-of",
            as_of,
            "--output",
            str(manifest_output),
        ],
    )
    manifest = read_json(manifest_output)
    projected = project(
        resolution,
        manifest,
        Path(args.output_dir),
        Path(args.instructions),
    )
    result = {
        "schema_version": "isee-preflight/v1",
        "as_of": as_of,
        "scope": args.scope,
        "action": args.action,
        "autonomy": autonomy,
        "permitted_without_confirmation": autonomy.get("outcome") == "PROCEED",
        "projection": projected,
        "manifest_fingerprint": manifest["integrity"]["manifest_fingerprint"],
    }
    atomic_write_json(Path(args.output_dir) / "preflight.json", result)
    if args.require_proceed:
        fail(result["permitted_without_confirmation"], f"autonomy outcome is {autonomy.get('outcome')}")
    return result


def binding_key(value: dict[str, Any], kind: str) -> tuple[Any, ...]:
    identity = "decision_id" if kind == "intent" else "structure_id"
    return (
        value[identity],
        value["record_id"],
        value["record_version"],
        value["record_fingerprint"],
    )


def command_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(Path(args.manifest))
    fail(manifest.get("schema_version") == MANIFEST_SCHEMA, "unsupported execution manifest")
    evidence = read_json(Path(args.evidence))
    fail(evidence.get("schema_version") in {AERP_RECORD_SCHEMA, AERP_BUNDLE_SCHEMA}, "unsupported AERP evidence")
    run_json("aerp", ["validate", args.evidence])
    records = [evidence] if evidence["schema_version"] == AERP_RECORD_SCHEMA else evidence["records"]

    evidence_intent = {
        binding_key(item, "intent")
        for record in records
        for item in record["decision_bindings"]
    }
    evidence_structure = {
        binding_key(item, "structure")
        for record in records
        for item in record["structure_bindings"]
    }
    expected_intent = {binding_key(item, "intent") for item in manifest["intent_bindings"]}
    expected_structure = {binding_key(item, "structure") for item in manifest["structure_bindings"]}
    missing_intent = sorted(expected_intent - evidence_intent)
    missing_structure = sorted(expected_structure - evidence_structure)

    requirements = []
    for requirement in manifest["evidence_requirements"]:
        matches = []
        for record in records:
            artifact_roles = {item["role"] for item in record["artifacts"]}
            if (
                record["evidence_type"] == requirement["evidence_type"]
                and record["subject"]["name"].casefold() == requirement["subject"].casefold()
                and record["claim"]["result"] in requirement["required_results"]
                and set(requirement["artifact_roles"]) <= artifact_roles
                and set(requirement["criteria_refs"]) <= set(record["claim"]["criteria_refs"])
            ):
                matches.append(record["evidence_id"])
        requirements.append(
            {
                "requirement_id": requirement["requirement_id"],
                "satisfied": bool(matches),
                "matching_evidence_ids": matches,
            }
        )
    valid = not missing_intent and not missing_structure and all(item["satisfied"] for item in requirements)
    return {
        "schema_version": "isee-evaluation/v1",
        "valid": valid,
        "manifest_fingerprint": manifest["integrity"]["manifest_fingerprint"],
        "missing_intent_bindings": [
            {"decision_id": item[0], "record_id": item[1], "record_version": item[2], "record_fingerprint": item[3]}
            for item in missing_intent
        ],
        "missing_structure_bindings": [
            {"structure_id": item[0], "record_id": item[1], "record_version": item[2], "record_fingerprint": item[3]}
            for item in missing_structure
        ],
        "requirements": requirements,
    }


def command_doctor(_: argparse.Namespace) -> dict[str, Any]:
    tools = {}
    for name in ("adrp", "asrp", "aerp"):
        path = command_path(name)
        process = subprocess.run([path, "--version"], text=True, capture_output=True, check=False)
        tools[name] = {
            "path": path,
            "available": process.returncode == 0,
            "version": process.stdout.strip(),
            "error": process.stderr.strip() or None,
        }
    return {"healthy": all(item["available"] for item in tools.values()), "tools": tools}


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="isee", description=__doc__)
    root.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Scaffold ISEE repository directories and Copilot instructions")
    init.add_argument("--repository", default=".")

    project_parser = commands.add_parser("project", help="Project resolved Intent and Structure into Copilot context")
    project_parser.add_argument("--intent-resolution", required=True)
    project_parser.add_argument("--manifest", required=True)
    project_parser.add_argument("--output-dir", default=".github/isee")
    project_parser.add_argument("--instructions", default=".github/instructions/isee.instructions.md")

    preflight = commands.add_parser("preflight", help="Resolve Intent, compile Structure, and generate Copilot context")
    preflight.add_argument("--decisions", action="append", required=True)
    preflight.add_argument("--structures", action="append", required=True)
    preflight.add_argument("--scope", required=True)
    preflight.add_argument("--entry-point", required=True)
    preflight.add_argument("--action", required=True)
    preflight.add_argument("--as-of")
    preflight.add_argument("--output-dir", default=".github/isee")
    preflight.add_argument("--instructions", default=".github/instructions/isee.instructions.md")
    preflight.add_argument("--require-proceed", action="store_true")

    evaluate = commands.add_parser("evaluate", help="Compare AERP Evidence with an ISEE execution manifest")
    evaluate.add_argument("--manifest", required=True)
    evaluate.add_argument("--evidence", required=True)

    commands.add_parser("doctor", help="Check ADRP, ASRP, and AERP availability")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            emit(command_init(args))
        elif args.command == "project":
            emit(command_project(args))
        elif args.command == "preflight":
            emit(command_preflight(args))
        elif args.command == "evaluate":
            result = command_evaluate(args)
            emit(result)
            return 0 if result["valid"] else 1
        elif args.command == "doctor":
            result = command_doctor(args)
            emit(result)
            return 0 if result["healthy"] else 1
        else:
            raise IseeError(f"unsupported command: {args.command}")
    except IseeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

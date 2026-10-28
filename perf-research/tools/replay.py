"""Stage archived experiments with isolated outputs and a pinned function baseline."""

import argparse
import ast
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent
SESSION = RESEARCH / "evidence/session-2026-10-14-15"
EXPERIMENTS = {
    "lookup-decision": ("paired_cpu.py", "Lookup and sampling-decision bundle; seven paired batches."),
    "context-copy": ("context_copy_probe.py", "Rejected one-copy Context experiment."),
    "attributes": ("attribute-audit/compare.py", "Saved attribute/storage baselines versus current editable sources."),
    "memory": ("attribute-audit/memory_compare.py", "Retained tracemalloc memory for sampled span cohorts."),
    "bulk-update": ("attribute-audit/bulk_compare.py", "Rejected nonempty attribute-update candidate."),
    "constructor": ("attribute-audit/ctor_compare.py", "Weak rejected constructor experiment; original short batches."),
    "scalar-tuple": (
        "attribute-audit/cleaner_compare.py",
        "Original tuple-hoisting experiment; requires the pre-hoisting source.",
    ),
    "propagation": ("propagation-audit/extract_compare.py", "Bundled regex, tracestate and getter prototype."),
    "parsers": ("propagation-audit/parser_compare.py", "Rejected manual parser alternatives versus optimized regex."),
    "strip-parser": ("propagation-audit/strip_compare.py", "Rejected native strip parser follow-up."),
    "scope": ("lifecycle-audit/contextmanager_compare.py", "Shared scope generator and inline upper bound."),
    "parent-reuse": (
        "lifecycle-audit/parent_reuse_compare.py",
        "Built-in parent-context reuse with custom sampler controls.",
    ),
    "combined": (
        "lifecycle-audit/combined_compare.py",
        "Combined lifecycle prototype; sampled row is uncounted and unsuitable for claims.",
    ),
    "combined-counted": (
        "lifecycle-audit/counted_compare.py",
        "Combined sampled case with exported-count assertions and queue drain.",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReplayPaths(ast.NodeTransformer):
    def __init__(self, scratch, baseline, pin_head):
        self.scratch = scratch.as_posix()
        self.baseline = baseline
        self.pin_head = pin_head
        self.changed = False

    def visit_Constant(self, node):
        value = node.value
        if value == ".agent":
            self.changed = True
            return ast.copy_location(ast.Constant(self.scratch), node)
        if isinstance(value, str) and value.startswith(".agent/"):
            self.changed = True
            return ast.copy_location(ast.Constant(self.scratch + "/" + value[len(".agent/") :]), node)
        if self.pin_head and value == "HEAD:":
            self.changed = True
            return ast.copy_location(ast.Constant(self.baseline + ":"), node)
        return node


def stage(destination, manifest):
    """Copy Python artifacts only; leave immutable raw results in the archive."""
    scratch = destination / ".agent"
    records = []
    for record in manifest["artifacts"]:
        source = RESEARCH / record["path"]
        if digest(source) != record["sha256"]:
            raise ValueError(f"Archive hash mismatch: {source}")
        if source.suffix != ".py":
            continue
        relative = Path(record["original_path"]).relative_to(".agent")
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        transform = ReplayPaths(scratch, manifest["head"], relative.as_posix() == "paired_cpu.py")
        tree = transform.visit(ast.parse(source.read_text(encoding="utf-8"), filename=str(source)))
        if transform.changed:
            target.write_text(ast.unparse(ast.fix_missing_locations(tree)) + "\n", encoding="utf-8")
        else:
            target.write_bytes(source.read_bytes())
        records.append(
            {
                "archive": record["path"],
                "archive_sha256": record["sha256"],
                "staged": target.relative_to(destination).as_posix(),
                "staged_sha256": digest(target),
                "rewritten": transform.changed,
            }
        )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List available archived experiments.")
    run = commands.add_parser("run", help="Stage and run an experiment against current editable sources.")
    run.add_argument(
        "--prepare-only", action="store_true", help="Stage and verify artifacts without running a benchmark."
    )
    run.add_argument("experiment", choices=EXPERIMENTS)
    run.add_argument("arguments", nargs=argparse.REMAINDER, help="Harness arguments after --.")
    args = parser.parse_args()
    if args.command == "list":
        for name, (_, description) in EXPERIMENTS.items():
            print(f"{name:20} {description}")
        return
    manifest = json.loads((SESSION / "manifest.json").read_text(encoding="utf-8"))
    name, _ = EXPERIMENTS[args.experiment]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = RESEARCH / ".runs" / f"{stamp}-{args.experiment}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    staged = stage(destination, manifest)
    extra = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    command = [sys.executable, str(destination / ".agent" / name), *extra]
    sources = [
        {"path": item["source"], "sha256": digest(ROOT / item["source"])}
        for item in manifest["working_tree_sources"]
        if (ROOT / item["source"]).is_file()
    ]
    record = {
        "experiment": args.experiment,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "command": command,
        "working_directory": str(ROOT),
        "function_baseline_revision": manifest["head"],
        "archive_manifest_sha256": digest(SESSION / "manifest.json"),
        "current_sources": sources,
        "staged_scripts": staged,
        "status": "prepared",
        "scope": "New measurement against current editable checkout; not a full historical-tree reconstruction.",
    }
    record_path = destination / "run.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Run directory: {destination}", flush=True)
    if args.prepare_only:
        return
    with (destination / "run.log").open("w", encoding="utf-8") as output:
        with subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        ) as process:
            if process.stdout is None:
                raise RuntimeError("Subprocess stdout was not connected.")
            for line in process.stdout:
                output.write(line)
                output.flush()
                print(line, end="", flush=True)
            returncode = process.wait()
    record.update(status="complete" if returncode == 0 else "failed", exit_code=returncode)
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(returncode)


if __name__ == "__main__":
    main()

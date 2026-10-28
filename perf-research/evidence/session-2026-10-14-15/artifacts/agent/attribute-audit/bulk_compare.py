"""Paired audit of the incremental bulk-update path only.

This compares the checked-in adoption-only ``BoundedAttributes._set_items``
with the ignored prototype, keeping the live SDK span/storage implementation
constant. Run from the repository root when the primary timing run is stopped.
"""

import argparse
import gc
import hashlib
import importlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import opentelemetry.attributes as attributes_module
from opentelemetry.sdk.trace import TracerProvider, sampling

_AUDIT_DIR = Path(".agent/attribute-audit")
_REPEATS = 9
_TARGET_SECONDS = 0.6
_WARMUP_LOOPS = 500
_COUNTS = (4, 10, 64)
_SEED_ATTRIBUTES = {"seed-0": "initial-0", "seed-1": "initial-1"}
_CURRENT_SET_ITEMS = attributes_module.BoundedAttributes._set_items


def _load_candidate_set_items():
    prototype_path = _AUDIT_DIR / "bulk-candidate.py"
    prototype_globals = {"__name__": "attribute_audit_bulk_prototype"}
    exec(compile(prototype_path.read_text(encoding="utf-8"), str(prototype_path), "exec"), prototype_globals)  # noqa: S102
    candidate_globals = vars(attributes_module).copy()
    exec(  # noqa: S102
        compile(prototype_globals["SOURCE"], str(prototype_path), "exec"),
        candidate_globals,
    )
    return candidate_globals["_set_items"]


_CANDIDATE_SET_ITEMS = _load_candidate_set_items()


def _pin_cpu():
    if importlib.util.find_spec("psutil") is None:
        return {"psutil_available": False, "affinity_before": None, "affinity_pinned": None}, None, None
    psutil = importlib.import_module("psutil")

    process = psutil.Process()
    try:
        allowed = process.cpu_affinity()
        if not allowed:
            return {"psutil_available": True, "affinity_before": [], "affinity_pinned": None}, process, []
        process.cpu_affinity([allowed[0]])
        return (
            {"psutil_available": True, "affinity_before": allowed, "affinity_pinned": [allowed[0]]},
            process,
            allowed,
        )
    except (AttributeError, OSError, psutil.Error):
        return {"psutil_available": True, "affinity_before": None, "affinity_pinned": None}, process, None


def _restore_affinity(process, allowed) -> None:
    if process is not None and allowed:
        try:
            process.cpu_affinity(allowed)
        except (AttributeError, OSError):
            pass


def _measure(operation, loops: int) -> dict[str, float | int]:
    operation(_WARMUP_LOOPS)
    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        operation(loops)
        wall_seconds = time.perf_counter() - wall_start
        cpu_seconds = time.process_time() - cpu_start
    finally:
        if was_enabled:
            gc.enable()
    return {
        "loops": loops,
        "cpu_seconds": cpu_seconds,
        "wall_seconds": wall_seconds,
        "cpu_ns_per_op": cpu_seconds * 1e9 / loops,
        "wall_ns_per_op": wall_seconds * 1e9 / loops,
    }


def _calibrate(operation, target_seconds: float) -> int:
    pilot_loops = 100
    pilot = _measure(operation, pilot_loops)
    return max(1, round(pilot_loops * target_seconds / pilot["wall_seconds"]))


def _make_operation(tracer, update_attributes: dict[str, str]):
    def operation(loops: int) -> None:
        for _ in range(loops):
            span = tracer.start_span("benchmark", attributes=_SEED_ATTRIBUTES)
            span.set_attributes(update_attributes)
            span.end()

    return operation


def _cases():
    for count in _COUNTS:
        disjoint = {f"update-{index}": f"value-{index}" for index in range(count)}
        overlapping = {"seed-0": "updated-seed"}
        overlapping.update({f"update-{index}": f"value-{index}" for index in range(count - 1)})
        yield {"case": "disjoint", "count": count, "updates": disjoint}
        yield {"case": "overlapping-seed-0", "count": count, "updates": overlapping}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_case(case: dict, tracer, repeats: int, target_seconds: float) -> dict:
    operation = _make_operation(tracer, case["updates"])
    samples = []
    loops = _calibrate(operation, target_seconds)
    for pair in range(repeats):
        order = ("adoption-only", "bulk-candidate") if pair % 2 == 0 else ("bulk-candidate", "adoption-only")
        pair_batches = []
        for mode in order:
            attributes_module.BoundedAttributes._set_items = (
                _CURRENT_SET_ITEMS if mode == "adoption-only" else _CANDIDATE_SET_ITEMS
            )
            pair_batches.append({"mode": mode, **_measure(operation, loops)})
        samples.append({"pair": pair, "order": order, "batches": pair_batches})

    summary = {}
    for mode in ("adoption-only", "bulk-candidate"):
        batches = [batch for pair in samples for batch in pair["batches"] if batch["mode"] == mode]
        total_loops = sum(batch["loops"] for batch in batches)
        summary[mode] = {
            "cpu_ns_per_op_pooled": sum(batch["cpu_seconds"] for batch in batches) * 1e9 / total_loops,
            "wall_ns_per_op_median": statistics.median(batch["wall_ns_per_op"] for batch in batches),
        }
    return {
        "case": case["case"],
        "update_count": case["count"],
        "loops_per_batch": loops,
        "samples": samples,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run one short case with one pair.")
    parser.add_argument(
        "--output",
        type=Path,
        default=_AUDIT_DIR / "paired-bulk-comparison.json",
        help="Path for raw paired samples and summaries.",
    )
    args = parser.parse_args()
    repeats = 1 if args.smoke else _REPEATS
    target_seconds = 0.02 if args.smoke else _TARGET_SECONDS
    cases = list(_cases())
    if args.smoke:
        cases = [next(case for case in cases if case["case"] == "disjoint" and case["count"] == 4)]

    affinity, affinity_process, original_affinity = _pin_cpu()
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("bulk-attribute-audit")
    results = []
    try:
        for case in cases:
            result = _run_case(case, tracer, repeats, target_seconds)
            results.append(result)
            baseline = result["summary"]["adoption-only"]
            candidate = result["summary"]["bulk-candidate"]
            cpu_change = (candidate["cpu_ns_per_op_pooled"] / baseline["cpu_ns_per_op_pooled"] - 1) * 100
            wall_change = (candidate["wall_ns_per_op_median"] / baseline["wall_ns_per_op_median"] - 1) * 100
            print(
                f"{case['case']}/{case['count']}: CPU {cpu_change:+.1f}%, wall {wall_change:+.1f}%",
                flush=True,
            )
    finally:
        attributes_module.BoundedAttributes._set_items = _CURRENT_SET_ITEMS
        provider.shutdown()
        _restore_affinity(affinity_process, original_affinity)

    metadata = {
        "python_version": sys.version,
        "affinity": affinity,
        "harness_sha256": _sha256(Path(__file__)),
        "prototype_sha256": _sha256(_AUDIT_DIR / "bulk-candidate.py"),
        "candidate_attributes_sha256": _sha256(Path("opentelemetry-api/src/opentelemetry/attributes/__init__.py")),
        "sdk_trace_sha256": _sha256(Path("opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py")),
    }
    output = {"metadata": metadata, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Raw paired batches and summaries saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()

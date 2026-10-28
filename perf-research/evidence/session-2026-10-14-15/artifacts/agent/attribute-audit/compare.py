"""Paired CPU and wall audit for span attribute and storage changes.

Run from the repository root after the candidate changes are ready. The script
loads saved pre-change API/SDK modules under unique names and measures four
same-process combinations: baseline, attributes-only, lazy-only, and combined.
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

from opentelemetry.attributes import BoundedAttributes as _CURRENT_BOUNDED_ATTRIBUTES
from opentelemetry.sdk import trace as live_trace
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.util import BoundedList as live_bounded_list
from opentelemetry.trace import SpanContext, TraceFlags

_AUDIT_DIR = Path(".agent/attribute-audit")
_MODES = ("baseline", "attributes-only", "lazy-only", "combined")
_REPEATS = 7
_TARGET_SECONDS = 0.20
_WARMUP_LOOPS = 1_000
_ATTR_COUNTS = (0, 4, 10, 64)
_ATTR_MODES = ("constructor", "set-attribute", "set-attributes")
_LINK_CONTEXT = SpanContext(
    0x123456789ABCDEF0123456789ABCDEF0,
    0x123456789ABCDEF0,
    True,
    TraceFlags(TraceFlags.SAMPLED),
)


def _load_saved_module(name: str, filename: str):
    path = _AUDIT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load saved baseline module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_BASELINE_ATTRIBUTES = _load_saved_module("otel_attribute_audit_attributes_baseline", "attributes-baseline.py")
_BASELINE_UTIL = _load_saved_module("otel_attribute_audit_util_baseline", "util-baseline.py")
_BASELINE_TRACE = _load_saved_module("otel_attribute_audit_trace_baseline", "trace-baseline.py")


def _set_mode(mode: str) -> None:
    baseline_attrs = mode in ("baseline", "lazy-only")
    baseline_lazy = mode in ("baseline", "attributes-only")
    attr_class = _BASELINE_ATTRIBUTES.BoundedAttributes if baseline_attrs else _CURRENT_BOUNDED_ATTRIBUTES
    _BASELINE_TRACE.BoundedAttributes = attr_class
    live_trace.BoundedAttributes = attr_class
    _BASELINE_TRACE.BoundedList = _BASELINE_UTIL.BoundedList if baseline_lazy else live_bounded_list
    live_trace.BoundedList = _BASELINE_UTIL.BoundedList if baseline_lazy else live_bounded_list


def _pin_cpu() -> dict:
    if importlib.util.find_spec("psutil") is None:
        return {"psutil_available": False, "affinity_before": None, "affinity_pinned": None}
    psutil = importlib.import_module("psutil")
    process = psutil.Process()
    try:
        allowed = process.cpu_affinity()
        if not allowed:
            return {"psutil_available": True, "affinity_before": [], "affinity_pinned": None}
        process.cpu_affinity([allowed[0]])
        return {"psutil_available": True, "affinity_before": allowed, "affinity_pinned": [allowed[0]]}
    except (AttributeError, OSError, psutil.Error):
        return {"psutil_available": True, "affinity_before": None, "affinity_pinned": None}


def _measure(operation, loops: int) -> dict[str, float | int]:
    gc.collect()
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        for _ in range(loops):
            operation()
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
    loops = 10_000
    pilot = _measure(operation, loops)
    return max(1, round(loops * target_seconds / pilot["wall_seconds"]))


def _make_operation(tracer, case: dict, attributes: dict[str, str], items: tuple):
    lifecycle = case["lifecycle"]
    attribute_mode = case["attribute_mode"]
    extra = case["extra"]

    def update_attributes(span) -> None:
        if attribute_mode == "set-attribute":
            for key, value in items:
                span.set_attribute(key, value)
        elif attribute_mode == "set-attributes":
            span.set_attributes(attributes)

    if lifecycle == "start-span":

        def operation() -> None:
            span = tracer.start_span(
                "benchmark",
                attributes=attributes if attribute_mode == "constructor" else None,
            )
            update_attributes(span)
            if extra in ("one-event", "one-event-and-link"):
                span.add_event("benchmark-event")
            if extra in ("one-link", "one-event-and-link"):
                span.add_link(_LINK_CONTEXT)
            span.end()

    else:

        def operation() -> None:
            with tracer.start_as_current_span(
                "benchmark",
                attributes=attributes if attribute_mode == "constructor" else None,
            ) as span:
                update_attributes(span)

    return operation


def _check_mode_storage(providers: dict) -> None:
    for mode in _MODES:
        _set_mode(mode)
        span = providers[mode].get_tracer("attribute-audit-preflight").start_span("preflight")
        expected_attributes = (
            _BASELINE_ATTRIBUTES.BoundedAttributes if mode in ("baseline", "lazy-only") else _CURRENT_BOUNDED_ATTRIBUTES
        )
        expected_lazy = mode in ("lazy-only", "combined")
        if type(span._attributes) is not expected_attributes:
            raise RuntimeError(f"{mode} did not select the expected BoundedAttributes class")
        if expected_lazy:
            if span._events is not None or span._links is not None:
                raise RuntimeError(f"{mode} did not select lazy empty event/link storage")
        elif not isinstance(span._events, _BASELINE_UTIL.BoundedList) or not isinstance(
            span._links, _BASELINE_UTIL.BoundedList
        ):
            raise RuntimeError(f"{mode} did not select baseline eager event/link storage")
        span.end()


def _preflight_case() -> None:
    providers = {}
    try:
        for mode, trace_module in (
            ("baseline", _BASELINE_TRACE),
            ("attributes-only", _BASELINE_TRACE),
            ("lazy-only", live_trace),
            ("combined", live_trace),
        ):
            providers[mode] = trace_module.TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
        _check_mode_storage(providers)
    finally:
        _set_mode("combined")
        for provider in providers.values():
            provider.shutdown()


def _run_case(case: dict, repeats: int, target_seconds: float) -> dict:
    attributes = {f"key-{index}": f"value-{index}" for index in range(case["attribute_count"])}
    items = tuple(attributes.items())
    providers = {}
    operations = {}
    try:
        for mode, trace_module in (
            ("baseline", _BASELINE_TRACE),
            ("attributes-only", _BASELINE_TRACE),
            ("lazy-only", live_trace),
            ("combined", live_trace),
        ):
            provider = trace_module.TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
            providers[mode] = provider
            operations[mode] = _make_operation(
                provider.get_tracer("attribute-audit-benchmark"), case, attributes, items
            )

        _check_mode_storage(providers)

        for mode in _MODES:
            _set_mode(mode)
            _measure(operations[mode], _WARMUP_LOOPS)
        _set_mode("combined")
        loops = _calibrate(operations["combined"], target_seconds)

        batches = []
        for pair in range(repeats):
            order = _MODES if pair % 2 == 0 else tuple(reversed(_MODES))
            pair_batches = []
            for mode in order:
                _set_mode(mode)
                pair_batches.append({"mode": mode, **_measure(operations[mode], loops)})
            batches.append({"pair": pair, "order": order, "batches": pair_batches})
    finally:
        _set_mode("combined")
        for provider in providers.values():
            provider.shutdown()

    summary = {}
    for mode in _MODES:
        mode_batches = [batch for pair in batches for batch in pair["batches"] if batch["mode"] == mode]
        total_loops = sum(batch["loops"] for batch in mode_batches)
        summary[mode] = {
            "cpu_ns_per_op_pooled": sum(batch["cpu_seconds"] for batch in mode_batches) * 1e9 / total_loops,
            "wall_ns_per_op_median": statistics.median(batch["wall_ns_per_op"] for batch in mode_batches),
        }
    return {**case, "loops_per_batch": loops, "samples": batches, "summary": summary}


def _cases():
    for lifecycle in ("start-span", "current-span"):
        for attribute_mode in _ATTR_MODES:
            for count in _ATTR_COUNTS:
                yield {
                    "kind": "attributes",
                    "lifecycle": lifecycle,
                    "attribute_mode": attribute_mode,
                    "attribute_count": count,
                    "extra": "empty",
                }
    for extra in ("empty", "one-event", "one-link", "one-event-and-link"):
        yield {
            "kind": "empty-event-link-control",
            "lifecycle": "start-span",
            "attribute_mode": "constructor",
            "attribute_count": 0,
            "extra": extra,
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-filter",
        action="append",
        default=[],
        help="Run only case labels containing this substring; may be repeated.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check baseline/candidate class and storage wiring without timing workloads.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one short sampled attribute case and one event+link storage case.",
    )
    parser.add_argument("--target-seconds", type=float, help="Target seconds for each measured batch.")
    parser.add_argument("--repeats", type=int, help="Number of paired samples per case.")
    parser.add_argument(
        "--output",
        type=Path,
        default=_AUDIT_DIR / "paired-attribute-comparison.json",
        help="Path for raw paired samples and summaries.",
    )
    args = parser.parse_args()
    if args.preflight_only:
        _preflight_case()
        print("preflight passed for all four mode combinations", flush=True)
        return
    cases = list(_cases())
    repeats = args.repeats if args.repeats is not None else _REPEATS
    target_seconds = args.target_seconds if args.target_seconds is not None else _TARGET_SECONDS
    if args.smoke:
        cases = [
            next(
                case
                for case in cases
                if case["kind"] == "attributes"
                and case["lifecycle"] == "current-span"
                and case["attribute_mode"] == "set-attributes"
                and case["attribute_count"] == 4
            ),
            next(case for case in cases if case["extra"] == "one-event-and-link"),
        ]
        if args.repeats is None:
            repeats = 1
        if args.target_seconds is None:
            target_seconds = 0.02
    affinity = _pin_cpu()
    metadata = {
        "python_version": sys.version,
        "affinity": affinity,
        "harness_sha256": _sha256(Path(__file__)),
        "baseline_sha256": {
            name: _sha256(_AUDIT_DIR / filename)
            for name, filename in (
                ("attributes", "attributes-baseline.py"),
                ("trace", "trace-baseline.py"),
                ("util", "util-baseline.py"),
            )
        },
        "candidate_sha256": {
            "attributes": _sha256(Path("opentelemetry-api/src/opentelemetry/attributes/__init__.py")),
            "trace": _sha256(Path("opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py")),
            "util": _sha256(Path("opentelemetry-sdk/src/opentelemetry/sdk/util/__init__.py")),
        },
    }
    results = []
    for case in cases:
        case_label = (
            f"{case['kind']}/{case['lifecycle']}/{case['attribute_mode']}/{case['attribute_count']}/{case['extra']}"
        )
        if args.case_filter and not any(fragment in case_label for fragment in args.case_filter):
            continue
        result = _run_case(case, repeats, target_seconds)
        results.append(result)
        baseline = result["summary"]["baseline"]
        combined = result["summary"]["combined"]
        cpu_change = (combined["cpu_ns_per_op_pooled"] / baseline["cpu_ns_per_op_pooled"] - 1) * 100
        wall_change = (combined["wall_ns_per_op_median"] / baseline["wall_ns_per_op_median"] - 1) * 100
        print(
            f"{case['kind']}/{case['lifecycle']}/{case['attribute_mode']}/"
            f"{case['attribute_count']}/{case['extra']}: "
            f"combined CPU {cpu_change:+.1f}%, wall {wall_change:+.1f}%",
            flush=True,
        )
    output = {"metadata": metadata, "results": results}
    destination = args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Raw paired batches and summaries saved to {destination}", flush=True)


if __name__ == "__main__":
    main()

"""Compare retained memory for live sampled spans across audit modes.

Run from the repository root after the candidate changes are ready. The
script measures the incremental tracemalloc footprint of an unended cohort,
excluding provider, tracer, and constructor-attribute setup.
"""

import argparse
import gc
import hashlib
import json
import sys
import tracemalloc
from pathlib import Path

import compare as _compare

_AUDIT_DIR = Path(".agent/attribute-audit")
_MODES = _compare._MODES
_TRACE_MODULES = {
    "baseline": _compare._BASELINE_TRACE,
    "attributes-only": _compare._BASELINE_TRACE,
    "lazy-only": _compare.live_trace,
    "combined": _compare.live_trace,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _measure_cohort(mode: str, attribute_count: int, span_count: int) -> dict:
    _compare._set_mode(mode)
    tracer_provider = _TRACE_MODULES[mode].TracerProvider(
        sampler=_compare.sampling.ALWAYS_ON,
        shutdown_on_exit=False,
    )
    tracer = tracer_provider.get_tracer("retained-span-memory-audit")
    attributes = {f"key-{index}": f"value-{index}" for index in range(attribute_count)}

    for _ in range(100):
        span = tracer.start_span("memory-audit", attributes=attributes)
        span.end()
    gc.collect()

    cohort = []
    tracemalloc.start()
    try:
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()
        cohort = [tracer.start_span("memory-audit", attributes=attributes) for _ in range(span_count)]
        gc.collect()
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        current_delta = max(0, current_bytes - baseline_current)
        peak_delta = max(0, peak_bytes - baseline_peak)
        return {
            "mode": mode,
            "attribute_count": attribute_count,
            "span_count": span_count,
            "current_bytes": current_delta,
            "current_bytes_per_span": current_delta / span_count,
            "peak_bytes": peak_delta,
            "peak_bytes_per_span": peak_delta / span_count,
        }
    finally:
        cohort.clear()
        del cohort
        gc.collect()
        tracemalloc.stop()
        tracer_provider.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spans", type=int, default=2_000, help="Unended spans per cohort (default: 2000).")
    parser.add_argument(
        "--output",
        type=Path,
        default=_AUDIT_DIR / "retained-memory-comparison.json",
        help="Path for raw memory measurements and provenance.",
    )
    args = parser.parse_args()
    if args.spans < 1:
        parser.error("--spans must be at least 1")

    _compare._preflight_case()
    results = []
    for attribute_count in (4, 10):
        for mode in _MODES:
            result = _measure_cohort(mode, attribute_count, args.spans)
            results.append(result)
            print(
                f"{mode}/{attribute_count} attributes: "
                f"current={result['current_bytes_per_span']:.1f} B/span, "
                f"peak={result['peak_bytes_per_span']:.1f} B/span",
                flush=True,
            )

    metadata = {
        "python_version": sys.version,
        "span_count_per_cohort": args.spans,
        "attribute_counts": [4, 10],
        "modes": list(_MODES),
        "measurement": "tracemalloc bytes above pre-cohort baseline, after GC",
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
    output = {"metadata": metadata, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Retained memory measurements saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()

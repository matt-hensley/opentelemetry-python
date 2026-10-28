"""Paired CPU and wall-clock measurements for tracing hot paths.

Run from the repository root with the active candidate source tree. Baseline
functions are loaded from HEAD, and both implementations are measured in this
process in alternating order. Results are written to .agent/paired-cpu.json.
"""

import ast
import gc
import json
import statistics
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, NonRecordingSpan, SpanContext, SpanKind, TraceFlags, propagation
from opentelemetry.trace.propagation import set_span_in_context
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes

_REPEATS = 7
_TARGET_SECONDS = 0.35
_WARMUP_LOOPS = 2_000
_ATTRIBUTES = {"benchmark.key": "value"}
_UNSAMPLED_PARENT = NonRecordingSpan(
    SpanContext(
        0x123456789ABCDEF0123456789ABCDEF0,
        0x123456789ABCDEF0,
        False,
        TraceFlags(TraceFlags.DEFAULT),
    )
)


class _DropSampler(Sampler):
    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        return SamplingResult(Decision.DROP)

    def get_description(self) -> str:
        return "PairedBenchmarkDropSampler"


def _head_function(path: str, name: str, namespace: dict, class_name: str | None = None):
    source = subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True)
    nodes = ast.parse(source).body
    if class_name:
        nodes = next(node for node in nodes if isinstance(node, ast.ClassDef) and node.name == class_name).body
    node = next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)
    isolated = ast.Module(body=[node], type_ignores=[])
    result = namespace.copy()
    exec(compile(isolated, path, "exec"), result)  # noqa: S102
    return result[name]


_CANDIDATE_LOOKUP = propagation.get_current_span
_CANDIDATE_IS_RECORDING = Decision.is_recording
_BASELINE_LOOKUP = _head_function(
    "opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py",
    "get_current_span",
    {**vars(propagation), "get_value": context_api.get_value},
)
_BASELINE_IS_RECORDING = _head_function(
    "opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py",
    "is_recording",
    vars(sampling),
    "Decision",
)


def _set_mode(mode: str) -> None:
    lookup = _BASELINE_LOOKUP if mode == "baseline" else _CANDIDATE_LOOKUP
    is_recording = _BASELINE_IS_RECORDING if mode == "baseline" else _CANDIDATE_IS_RECORDING
    propagation.get_current_span = lookup
    trace.get_current_span = lookup
    sampling.get_current_span = lookup
    Decision.is_recording = is_recording


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


def _calibrate(operation) -> int:
    loops = 10_000
    pilot = _measure(operation, loops)
    estimate = round(loops * _TARGET_SECONDS / pilot["wall_seconds"])
    return max(loops, estimate)


def _case_definitions():
    return [
        ("always-off-root", sampling.ALWAYS_OFF, "root"),
        ("always-off-local-child", sampling.ALWAYS_OFF, "local"),
        (
            "parentbased-ratio-zero-root",
            sampling.ParentBased(sampling.TraceIdRatioBased(0)),
            "root",
        ),
        (
            "parentbased-ratio-zero-local-child",
            sampling.ParentBased(sampling.TraceIdRatioBased(0)),
            "local",
        ),
        ("always-on-root", sampling.ALWAYS_ON, "root"),
        ("always-on-sdk-recording-parent", sampling.ALWAYS_ON, "recording"),
        ("custom-drop-root", _DropSampler(), "root"),
    ]


def _run_case(label: str, sampler: Sampler, parent_kind: str, lifecycle: str) -> dict:
    provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
    tracer = provider.get_tracer("paired-cpu-benchmark")
    parent_provider = None
    parent_span = None
    ambient = Context({"benchmark.baggage": {"item": "value"}, "benchmark.extra": "value"})
    ambient_token = context_api.attach(ambient)

    parent_context = None
    if parent_kind == "local":
        parent_context = set_span_in_context(_UNSAMPLED_PARENT, ambient)
    elif parent_kind == "recording":
        parent_provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
        parent_span = parent_provider.get_tracer("paired-cpu-parent").start_span("parent")
        parent_context = set_span_in_context(parent_span, ambient)

    if lifecycle == "start-span":

        def operation() -> None:
            span = tracer.start_span("benchmark", context=parent_context, attributes=_ATTRIBUTES)
            span.end()

    else:

        def operation() -> None:
            with tracer.start_as_current_span("benchmark", context=parent_context, attributes=_ATTRIBUTES):
                pass

    samples: dict[str, list[dict[str, float | int]]] = {"baseline": [], "candidate": []}
    try:
        for mode in ("baseline", "candidate"):
            _set_mode(mode)
            _measure(operation, _WARMUP_LOOPS)
        _set_mode("candidate")
        loops = _calibrate(operation)

        for pair in range(_REPEATS):
            order = ("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline")
            for mode in order:
                _set_mode(mode)
                samples[mode].append(_measure(operation, loops))
    finally:
        _set_mode("candidate")
        if parent_span is not None:
            parent_span.end()
        if parent_provider is not None:
            parent_provider.shutdown()
        provider.shutdown()
        context_api.detach(ambient_token)

    summary = {}
    for mode, batches in samples.items():
        total_loops = sum(batch["loops"] for batch in batches)
        summary[mode] = {
            "cpu_ns_per_op_pooled": sum(batch["cpu_seconds"] for batch in batches) * 1e9 / total_loops,
            "wall_ns_per_op_median": statistics.median(batch["wall_ns_per_op"] for batch in batches),
        }
    return {"case": label, "loops_per_batch": loops, "samples": samples, "summary": summary}


def main() -> None:
    results = []
    for case_label, sampler, parent_kind in _case_definitions():
        for lifecycle in ("start-span", "current-span"):
            label = f"{case_label}/{lifecycle}"
            result = _run_case(label, sampler, parent_kind, lifecycle)
            results.append(result)
            baseline = result["summary"]["baseline"]
            candidate = result["summary"]["candidate"]
            cpu_change = (candidate["cpu_ns_per_op_pooled"] / baseline["cpu_ns_per_op_pooled"] - 1) * 100
            wall_change = (candidate["wall_ns_per_op_median"] / baseline["wall_ns_per_op_median"] - 1) * 100
            print(
                f"{label}: CPU {baseline['cpu_ns_per_op_pooled']:.1f} -> "
                f"{candidate['cpu_ns_per_op_pooled']:.1f} ns/op ({cpu_change:+.1f}%); "
                f"wall median {baseline['wall_ns_per_op_median']:.1f} -> "
                f"{candidate['wall_ns_per_op_median']:.1f} ns/op ({wall_change:+.1f}%)",
                flush=True,
            )
    destination = Path(".agent/paired-cpu.json")
    destination.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Raw paired batches and summaries saved to {destination}", flush=True)


if __name__ == "__main__":
    main()

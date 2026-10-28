"""Paired CPU and wall audit of W3C extraction, including custom getters."""
import gc
import hashlib
import inspect
import json
import statistics
import sys
import textwrap
import time
from pathlib import Path

import psutil
import opentelemetry.trace.propagation.tracecontext as tc
import opentelemetry.trace.span as spanmod
import opentelemetry.propagators.textmap as tm
from opentelemetry import trace
from opentelemetry.trace import TraceState

Prop = tc.TraceContextTextMapPropagator
PAIRS = 9
TARGET_SECONDS = 0.8
WARMUP = 1000
src = textwrap.dedent(inspect.getsource(Prop.extract))
src = src.replace("re.search(self._TRACEPARENT_HEADER_FORMAT_RE, header[0])", "self._TRACEPARENT_HEADER_FORMAT_RE.search(header[0])")
src = src.replace("version: str = match.group(1)", "version, trace_id, span_id, trace_flags, suffix = match.groups()")
for line in ("trace_id: str = match.group(2)", "span_id: str = match.group(3)", "trace_flags: str = match.group(4)"):
    src = src.replace("    " + line + "\n", "")
src = src.replace("if match.group(5):  # type: ignore", "if suffix:")
assert "re.search(" not in src and "match.group(" not in src
namespace = vars(tc).copy()
exec(compile(src, "<candidate-extract>", "exec"), namespace)
fast_extract = namespace["extract"]

state_src = textwrap.dedent(inspect.getsource(TraceState.from_header.__func__)).replace("@classmethod\n", "", 1)
state_src = state_src.replace(
    "    return cls(list(pairs.items()))",
    """    if cls is TraceState and len(pairs) <= _TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS:
        result = cls()
        result._dict = pairs
        return result
    return cls(list(pairs.items()))""",
)
assert "result._dict = pairs" in state_src
namespace = vars(spanmod).copy()
exec(compile(state_src, "<candidate-tracestate>", "exec"), namespace)
fast_state = namespace["from_header"]

get_src = """def get(self, carrier, key):
    val = carrier.get(key, None)
    if val is None:
        return None
    if isinstance(val, str):
        return [val]
    if isinstance(val, Iterable):
        return list(val)
    return [val]
"""
namespace = vars(tm).copy()
exec(compile(get_src, "<candidate-getter>", "exec"), namespace)
fast_get = namespace["get"]
original_extract = Prop.extract
original_state = TraceState.__dict__["from_header"]
original_get = tm.DefaultGetter.get

def install(candidate):
    Prop.extract = fast_extract if candidate else original_extract
    TraceState.from_header = classmethod(fast_state) if candidate else original_state
    tm.DefaultGetter.get = fast_get if candidate else original_get

class ListGetter(tm.Getter):
    def get(self, carrier, key):
        return carrier.get(key)
    def keys(self, carrier):
        return list(carrier)

def fingerprint(prop, carrier, getter):
    context = trace.get_current_span(prop.extract(carrier, getter=getter)).get_span_context()
    return (context.trace_id, context.span_id, context.trace_flags, context.is_remote, tuple(context.trace_state.items()))

def measure(operation, loops):
    operation(WARMUP)
    gc.collect()
    enabled = gc.isenabled()
    gc.disable()
    try:
        cpu_start = time.process_time_ns()
        wall_start = time.perf_counter_ns()
        operation(loops)
        wall_ns = time.perf_counter_ns() - wall_start
        cpu_ns = time.process_time_ns() - cpu_start
    finally:
        if enabled:
            gc.enable()
    return {"loops": loops, "cpu_ns": cpu_ns, "wall_ns": wall_ns}

def main():
    prop = Prop()
    parent = "00-12345678901234567890123456789012-1234567890123456-01"
    cases = [
        ("default_strings/no-state", {"traceparent": parent}, tm.default_getter),
        ("default_strings/one-state", {"traceparent": parent, "tracestate": "vendor=value"}, tm.default_getter),
        ("default_strings/three-state", {"traceparent": parent, "tracestate": "vendor=value,foo=bar,baz=qux"}, tm.default_getter),
        ("custom_lists/no-state", {"traceparent": [parent]}, ListGetter()),
        ("custom_lists/three-state", {"traceparent": [parent], "tracestate": ["vendor=value,foo=bar,baz=qux"]}, ListGetter()),
    ]
    process = psutil.Process()
    previous_affinity = process.cpu_affinity()
    process.cpu_affinity([previous_affinity[0]])
    results = []
    try:
        for name, carrier, getter in cases:
            install(False)
            expected = fingerprint(prop, carrier, getter)
            install(True)
            assert fingerprint(prop, carrier, getter) == expected, name
            def operation(loops):
                for _ in range(loops):
                    prop.extract(carrier, getter=getter)
            install(False)
            pilot = measure(operation, 10000)
            loops = max(10000, round(10000 * TARGET_SECONDS * 1e9 / pilot["wall_ns"]))
            samples = []
            for pair in range(PAIRS):
                order = ("baseline", "combined") if pair % 2 == 0 else ("combined", "baseline")
                for mode in order:
                    install(mode == "combined")
                    samples.append({"pair": pair, "mode": mode, **measure(operation, loops)})
            summary = {}
            for mode in ("baseline", "combined"):
                batches = [sample for sample in samples if sample["mode"] == mode]
                summary[mode] = {
                    "cpu_ns_op_pooled": sum(sample["cpu_ns"] for sample in batches) / sum(sample["loops"] for sample in batches),
                    "wall_ns_op_median": statistics.median(sample["wall_ns"] / sample["loops"] for sample in batches),
                    "min_cpu_seconds": min(sample["cpu_ns"] for sample in batches) / 1e9,
                }
            change = {key: (summary["combined"][key] / summary["baseline"][key] - 1) * 100 for key in ("cpu_ns_op_pooled", "wall_ns_op_median")}
            results.append({"case": name, "loops_per_batch": loops, "summary": summary, "change_percent": change, "samples": samples})
            print(f"{name}: CPU {change['cpu_ns_op_pooled']:+.1f}%, wall {change['wall_ns_op_median']:+.1f}%", flush=True)
    finally:
        install(False)
        process.cpu_affinity(previous_affinity)
    paths = [
        Path("opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py"),
        Path("opentelemetry-api/src/opentelemetry/trace/span.py"),
        Path("opentelemetry-api/src/opentelemetry/propagators/textmap.py"),
    ]
    output = {
        "metadata": {
            "python": sys.version,
            "pairs": PAIRS,
            "target_seconds": TARGET_SECONDS,
            "affinity": [previous_affinity[0]],
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            "candidate_sources": {"extract": src, "tracestate": state_src, "getter": get_src},
        },
        "results": results,
    }
    Path(".agent/propagation-audit/paired-extract-comparison.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()

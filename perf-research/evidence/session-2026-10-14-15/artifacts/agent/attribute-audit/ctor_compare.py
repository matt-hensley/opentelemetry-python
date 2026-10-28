"""Paired constructor-specialization experiment; not a product benchmark."""

import hashlib
import json
import statistics
import time
from pathlib import Path

import opentelemetry.attributes as attributes_module
from opentelemetry.sdk.trace import TracerProvider, sampling

AUDIT = Path(".agent/attribute-audit")
LOOPS = 50_000
PAIRS = 9
BASELINE_INIT = attributes_module.BoundedAttributes.__init__
candidate_file = AUDIT / "ctor-candidate.py"
candidate_text = candidate_file.read_text(encoding="utf-8")
source = candidate_text.split("SOURCE = '''\\\n", 1)[1].split("'''", 1)[0]
candidate_globals = vars(attributes_module).copy()
exec(compile(source, str(candidate_file), "exec"), candidate_globals)  # noqa: S102
CANDIDATE_INIT = candidate_globals["__init__"]


def timed_batch(tracer, values, init):
    attributes_module.BoundedAttributes.__init__ = init
    start = time.process_time_ns()
    for _ in range(LOOPS):
        span = tracer.start_span("span", attributes=values)
        span.end()
    return time.process_time_ns() - start


def main():
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("ctor-audit")
    cases = {
        "empty": {},
        "4_strings": {f"key-{i}": f"value-{i}" for i in range(4)},
        "4_mixed": {"a": "value", "b": 42, "c": False, "d": 3.14},
        "10_strings": {f"key-{i}": f"value-{i}" for i in range(10)},
        "10_mixed": {f"key-{i}": (f"value-{i}" if i % 2 == 0 else i) for i in range(10)},
    }
    results = {}
    try:
        for name, attrs in cases.items():
            # Warm both implementations outside the recorded samples.
            timed_batch(tracer, attrs, BASELINE_INIT)
            timed_batch(tracer, attrs, CANDIDATE_INIT)
            raw = {"baseline_cpu_ns": [], "candidate_cpu_ns": []}
            for pair in range(PAIRS):
                order = ("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline")
                for mode in order:
                    init = BASELINE_INIT if mode == "baseline" else CANDIDATE_INIT
                    raw[f"{mode}_cpu_ns"].append(timed_batch(tracer, attrs, init))
            baseline_median = statistics.median(raw["baseline_cpu_ns"]) / LOOPS
            candidate_median = statistics.median(raw["candidate_cpu_ns"]) / LOOPS
            results[name] = {
                "baseline_median_ns_per_op": baseline_median,
                "candidate_median_ns_per_op": candidate_median,
                "median_cpu_change_percent": (candidate_median / baseline_median - 1) * 100,
                "raw_samples_cpu_ns": raw,
            }
    finally:
        attributes_module.BoundedAttributes.__init__ = BASELINE_INIT
        provider.shutdown()
    output = {
        "provenance": {
            "candidate_file": str(candidate_file),
            "candidate_sha256": hashlib.sha256(candidate_file.read_bytes()).hexdigest(),
            "adoption_only_source_sha256": hashlib.sha256(
                Path("opentelemetry-api/src/opentelemetry/attributes/__init__.py").read_bytes()
            ).hexdigest(),
            "loops_per_sample": LOOPS,
            "pairs": PAIRS,
            "timing": "time.process_time_ns; same provider/tracer per case; alternating lane order",
        },
        "results": results,
    }
    (AUDIT / "paired-ctor-comparison.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

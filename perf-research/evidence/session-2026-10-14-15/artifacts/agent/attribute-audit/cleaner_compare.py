"""Compare reusing the primitive type tuple with rebuilding it per call."""

import argparse
import hashlib
import inspect
import json
import statistics
import sys
from pathlib import Path

import bulk_compare as harness
import opentelemetry.attributes as attributes_module
from opentelemetry.sdk.trace import TracerProvider, sampling

original = attributes_module._clean_attribute_value
candidate_source = inspect.getsource(original).replace(
    "isinstance(value, (NoneType, bool, int, float, bytes))",
    "isinstance(value, _SCALAR_TYPES)",
)
assert candidate_source != inspect.getsource(original)
candidate_globals = vars(attributes_module).copy()
candidate_globals["_SCALAR_TYPES"] = (type(None), bool, int, float, bytes)
exec(compile(candidate_source, str(Path(__file__)), "exec"), candidate_globals)
candidate = candidate_globals["_clean_attribute_value"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--seconds", type=float, default=0.8)
    parser.add_argument("--output", type=Path, default=Path(".agent/attribute-audit/paired-cleaner-comparison.json"))
    args = parser.parse_args()
    affinity, process, previous_affinity = harness._pin_cpu()
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("cleaner-audit")
    modes = {"current": original, "tuple-constant": candidate}
    results = []
    try:
        for count, shape in ((0, "empty"), (4, "strings"), (10, "strings"), (10, "mixed")):
            values = ("value", 42, False, 3.14, None) if shape == "mixed" else ("value",)
            attributes = {f"key-{i}": values[i % len(values)] for i in range(count)}

            def operation(loops):
                for _ in range(loops):
                    span = tracer.start_span("benchmark", attributes=attributes)
                    span.end()

            attributes_module._clean_attribute_value = original
            loops = harness._calibrate(operation, args.seconds)
            samples = []
            for pair in range(args.repeats):
                order = tuple(modes) if pair % 2 == 0 else tuple(reversed(modes))
                for mode in order:
                    attributes_module._clean_attribute_value = modes[mode]
                    samples.append({"pair": pair, "mode": mode, **harness._measure(operation, loops)})
            summary = {}
            for mode in modes:
                batches = [sample for sample in samples if sample["mode"] == mode]
                summary[mode] = {
                    "cpu_ns": sum(batch["cpu_seconds"] for batch in batches) * 1e9 / sum(batch["loops"] for batch in batches),
                    "wall_ns": statistics.median(batch["wall_ns_per_op"] for batch in batches),
                }
            change = {key: (summary["tuple-constant"][key] / summary["current"][key] - 1) * 100 for key in ("cpu_ns", "wall_ns")}
            results.append({"count": count, "shape": shape, "samples": samples, "summary": summary, "change_percent": change})
            print(f"{shape}/{count}: CPU {change['cpu_ns']:+.1f}%, wall {change['wall_ns']:+.1f}%", flush=True)
    finally:
        attributes_module._clean_attribute_value = original
        provider.shutdown()
        harness._restore_affinity(process, previous_affinity)
    output = {
        "metadata": {
            "python": sys.version,
            "affinity": affinity,
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "attributes_sha256": hashlib.sha256(Path(attributes_module.__file__).read_bytes()).hexdigest(),
            "trace_sha256": hashlib.sha256(Path(sys.modules["opentelemetry.sdk.trace"].__file__).read_bytes()).hexdigest(),
            "candidate_source": candidate_source,
        },
        "results": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

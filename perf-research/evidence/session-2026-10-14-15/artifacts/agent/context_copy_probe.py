"""Local candidate comparison; not part of the submitted benchmark suite."""

import gc
import json
import statistics
import time

from opentelemetry import context
from opentelemetry.context import Context


def candidate(key, value, source=None):
    if source is None:
        source = context.get_current()
    if type(source) is Context:
        result = Context(source)
        dict.__setitem__(result, key, value)
        return result
    values = source.copy()
    values[key] = value
    return Context(values)


def measure(fn, source, loops=1_000_000):
    start_cpu = time.process_time()
    start_wall = time.perf_counter()
    for _ in range(loops):
        fn("target", 1, source)
    return {
        "cpu_ns": (time.process_time() - start_cpu) * 1e9 / loops,
        "wall_ns": (time.perf_counter() - start_wall) * 1e9 / loops,
    }


def main():
    rows = []
    gc.disable()
    for size in (0, 1, 2, 8):
        source = Context({str(i): i for i in range(size)})
        samples = {"baseline": [], "candidate": []}
        variants = [("baseline", context.set_value), ("candidate", candidate)]
        for repeat in range(5):
            for name, fn in variants[:: 1 if repeat % 2 == 0 else -1]:
                samples[name].append(measure(fn, source))
        rows.append({"size": size, "samples": samples})
        print(json.dumps({"size": size, **{
            name: {metric: statistics.median(sample[metric] for sample in values)
                   for metric in ("cpu_ns", "wall_ns")}
            for name, values in samples.items()
        }}), flush=True)
    with open(".agent/context-copy-probe.json", "w") as output:
        json.dump(rows, output, indent=2)


if __name__ == "__main__":
    main()

"""Compare specialized traceparent parsers against the optimized regex prototype."""
import argparse
import hashlib
import json
import random
import statistics
import sys
import textwrap
from pathlib import Path

import extract_compare as audit
from opentelemetry import trace
from opentelemetry.context import Context

HEX = "0123456789abcdef"
DELETE_HEX = str.maketrans("", "", HEX + "-")
HEX_VALUES = {character: value for value, character in enumerate(HEX)}
START = audit.src.index("    match = self._TRACEPARENT_HEADER_FORMAT_RE.search(header[0])")
END = audit.src.index("    tracestate_headers = getter.get", START)
FALLBACK = """    else:
        match = self._TRACEPARENT_HEADER_FORMAT_RE.search(value)
        if not match:
            return context
        version, trace_id, span_id, trace_flags, suffix = match.groups()
        if version == "ff" or (version == "00" and suffix):
            return context
        trace_id = int(trace_id, 16)
        span_id = int(span_id, 16)
        trace_flags = int(trace_flags, 16)
    if not trace_id or not span_id:
        return context

"""
PREFIX = """    value = header[0]
    if type(value) is str and len(value) == 55 and value.startswith("00-") and value[35] == "-" and value[52] == "-":
"""
SLICES = """        trace_id = value[3:35]
        span_id = value[36:52]
        trace_flags = value[53:55]
"""
DECODE = """        trace_id = int(trace_id, 16)
        span_id = int(span_id, 16)
        trace_flags = int(trace_flags, 16)
"""
BODIES = {
    "native-strings": """        if not value.isascii() or value.lower() != value:
            return context
""" + SLICES + """        if not (trace_id.isalnum() and span_id.isalnum() and trace_flags.isalnum()):
            return context
        try:
""" + textwrap.indent(DECODE, "    ") + """        except ValueError:
            return context
""",
    "translate": """        if value.count("-") != 3 or value.translate(_DELETE_HEX):
            return context
""" + SLICES + DECODE,
    "character-loop": SLICES + """        for field in (trace_id, span_id, trace_flags):
            for character in field:
                if character not in _HEX:
                    return context
""" + DECODE,
    "fused-loop": """        digit_for = _HEX_VALUES.get
        trace_id = 0
        for character in value[3:35]:
            digit = digit_for(character)
            if digit is None:
                return context
            trace_id = (trace_id << 4) | digit
        span_id = 0
        for character in value[36:52]:
            digit = digit_for(character)
            if digit is None:
                return context
            span_id = (span_id << 4) | digit
        trace_flags = 0
        for character in value[53:55]:
            digit = digit_for(character)
            if digit is None:
                return context
            trace_flags = (trace_flags << 4) | digit
""",
}
CANDIDATES = {"optimized-regex": audit.fast_extract}
SOURCES = {}
for name, body in BODIES.items():
    source = audit.src[:START] + PREFIX + body + FALLBACK + audit.src[END:]
    source = source.replace("trace_id=int(trace_id, 16)", "trace_id=trace_id").replace("span_id=int(span_id, 16)", "span_id=span_id").replace("trace.TraceFlags(int(trace_flags, 16))", "trace.TraceFlags(trace_flags)")
    namespace = vars(audit.tc).copy()
    namespace.update(_HEX=HEX, _HEX_VALUES=HEX_VALUES, _DELETE_HEX=DELETE_HEX)
    exec(compile(source, "<traceparent-" + name + ">", "exec"), namespace)
    CANDIDATES[name] = namespace["extract"]
    SOURCES[name] = source

class RecordingGetter(audit.tm.Getter):
    def __init__(self):
        self.calls = []
    def get(self, carrier, key):
        self.calls.append(key)
        return carrier.get(key)
    def keys(self, carrier):
        return list(carrier)

def fingerprint(parser, parent):
    getter = RecordingGetter()
    original_context = Context({"retained": "value"})
    output = parser(audit.Prop(), {"traceparent": [parent], "tracestate": ["vendor=value"]}, context=original_context, getter=getter)
    context = trace.get_current_span(output).get_span_context()
    return (
        output is original_context, output.get("retained"), tuple(getter.calls),
        context.trace_id, context.span_id, context.trace_flags,
        context.is_remote, tuple(context.trace_state.items()),
    )

def corpus():
    rng = random.Random(173)
    seeds = [
        "00-12345678901234567890123456789012-1234567890123456-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00",
        "00-" + "0" * 32 + "-" + "0" * 16 + "-ff",
    ]
    samples = list(seeds)
    for seed in seeds:
        for prefix in ("", " ", "\t", " \t", "\n", "\r", "\u00a0"):
            for suffix in ("", " ", "\t", "\n", " \t\n", "\r\n", "-","-suffix", "-x\n"):
                samples.append(prefix + seed + suffix)
        for version in ("00", "01", "02", "0a", "fe", "ff", "FF", "g0", ""):
            for suffix in ("", "-", "-extra", "-extra\n", "\n"):
                samples.append(version + seed[2:] + suffix)
        for position in range(len(seed)):
            for character in "0fAz_+- \t\n\r\u00e9\u0661":
                samples.append(seed[:position] + character + seed[position + 1:])
            samples.append(seed[:position] + seed[position + 1:])
            samples.append(seed[:position] + "0" + seed[position:])
        for flags in range(256):
            samples.append(seed[:-2] + f"{flags:02x}")
    for _ in range(200):
        samples.append(f"00-{rng.getrandbits(128):032x}-{rng.getrandbits(64):016x}-{rng.getrandbits(8):02x}")
    alphabet = HEX + "XYZ_- +\t\n\r\u0661"
    for _ in range(8000):
        value = rng.choice(seeds)
        for _ in range(rng.randrange(1, 5)):
            position = rng.randrange(len(value))
            value = value[:position] + rng.choice(alphabet) + value[position + 1:]
        samples.append(value)
    return samples

def check():
    samples = corpus()
    # Compare against the actual checked-out parser, not another candidate.
    for value in samples:
        expected = fingerprint(audit.original_extract, value)
        for name, parser in CANDIDATES.items():
            actual = fingerprint(parser, value)
            if actual != expected:
                raise AssertionError((name, repr(value), expected, actual))
    print(f"All {len(samples)} differential header cases agree for {len(CANDIDATES)} parsers", flush=True)
    return len(samples)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--seconds", type=float, default=0.6)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--mode", action="append")
    parser.add_argument("--output", type=Path, default=Path(".agent/propagation-audit/paired-parser-comparison.json"))
    args = parser.parse_args()
    audit.install(True)
    try:
        checked = check()
    finally:
        audit.install(False)
    if args.check_only:
        return
    names = args.mode or list(CANDIDATES)
    prop = audit.Prop()
    parent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    cases = [
        ("default_strings/no-state", {"traceparent": parent}, audit.tm.default_getter),
        ("custom_lists/no-state", {"traceparent": [parent]}, audit.ListGetter()),
        ("custom_lists/three-state", {"traceparent": [parent], "tracestate": ["vendor=value,foo=bar,baz=qux"]}, audit.ListGetter()),
    ]
    process = audit.psutil.Process()
    previous_affinity = process.cpu_affinity()
    process.cpu_affinity([previous_affinity[0]])
    results = []
    try:
        audit.install(True)
        for label, carrier, getter in cases:
            def operation(loops):
                for _ in range(loops):
                    prop.extract(carrier, getter=getter)
            audit.Prop.extract = CANDIDATES["optimized-regex"]
            pilot = audit.measure(operation, 10000)
            loops = max(10000, round(10000 * args.seconds * 1e9 / pilot["wall_ns"]))
            samples = []
            for pair in range(args.repeats):
                # Rotate all candidates through all positions.
                order = names[pair % len(names):] + names[:pair % len(names)]
                if pair % 2:
                    order = list(reversed(order))
                for name in order:
                    audit.Prop.extract = CANDIDATES[name]
                    samples.append({"pair": pair, "mode": name, **audit.measure(operation, loops)})
            summary = {}
            for name in names:
                batches = [sample for sample in samples if sample["mode"] == name]
                summary[name] = {
                    "cpu_ns_op": sum(sample["cpu_ns"] for sample in batches) / sum(sample["loops"] for sample in batches),
                    "wall_ns_op": statistics.median(sample["wall_ns"] / sample["loops"] for sample in batches),
                }
            baseline = summary["optimized-regex"]
            for name in names:
                change = (summary[name]["cpu_ns_op"] / baseline["cpu_ns_op"] - 1) * 100
                wall = (summary[name]["wall_ns_op"] / baseline["wall_ns_op"] - 1) * 100
                print(f"{label}/{name}: CPU {change:+.1f}%, wall {wall:+.1f}%", flush=True)
            results.append({"case": label, "loops_per_batch": loops, "summary": summary, "samples": samples})
    finally:
        audit.install(False)
        process.cpu_affinity(previous_affinity)
    output = {
        "metadata": {
            "python": sys.version,
            "checked_headers": checked,
            "parsers_checked": list(CANDIDATES),
            "pairs": args.repeats,
            "target_seconds": args.seconds,
            "affinity": [previous_affinity[0]],
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "regex_harness_sha256": hashlib.sha256(Path(audit.__file__).read_bytes()).hexdigest(),
            "sources": SOURCES,
        },
        "results": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()

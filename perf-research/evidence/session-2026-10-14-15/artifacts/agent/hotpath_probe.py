import gc
import json
import statistics
import time

from opentelemetry import context
from opentelemetry.context import get_current
from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.trace import NonRecordingSpan, Span, INVALID_SPAN, SpanContext
from opentelemetry.trace.propagation import _SPAN_KEY, get_current_span


def inline_get_current_span(parent=None):
    span = (get_current() if parent is None else parent).get(_SPAN_KEY)
    if span is None or not isinstance(span, Span):
        return INVALID_SPAN
    return span


def exact_get_current_span(parent=None):
    span = context.get_value(_SPAN_KEY, context=parent)
    if span is None or (type(span) is not NonRecordingSpan and not isinstance(span, Span)):
        return INVALID_SPAN
    return span


def both_get_current_span(parent=None):
    span = (get_current() if parent is None else parent).get(_SPAN_KEY)
    if span is None or (type(span) is not NonRecordingSpan and not isinstance(span, Span)):
        return INVALID_SPAN
    return span


def run(fn, value, count=1_000_000):
    start_cpu = time.process_time()
    start_wall = time.perf_counter()
    for _ in range(count):
        fn(value)
    return [(time.process_time() - start_cpu) * 1e9 / count,
            (time.perf_counter() - start_wall) * 1e9 / count]


gc.disable()
parent = NonRecordingSpan(SpanContext(123, 456, False))
contexts = [context.Context(), context.set_value(_SPAN_KEY, parent)]
token = context.attach(contexts[1])
try:
    for label, value in [("empty", contexts[0]), ("parent", contexts[1]), ("ambient", None)]:
        samples = {name: [] for name in ("baseline", "inline", "exact", "both")}
        variants = [("baseline", get_current_span), ("inline", inline_get_current_span),
                    ("exact", exact_get_current_span), ("both", both_get_current_span)]
        for repeat in range(5):
            for name, fn in variants[::1 if repeat % 2 == 0 else -1]:
                samples[name].append(run(fn, value))
        print(json.dumps({"case": label, **{name: [statistics.median(s[i] for s in values)
                                                   for i in (0, 1)]
                                              for name, values in samples.items()}}), flush=True)
finally:
    context.detach(token)

def old_recording(decision):
    return decision in (Decision.RECORD_ONLY, Decision.RECORD_AND_SAMPLE)

def identity_recording(decision):
    return decision is not Decision.DROP

for value in Decision:
    samples = {"old": [], "identity": []}
    for repeat in range(5):
        for name, fn in [("old", old_recording), ("identity", identity_recording)][::1 if repeat % 2 == 0 else -1]:
            samples[name].append(run(fn, value))
    print(json.dumps({"decision": value.name, **{name: [statistics.median(s[i] for s in values)
                                                      for i in (0, 1)]
                                                 for name, values in samples.items()}}), flush=True)

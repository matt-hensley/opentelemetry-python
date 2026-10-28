# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.trace import SpanContext, TraceFlags

_EVENT_NAME = "benchmark-event"
_LINK_CONTEXT = SpanContext(
    trace_id=0x123456789ABCDEF0123456789ABCDEF0,
    span_id=0x123456789ABCDEF0,
    is_remote=True,
    trace_flags=TraceFlags(TraceFlags.SAMPLED),
)


@pytest.mark.parametrize("lifecycle", ["start-span", "current-span"])
@pytest.mark.parametrize("attribute_mode", ["constructor", "set-attribute", "set-attributes"])
@pytest.mark.parametrize("attribute_count", [0, 4, 10, 64])
def test_benchmark_span_attributes(
    benchmark,
    lifecycle: str,
    attribute_mode: str,
    attribute_count: int,
) -> None:
    attributes = {f"key-{index}": f"value-{index}" for index in range(attribute_count)}
    attribute_items = tuple(attributes.items())
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("span-attributes-benchmark")

    def mutate(span) -> None:
        if attribute_mode == "set-attribute":
            for key, value in attribute_items:
                span.set_attribute(key, value)
        elif attribute_mode == "set-attributes":
            span.set_attributes(attributes)

    if lifecycle == "start-span":

        def operation() -> None:
            span = tracer.start_span(
                "benchmark",
                attributes=attributes if attribute_mode == "constructor" else None,
            )
            mutate(span)
            span.end()

    else:

        def operation() -> None:
            with tracer.start_as_current_span(
                "benchmark",
                attributes=attributes if attribute_mode == "constructor" else None,
            ) as span:
                mutate(span)

    try:
        benchmark(operation)
    finally:
        provider.shutdown()


@pytest.mark.parametrize("attribute_count", [4, 10, 64])
@pytest.mark.parametrize("overlap", [False, True], ids=["disjoint", "overlapping"])
def test_benchmark_nonempty_bulk_update(benchmark, attribute_count: int, overlap: bool) -> None:
    seed_attributes = {"seed-0": "initial-0", "seed-1": "initial-1"}
    if overlap:
        update_attributes = {
            **{f"seed-{index}": f"updated-{index}" for index in range(min(attribute_count, 2))},
            **{f"update-{index}": f"value-{index}" for index in range(max(0, attribute_count - 2))},
        }
    else:
        update_attributes = {f"update-{index}": f"value-{index}" for index in range(attribute_count)}
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("span-bulk-update-benchmark")

    def operation() -> None:
        span = tracer.start_span("benchmark", attributes=seed_attributes)
        span.set_attributes(update_attributes)
        span.end()

    try:
        benchmark(operation)
    finally:
        provider.shutdown()


@pytest.mark.parametrize("extra", ["empty", "one-event", "one-link", "one-event-and-link"])
def test_benchmark_empty_event_link_storage(benchmark, extra: str) -> None:
    provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
    tracer = provider.get_tracer("span-storage-benchmark")

    def operation() -> None:
        span = tracer.start_span("benchmark")
        if extra == "one-event":
            span.add_event(_EVENT_NAME)
        elif extra == "one-link":
            span.add_link(_LINK_CONTEXT)
        elif extra == "one-event-and-link":
            span.add_event(_EVENT_NAME)
            span.add_link(_LINK_CONTEXT)
        span.end()

    try:
        benchmark(operation)
    finally:
        provider.shutdown()

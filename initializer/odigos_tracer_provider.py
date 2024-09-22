from os import environ
from warnings import filterwarnings
from opentelemetry.trace import (
    TracerProvider, 
    Tracer, 
    Span, 
    SpanKind, 
    SpanContext,
    NoOpTracer,
    Link, 
    use_span, 
    get_current_span, 
    TraceFlags, 
    NonRecordingSpan
)
from opentelemetry.sdk.trace import (
    sampling,
    SynchronousMultiSpanProcessor,
    ConcurrentMultiSpanProcessor,
    SpanProcessor,
    SpanLimits,
    _Span,
)
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationInfo,
    InstrumentationScope,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator

from opentelemetry.sdk.resources import Resource
from opentelemetry.util import types
from opentelemetry import context as context_api
from opentelemetry.util._decorator import _agnosticcontextmanager

import typing
from typing import Iterator, Optional, Sequence, Union

import atexit
from opentelemetry.sdk.environment_variables import (
    OTEL_SDK_DISABLED,
)


class OdigosTracerProvider(TracerProvider):
    """See `opentelemetry.trace.TracerProvider`."""

    def __init__(
        self,
        sampler: Optional[sampling.Sampler] = None,
        resource: Optional[Resource] = None,
        shutdown_on_exit: bool = True,
        active_span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor, None
        ] = None,
        id_generator: Optional[IdGenerator] = None,
        span_limits: Optional[SpanLimits] = None,
    ) -> None:
        self._active_span_processor = (
            active_span_processor or SynchronousMultiSpanProcessor()
        )
        if id_generator is None:
            self.id_generator = RandomIdGenerator()
        else:
            self.id_generator = id_generator
        if resource is None:
            self._resource = Resource.create({})
        else:
            self._resource = resource
        if not sampler:
            sampler = sampling._get_from_env_or_default()
        self.sampler = sampler
        self._span_limits = span_limits or SpanLimits()
        disabled = environ.get(OTEL_SDK_DISABLED, "")
        self._disabled = disabled.lower().strip() == "true"
        self._atexit_handler = None

        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)

    @property
    def resource(self) -> Resource:
        return self._resource

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: typing.Optional[str] = None,
        schema_url: typing.Optional[str] = None,
    ) -> "OdigosTracer":
        if self._disabled:
            return NoOpTracer()
        if not instrumenting_module_name:  # Reject empty strings too.
            instrumenting_module_name = ""
        if instrumenting_library_version is None:
            instrumenting_library_version = ""


        return OdigosTracer(
            self.sampler,
            self.resource,
            self._active_span_processor,
            self.id_generator,
            instrumentation_info,
            self._span_limits,
            InstrumentationScope(
                instrumenting_module_name,
                instrumenting_library_version,
                schema_url,
            ),
        )
        
    def add_span_processor(self, span_processor: SpanProcessor) -> None:
        """Registers a new :class:`SpanProcessor` for this `TracerProvider`.

        The span processors are invoked in the same order they are registered.
        """

        # no lock here because add_span_processor is thread safe for both
        # SynchronousMultiSpanProcessor and ConcurrentMultiSpanProcessor.
        self._active_span_processor.add_span_processor(span_processor)

    def shutdown(self):
        """Shut down the span processors added to the tracer provider."""
        self._active_span_processor.shutdown()
        if self._atexit_handler is not None:
            atexit.unregister(self._atexit_handler)
            self._atexit_handler = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Requests the active span processor to process all spans that have not
        yet been processed.

        By default force flush is called sequentially on all added span
        processors. This means that span processors further back in the list
        have less time to flush their spans.
        To have span processors flush their spans in parallel it is possible to
        initialize the tracer provider with an instance of
        `ConcurrentMultiSpanProcessor` at the cost of using multiple threads.

        Args:
            timeout_millis: The maximum amount of time to wait for spans to be
                processed.

        Returns:
            False if the timeout is exceeded, True otherwise.
        """
        return self._active_span_processor.force_flush(timeout_millis)
        
        

class OdigosTracer(Tracer):
    """See `opentelemetry.trace.Tracer`."""

    def __init__(
        self,
        sampler: sampling.Sampler,
        resource: Resource,
        span_processor: Union[
            SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor
        ],
        id_generator: IdGenerator,
        span_limits: SpanLimits,
        instrumentation_scope: InstrumentationScope,
    ) -> None:
        print("OdigosTracer.__init__", sampler, resource, span_processor, id_generator, span_limits, instrumentation_scope)
        self.sampler = sampler
        self.resource = resource
        self.span_processor = span_processor
        self.id_generator = id_generator
        self._span_limits = span_limits
        self._instrumentation_scope = instrumentation_scope

    @_agnosticcontextmanager  # pylint: disable=protected-access
    def start_as_current_span(
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Optional[Sequence[Link]] = (),
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[Span]:
        span = self.start_span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes,
            links=links,
            start_time=start_time,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        )
        with use_span(
            span,
            end_on_exit=end_on_exit,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
        ) as span:
            yield span

    def start_span(  # pylint: disable=too-many-locals
        self,
        name: str,
        context: Optional[context_api.Context] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Optional[Sequence[Link]] = (),
        start_time: Optional[int] = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> Span:

        parent_span_context = get_current_span(
            context
        ).get_span_context()

        if parent_span_context is not None and not isinstance(
            parent_span_context, SpanContext
        ):
            raise TypeError(
                "parent_span_context must be a SpanContext or None."
            )

        # is_valid determines root span
        if parent_span_context is None or not parent_span_context.is_valid:
            parent_span_context = None
            trace_id = self.id_generator.generate_trace_id()
        else:
            trace_id = parent_span_context.trace_id

        # The sampler decides whether to create a real or no-op span at the
        # time of span creation. No-op spans do not record events, and are not
        # exported.
        # The sampler may also add attributes to the newly-created span, e.g.
        # to include information about the sampling result.
        # The sampler may also modify the parent span context's tracestate
        sampling_result = self.sampler.should_sample(
            context, trace_id, name, kind, attributes, links
        )

        trace_flags = (
            TraceFlags(TraceFlags.SAMPLED)
            if sampling_result.decision.is_sampled()
            else TraceFlags(TraceFlags.DEFAULT)
        )
        span_context = SpanContext(
            trace_id,
            self.id_generator.generate_span_id(),
            is_remote=False,
            trace_flags=trace_flags,
            trace_state=sampling_result.trace_state,
        )

        # Only record if is_recording() is true
        if sampling_result.decision.is_recording():
            # pylint:disable=protected-access
            span = _Span(
                name=name,
                context=span_context,
                parent=parent_span_context,
                sampler=self.sampler,
                resource=self.resource,
                attributes=sampling_result.attributes.copy(),
                span_processor=self.span_processor,
                kind=kind,
                links=links,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
                limits=self._span_limits,
                instrumentation_scope=self._instrumentation_scope,
            )
            span.start(start_time=start_time, parent_context=context)
        else:
            span = NonRecordingSpan(context=span_context)
        return span

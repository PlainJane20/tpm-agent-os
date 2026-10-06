"""Optional OpenTelemetry spans. A silent no-op unless tracing is set up.

``opentelemetry-api`` is an optional dependency (``pip install -r
requirements-tracing.txt``) imported lazily, so the Python 3.9+ support of this
repo does not depend on it. Without the API, or with it but no SDK
TracerProvider configured, every span is a no-op and behaviour is unchanged.

Attributes must be identifiers, counts, enums, verdicts and durations only.
Never pass prompt text, briefs, charters, model output, or secrets.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

_PREFIX = "tpm."
_MAX_STR = 64

_provider: Any = None


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass

    def is_recording(self) -> bool:
        return False


def _load_trace() -> Any:
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    return trace


def configure(provider: Any) -> None:
    """Use `provider` for this repo's spans (None restores the global default)."""
    global _provider
    _provider = provider


def _clean(value: Any) -> Any:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    return str(value)[:_MAX_STR]


def set_attrs(s: Any, **attrs: Any) -> None:
    for key, value in attrs.items():
        if value is not None:
            s.set_attribute(key, _clean(value))


def record_error(s: Any, exc: BaseException) -> None:
    """Mark the span failed, recording only the exception *type* (messages may carry content)."""
    trace = _load_trace()
    if trace is None:
        return
    s.add_event("exception", {"exception.type": type(exc).__name__})
    s.set_status(trace.Status(trace.StatusCode.ERROR, type(exc).__name__))


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[Any]:
    trace = _load_trace()
    if trace is None:
        yield _NoopSpan()
        return
    tracer = (
        trace.get_tracer("tpm_agent_os", tracer_provider=_provider)
        if _provider is not None
        else trace.get_tracer("tpm_agent_os")
    )
    with tracer.start_as_current_span(
        _PREFIX + name, record_exception=False, set_status_on_exception=False
    ) as s:
        set_attrs(s, **attrs)
        try:
            yield s
        except BaseException as exc:
            record_error(s, exc)
            raise

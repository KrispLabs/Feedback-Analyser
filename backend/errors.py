"""The pipeline's expected failures, each mapped to one HTTP status in api.py.

These used to be LookupError/RuntimeError, caught by type in api.py -- but
KeyError is a LookupError, so a plain coding bug (a missing dict key) came back
to the client as a 404 "not found" instead of a 500. Anything that is NOT a
PipelineError is a bug and is reported as one.

ConfigError and UpstreamError also subclass RuntimeError, so older callers
that catch RuntimeError keep working."""


class PipelineError(Exception):
    status = 500


class NothingToAnalyse(PipelineError):
    """No reviews found, all were filtered out, or the requested week doesn't exist."""
    status = 404


class UpstreamError(PipelineError, RuntimeError):
    """An external service (SerpApi, Google Places, Groq) failed. Usually retriable."""
    status = 502


class ConfigError(PipelineError, RuntimeError):
    """The server is missing an API key or similar -- not the client's fault, not retriable."""
    status = 503

"""Error hierarchy. The CLI catches ErgaError and exits nonzero."""


class ErgaError(Exception):
    """Base class for all expected erga failures."""


class ConfigError(ErgaError):
    """Invalid or missing configuration or curation file."""


class FetchError(ErgaError):
    """An API fetch failed after retries; the run must abort."""

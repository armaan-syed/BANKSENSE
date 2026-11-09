"""Exceptions shared by the NLP modules.

They live in their own module so the encoder/similarity/summariser code can
raise the same types without importing `predictor` (which would be circular).
`backend.nlp.predictor` re-exports every class, so Person B's contract of
importing them from `predictor` still holds.
"""


class NLPError(Exception):
    """Base class for recoverable NLP errors."""


class InvalidInputError(NLPError):
    """The caller supplied blank or otherwise invalid text."""


class UnknownModelError(NLPError):
    """The caller requested a model name outside `SUPPORTED_MODELS`."""


class ArtifactUnavailableError(NLPError):
    """A model artifact or optional dependency could not be loaded."""

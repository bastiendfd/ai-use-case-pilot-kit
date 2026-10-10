"""Shared exception type for the scoring and triage modules."""

from __future__ import annotations


class InputError(ValueError):
    """Raised when an input file is invalid.

    ``errors`` holds one human-readable message per problem found.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))

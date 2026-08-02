"""Compatibility guard for the parent presidio-hardened-x402 release line."""

from __future__ import annotations

from importlib.metadata import version

from presidio_x402 import ArchTranslucencyAdapter, SLOPaymentBroker


def _minor_tuple(raw: str) -> tuple[int, int, int]:
    major, minor, patch = raw.split(".")[:3]
    return int(major), int(minor), int(patch)


def test_parent_library_is_v011_compatible():
    """The floor is 0.11.1 specifically, not 0.11.0.

    0.11.1 is the release in which ``PIIFilter`` stopped missing percent-encoded
    PII. ``screen_payment_metadata`` scans ``resource_url``, which is by
    construction a URL and so the most likely place for an address to arrive
    percent-encoded — an earlier parent hands agents a filter with a known
    bypass. Do not lower this floor.
    """
    parent_version = _minor_tuple(version("presidio-hardened-x402"))
    assert (0, 11, 1) <= parent_version < (0, 12, 0)


def test_parent_symbols_are_importable():
    assert ArchTranslucencyAdapter is not None
    assert SLOPaymentBroker is not None

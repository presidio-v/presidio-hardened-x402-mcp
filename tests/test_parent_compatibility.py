"""Compatibility guard for the parent presidio-hardened-x402 release line."""

from __future__ import annotations

from importlib.metadata import version

from presidio_x402 import ArchTranslucencyAdapter, SLOPaymentBroker


def _minor_tuple(raw: str) -> tuple[int, int, int]:
    major, minor, patch = raw.split(".")[:3]
    return int(major), int(minor), int(patch)


def test_parent_library_is_v07_compatible():
    parent_version = _minor_tuple(version("presidio-hardened-x402"))
    assert (0, 7, 0) <= parent_version < (0, 8, 0)


def test_parent_v07_symbols_are_importable():
    assert ArchTranslucencyAdapter is not None
    assert SLOPaymentBroker is not None

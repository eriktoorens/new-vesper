"""Rules engine: pure, deterministic functions given an injected RNG.

Source of truth is docs/design.md. This package must not import from
``dm``, ``state`` or anything that touches the network.
"""

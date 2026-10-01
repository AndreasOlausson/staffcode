"""Reference implementation of the Stackoda language."""

from .interpreter import execute, parse

__all__ = ["execute", "parse"]
__version__ = "0.0.2"

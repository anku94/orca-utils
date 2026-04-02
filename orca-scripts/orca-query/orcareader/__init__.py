"""ORCA trace reader package.

Provides modular interfaces for querying ORCA parquet traces:
- OrcaReader: High-level interface returning DataFrames
- OrcaIndex: Low-level interface returning file paths
- Interval, IntervalIndex, Range: Range query primitives
"""

from .index import OrcaIndex
from .interval import Interval, IntervalIndex, Range
from .reader import OrcaReader

__all__ = ["OrcaReader", "OrcaIndex", "Interval", "IntervalIndex", "Range"]

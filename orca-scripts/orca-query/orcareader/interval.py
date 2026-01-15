"""Interval types for range queries."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

Range = tuple[int, int]


@dataclass(frozen=True)
class Interval:
    """Half-open interval [start, end)."""

    start: int
    end: int

    def overlaps(self, other: Interval) -> bool:
        """Check if two intervals overlap."""
        return not (self.end <= other.start or other.end <= self.start)

    def __lt__(self, other: Interval) -> bool:
        """Sort by start, then end."""
        return (self.start, self.end) < (other.start, other.end)


@dataclass
class IntervalIndex:
    """Index mapping intervals to values, optimized for non-overlapping intervals.

    Maintains sorted list of (interval, value) pairs.
    Query uses binary search to find first potential match, then linear scan.
    """

    _entries: list[tuple[Interval, Path]]

    def __init__(self):
        self._entries = []

    def add(self, interval: Interval, value: Path) -> None:
        """Add an interval -> value mapping."""
        self._entries.append((interval, value))

    def finalize(self) -> None:
        """Sort entries by interval start. Call after all adds."""
        self._entries.sort(key=lambda x: x[0])

    def query(self, q: Interval) -> list[Path]:
        """Return all values whose intervals overlap with q."""
        if not self._entries:
            return []

        # Binary search for first entry that might overlap
        starts = [iv.start for iv, _ in self._entries]
        idx = bisect.bisect_left(starts, q.end)

        # Scan backwards from idx to find all overlaps
        result = []
        for i in range(idx - 1, -1, -1):
            iv, val = self._entries[i]
            if iv.end <= q.start:
                break
            if iv.overlaps(q):
                result.append(val)

        return result[::-1]

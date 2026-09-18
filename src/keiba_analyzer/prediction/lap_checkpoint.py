"""Elapsed clocks at real metre checkpoints, without collapsing missing laps.

The database adapter and external acquisition code are deliberately omitted.
Input rows contain an original one-based index, seconds and an endpoint in m.
"""

import math


def checkpoint_clock(rows, checkpoint_m, race_distance=None):
    """Interpolate inside a measured interval and retain its provenance.

    A starting 100 m is not doubled: the following interval contributes the
    remaining distance. Missing prefixes cannot be replaced with later laps.
    """
    distance = float(race_distance or 0)
    first = (distance % 200 or 200) if distance > 0 else None
    elapsed, previous, indices = 0.0, 0.0, []
    unavailable = {"seconds": None, "measurement_kind": "UNAVAILABLE",
                   "checkpoint_m": float(checkpoint_m)}
    for expected, (index, seconds, endpoint) in enumerate(rows, 1):
        if int(index) != expected or seconds is None:
            return unavailable
        seconds = float(seconds)
        inferred_end = first + 200 * (expected - 1) if first else None
        end = float(endpoint) if endpoint is not None else inferred_end
        if (not math.isfinite(seconds) or seconds <= 0 or end is None
                or not math.isfinite(end) or end <= previous
                or (inferred_end is not None and abs(end - inferred_end) > 1e-6)):
            return unavailable
        indices.append(int(index))
        if end >= checkpoint_m:
            fraction = (checkpoint_m - previous) / (end - previous)
            return {"seconds": elapsed + seconds * fraction,
                    "measurement_kind": "MEASURED" if end == checkpoint_m else "INTERPOLATED",
                    "checkpoint_m": float(checkpoint_m), "lap_indices": indices,
                    "containing_interval_m": [previous, end]}
        elapsed += seconds
        previous = end
    return unavailable

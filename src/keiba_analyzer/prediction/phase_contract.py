"""One pre-race phase timeline shared by display, demands and physical models.

Pure-function excerpt of the deployed architecture. Distances are metres;
this module does not estimate a new pace or change any ability score.
"""

import math


def _positive(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def late_phase_furlongs(path, distance=None):
    path = path or {}
    phase = path.get("phase_transition") or {}
    # The decided transition takes precedence over the old course prior.
    value = (_positive(phase.get("late_start_furlongs"))
             or _positive(path.get("late_phase_furlongs")) or 3.0)
    total = _positive(distance)
    return min(value, total / 200.0) if total else value


def canonical_pace_path(path, distance=None):
    result = dict(path or {})
    late = late_phase_furlongs(result, distance)
    phase = dict(result.get("phase_transition") or {})
    phase["late_start_furlongs"] = late
    result["phase_transition"] = phase
    result["late_phase_furlongs"] = late
    result["phase_contract_version"] = "SHARED_PRE_RACE_PHASE_METERS_V1"
    return result


def phase_distances(path, distance, start=0.0, end=None):
    """Clip the shared timeline to a travelled interval, not the whole race."""
    total = max(1.0, float(distance))
    finish = total if end is None else min(total, max(0.0, float(end)))
    start = min(finish, max(0.0, float(start)))
    late_start = total - 200.0 * late_phase_furlongs(path, total)
    formation_end = min(late_start, 600.0)
    bounds = (("formation", 0.0, formation_end),
              ("middle", formation_end, late_start),
              ("late", late_start, total))
    return {name: max(0.0, min(finish, right) - max(start, left))
            for name, left, right in bounds}

"""Core industrial-engineering calculations for ie-toolkit.

Every function validates its inputs and raises ValueError with a clear
message on invalid input. All results are plain dicts so the CLI can render
them as text or JSON.
"""
import math


def _clean(value):
    """Round away binary-float noise (e.g. 7.299999999999997 -> 7.3)."""
    return round(value, 10) if isinstance(value, float) else value


def takt_time(available_seconds, demand_units, shifts=1):
    """Takt time = total available time / demand.

    `available_seconds` is the net available production time per shift;
    total available time is available_seconds * shifts.
    """
    if available_seconds <= 0:
        raise ValueError("available time must be positive")
    if demand_units <= 0:
        raise ValueError("demand must be positive")
    if shifts < 1:
        raise ValueError("shifts must be at least 1")
    total_available = available_seconds * shifts
    takt = total_available / demand_units
    return {
        "available_seconds": available_seconds,
        "shifts": shifts,
        "total_available_seconds": total_available,
        "demand_units": demand_units,
        "takt_seconds_per_unit": _clean(takt),
        "units_per_hour": _clean(3600.0 / takt),
    }


def oee(planned_minutes, downtime_minutes, ideal_cycle_seconds,
        total_count, good_count):
    """Overall Equipment Effectiveness = Availability x Performance x Quality.

    Availability = (planned - downtime) / planned
    Performance  = (ideal_cycle_seconds * total_count) / runtime_seconds
    Quality      = good_count / total_count
    """
    if planned_minutes <= 0:
        raise ValueError("planned time must be positive")
    if downtime_minutes < 0:
        raise ValueError("downtime must not be negative")
    if downtime_minutes > planned_minutes:
        raise ValueError("downtime must not exceed planned time")
    runtime_minutes = planned_minutes - downtime_minutes
    if runtime_minutes <= 0:
        raise ValueError(
            "runtime is zero (downtime equals planned time); "
            "performance and OEE are undefined")
    if ideal_cycle_seconds <= 0:
        raise ValueError("ideal cycle time must be positive")
    if total_count <= 0:
        raise ValueError("total count must be positive")
    if good_count < 0:
        raise ValueError("good count must not be negative")
    if good_count > total_count:
        raise ValueError("good count must not exceed total count")
    runtime_seconds = runtime_minutes * 60.0
    availability = runtime_minutes / planned_minutes
    performance = (ideal_cycle_seconds * total_count) / runtime_seconds
    quality = good_count / total_count
    return {
        "planned_minutes": planned_minutes,
        "downtime_minutes": downtime_minutes,
        "runtime_minutes": runtime_minutes,
        "ideal_cycle_seconds": ideal_cycle_seconds,
        "total_count": total_count,
        "good_count": good_count,
        "availability": _clean(availability),
        "performance": _clean(performance),
        "quality": _clean(quality),
        "oee": _clean(availability * performance * quality),
    }


def parse_stations(text):
    """Parse a comma-separated list of station cycle times (seconds)."""
    if text is None or not str(text).strip():
        raise ValueError("no station times given (expected e.g. '12.5,10.2,15.0')")
    times = []
    for token in str(text).split(","):
        token = token.strip()
        if not token:
            raise ValueError(
                "malformed station list: empty entry in %r" % text)
        try:
            value = float(token)
        except ValueError:
            raise ValueError("malformed station time: %r" % token) from None
        if value <= 0:
            raise ValueError("station times must be positive, got %s" % value)
        times.append(value)
    return times


def line_balance(station_times, takt_seconds):
    """Line-balancing summary for a list of station cycle times."""
    if not station_times:
        raise ValueError("at least one station time is required")
    for t in station_times:
        if t <= 0:
            raise ValueError("station times must be positive, got %s" % t)
    if takt_seconds <= 0:
        raise ValueError("takt time must be positive")
    total = sum(station_times)
    n = len(station_times)
    bottleneck_time = max(station_times)
    bottleneck_station = station_times.index(bottleneck_time) + 1
    efficiency = total / (n * bottleneck_time)
    idle = n * bottleneck_time - total
    min_stations = math.ceil(total / takt_seconds)
    violators = [i + 1 for i, t in enumerate(station_times) if t > takt_seconds]
    return {
        "stations": list(station_times),
        "takt_seconds": takt_seconds,
        "total_work_content": _clean(total),
        "station_count": n,
        "bottleneck_station": bottleneck_station,
        "bottleneck_time": bottleneck_time,
        "line_efficiency": _clean(efficiency),
        "idle_time_per_cycle": _clean(idle),
        "min_stations": min_stations,
        "within_takt": not violators,
        "violators": violators,
    }


def capacity(cycle_seconds, available_seconds, yield_rate=1.0):
    """Capacity = floor(available / cycle); good units apply the yield."""
    if cycle_seconds <= 0:
        raise ValueError("cycle time must be positive")
    if available_seconds <= 0:
        raise ValueError("available time must be positive")
    if yield_rate <= 0 or yield_rate > 1:
        raise ValueError("yield must be in the range (0, 1]")
    gross = math.floor(available_seconds / cycle_seconds)
    good = math.floor(gross * yield_rate)
    return {
        "cycle_seconds": cycle_seconds,
        "available_seconds": available_seconds,
        "yield_rate": yield_rate,
        "gross_units": gross,
        "good_units": good,
    }

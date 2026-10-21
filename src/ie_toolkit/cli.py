"""Command-line interface for ie-toolkit (`ie-calc`).

Subcommands: takt, oee, balance, capacity. Every subcommand accepts
--json for machine-readable output; otherwise it prints the inputs,
the formula, and the result.
"""
import argparse
import json
import sys

from . import calc


def _fmt(value):
    return "%g" % value


def _pct(fraction):
    return "%.2f%%" % (fraction * 100.0)


def _emit(result, as_json, render_text):
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_text(result))
    return 0


def _cmd_takt(args):
    r = calc.takt_time(args.available, args.demand, args.shifts)
    r = {"command": "takt", **r}

    def text(r):
        return "\n".join([
            "Inputs:",
            "  Available time per shift: %s s" % r["available_seconds"],
            "  Shifts: %s" % r["shifts"],
            "  Total available time: %s s" % r["total_available_seconds"],
            "  Demand: %s units" % r["demand_units"],
            "Formula:",
            "  Takt time = total available time / demand = %s / %s"
            % (r["total_available_seconds"], r["demand_units"]),
            "Result:",
            "  Takt time: %.2f s/unit" % r["takt_seconds_per_unit"],
            "  Rate: %.2f units/hour" % r["units_per_hour"],
        ])

    return _emit(r, args.json, text)


def _cmd_oee(args):
    r = calc.oee(args.planned, args.downtime, args.ideal_cycle,
                 args.total, args.good)
    r = {"command": "oee",
         **r,
         "availability_pct": r["availability"] * 100.0,
         "performance_pct": r["performance"] * 100.0,
         "quality_pct": r["quality"] * 100.0,
         "oee_pct": r["oee"] * 100.0}

    def text(r):
        return "\n".join([
            "Inputs:",
            "  Planned time: %s min" % r["planned_minutes"],
            "  Downtime: %s min" % r["downtime_minutes"],
            "  Runtime: %s min" % r["runtime_minutes"],
            "  Ideal cycle: %s s" % r["ideal_cycle_seconds"],
            "  Total count: %s" % r["total_count"],
            "  Good count: %s" % r["good_count"],
            "Formula:",
            "  Availability = runtime / planned = %s / %s"
            % (r["runtime_minutes"], r["planned_minutes"]),
            "  Performance = (ideal cycle x total) / runtime in seconds"
            " = (%s x %s) / %s"
            % (r["ideal_cycle_seconds"], r["total_count"],
               r["runtime_minutes"] * 60.0),
            "  Quality = good / total = %s / %s"
            % (r["good_count"], r["total_count"]),
            "  OEE = Availability x Performance x Quality",
            "Result:",
            "  Availability: %s" % _pct(r["availability"]),
            "  Performance: %s" % _pct(r["performance"]),
            "  Quality: %s" % _pct(r["quality"]),
            "  OEE: %s" % _pct(r["oee"]),
        ])

    return _emit(r, args.json, text)


def _cmd_balance(args):
    stations = calc.parse_stations(args.stations)
    r = calc.line_balance(stations, args.takt)
    r = {"command": "balance",
         **r,
         "line_efficiency_pct": r["line_efficiency"] * 100.0}

    def text(r):
        lines = [
            "Inputs:",
            "  Station cycle times: %s s"
            % ", ".join("%g" % t for t in r["stations"]),
            "  Takt time: %s s" % _fmt(r["takt_seconds"]),
            "Formula:",
            "  Line efficiency = total work content / (stations x bottleneck)"
            " = %s / (%s x %s)"
            % (_fmt(r["total_work_content"]), r["station_count"],
               _fmt(r["bottleneck_time"])),
            "  Idle time per cycle = stations x bottleneck - total work content",
            "  Theoretical min stations = ceil(total work content / takt)",
            "Result:",
            "  Total work content: %s s" % _fmt(r["total_work_content"]),
            "  Bottleneck: station %s at %s s"
            % (r["bottleneck_station"], _fmt(r["bottleneck_time"])),
            "  Line efficiency: %s" % _pct(r["line_efficiency"]),
            "  Idle time per cycle: %s s" % _fmt(r["idle_time_per_cycle"]),
            "  Theoretical min stations: %s" % r["min_stations"],
        ]
        if r["within_takt"]:
            lines.append("  Within takt: yes (every station <= takt)")
        else:
            lines.append(
                "  Within takt: NO - stations over takt: %s"
                % ", ".join("station %s" % v for v in r["violators"]))
        return "\n".join(lines)

    return _emit(r, args.json, text)


def _cmd_capacity(args):
    r = calc.capacity(args.cycle, args.available, args.yield_rate)
    r = {"command": "capacity", **r}

    def text(r):
        return "\n".join([
            "Inputs:",
            "  Cycle time: %s s/unit" % r["cycle_seconds"],
            "  Available time: %s s" % r["available_seconds"],
            "  Yield: %s" % r["yield_rate"],
            "Formula:",
            "  Gross units = floor(available / cycle) = floor(%s / %s)"
            % (r["available_seconds"], r["cycle_seconds"]),
            "  Good units = floor(gross units x yield)",
            "Result:",
            "  Gross units: %s" % r["gross_units"],
            "  Good units: %s" % r["good_units"],
        ])

    return _emit(r, args.json, text)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ie-calc",
        description="Industrial-engineering calculators: "
                    "takt time, OEE, line balancing, capacity.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("takt", help="takt time from available time and demand")
    p.add_argument("--available", type=float, required=True,
                   help="net available production time per shift, seconds")
    p.add_argument("--demand", type=float, required=True,
                   help="required output over the period, units")
    p.add_argument("--shifts", type=int, default=1,
                   help="number of shifts (default: 1)")
    p.add_argument("--json", action="store_true",
                   help="machine-readable JSON output")
    p.set_defaults(func=_cmd_takt)

    p = sub.add_parser("oee", help="overall equipment effectiveness")
    p.add_argument("--planned", type=float, required=True,
                   help="planned production time, minutes")
    p.add_argument("--downtime", type=float, required=True,
                   help="unplanned + planned stops within planned time, minutes")
    p.add_argument("--ideal-cycle", type=float, required=True,
                   help="ideal cycle time, seconds per unit")
    p.add_argument("--total", type=int, required=True,
                   help="total units produced")
    p.add_argument("--good", type=int, required=True,
                   help="good (first-pass OK) units")
    p.add_argument("--json", action="store_true",
                   help="machine-readable JSON output")
    p.set_defaults(func=_cmd_oee)

    p = sub.add_parser("balance", help="line-balancing summary for station times")
    p.add_argument("--stations", required=True,
                   help="comma-separated station cycle times, seconds "
                        "(e.g. '12.5,10.2,15.0')")
    p.add_argument("--takt", type=float, required=True,
                   help="takt time, seconds")
    p.add_argument("--json", action="store_true",
                   help="machine-readable JSON output")
    p.set_defaults(func=_cmd_balance)

    p = sub.add_parser("capacity", help="gross and good capacity for a cycle time")
    p.add_argument("--cycle", type=float, required=True,
                   help="cycle time, seconds per unit")
    p.add_argument("--available", type=float, required=True,
                   help="available production time, seconds")
    p.add_argument("--yield", dest="yield_rate", type=float, default=1.0,
                   help="first-pass yield as a fraction in (0, 1] (default: 1.0)")
    p.add_argument("--json", action="store_true",
                   help="machine-readable JSON output")
    p.set_defaults(func=_cmd_capacity)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

import json

import pytest

from ie_toolkit.cli import main


def run_json(capsys, argv):
    code = main(argv + ["--json"])
    out = capsys.readouterr().out
    assert code == 0
    return json.loads(out)


# ---------- takt CLI ----------

def test_cli_takt_json(capsys):
    data = run_json(capsys, ["takt", "--available", "27000", "--demand", "450"])
    assert data["command"] == "takt"
    assert data["takt_seconds_per_unit"] == pytest.approx(60.0)
    assert data["units_per_hour"] == pytest.approx(60.0)
    assert data["demand_units"] == 450


def test_cli_takt_human_shows_formula_and_result(capsys):
    code = main(["takt", "--available", "27000", "--demand", "450"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Takt time = total available time / demand" in out
    assert "60.00 s/unit" in out
    assert "60.00 units/hour" in out


def test_cli_takt_zero_demand_errors(capsys):
    code = main(["takt", "--available", "27000", "--demand", "0"])
    err = capsys.readouterr().err
    assert code == 2
    assert "demand" in err


# ---------- oee CLI ----------

def test_cli_oee_json_structure(capsys):
    data = run_json(capsys, ["oee", "--planned", "480", "--downtime", "30",
                              "--ideal-cycle", "50", "--total", "500",
                              "--good", "480"])
    assert data["command"] == "oee"
    for key in ("availability", "performance", "quality", "oee",
                "availability_pct", "performance_pct", "quality_pct",
                "oee_pct", "runtime_minutes"):
        assert key in data
    assert data["availability_pct"] == pytest.approx(93.75)
    assert data["quality_pct"] == pytest.approx(96.0)
    assert data["oee_pct"] == pytest.approx(data["oee"] * 100)


def test_cli_oee_human_shows_all_percentages(capsys):
    code = main(["oee", "--planned", "480", "--downtime", "30",
                 "--ideal-cycle", "50", "--total", "500", "--good", "480"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Availability: 93.75%" in out
    assert "Quality: 96.00%" in out
    assert "OEE:" in out


def test_cli_oee_downtime_over_planned_errors(capsys):
    code = main(["oee", "--planned", "480", "--downtime", "500",
                 "--ideal-cycle", "50", "--total", "500", "--good", "480"])
    err = capsys.readouterr().err
    assert code == 2
    assert "downtime" in err


def test_cli_oee_good_over_total_errors(capsys):
    code = main(["oee", "--planned", "480", "--downtime", "30",
                 "--ideal-cycle", "50", "--total", "500", "--good", "600"])
    assert code == 2
    assert "good" in capsys.readouterr().err


# ---------- balance CLI ----------

def test_cli_balance_json(capsys):
    data = run_json(capsys, ["balance", "--stations", "12.5,10.2,15.0",
                             "--takt", "20"])
    assert data["command"] == "balance"
    assert data["total_work_content"] == pytest.approx(37.7)
    assert data["bottleneck_station"] == 3
    assert data["line_efficiency_pct"] == pytest.approx(83.78, abs=0.01)
    assert data["min_stations"] == 2
    assert data["within_takt"] is True


def test_cli_balance_human(capsys):
    code = main(["balance", "--stations", "12.5,10.2,15.0", "--takt", "20"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Line efficiency: 83.78%" in out
    assert "Bottleneck: station 3" in out


def test_cli_balance_malformed_stations_errors(capsys):
    code = main(["balance", "--stations", "12.5,abc", "--takt", "20"])
    err = capsys.readouterr().err
    assert code == 2
    assert "malformed" in err


def test_cli_balance_over_takt_flagged(capsys):
    code = main(["balance", "--stations", "25,10", "--takt", "20"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Within takt: NO" in out
    assert "station 1" in out


# ---------- capacity CLI ----------

def test_cli_capacity_json(capsys):
    data = run_json(capsys, ["capacity", "--cycle", "30",
                             "--available", "27000", "--yield", "0.98"])
    assert data["command"] == "capacity"
    assert data["gross_units"] == 900
    assert data["good_units"] == 882


def test_cli_capacity_negative_cycle_errors(capsys):
    code = main(["capacity", "--cycle", "-30", "--available", "27000"])
    err = capsys.readouterr().err
    assert code == 2
    assert "cycle" in err

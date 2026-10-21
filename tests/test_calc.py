import math

import pytest

from ie_toolkit import capacity, line_balance, oee, takt_time
from ie_toolkit.calc import parse_stations


# ---------- takt ----------

def test_takt_worked_example():
    r = takt_time(available_seconds=27000, demand_units=450)
    assert r["takt_seconds_per_unit"] == pytest.approx(60.0)
    assert r["units_per_hour"] == pytest.approx(60.0)
    assert r["total_available_seconds"] == 27000


def test_takt_multiple_shifts():
    r = takt_time(available_seconds=27000, demand_units=900, shifts=2)
    assert r["total_available_seconds"] == 54000
    assert r["takt_seconds_per_unit"] == pytest.approx(60.0)


def test_takt_zero_demand_rejected():
    with pytest.raises(ValueError, match="demand"):
        takt_time(27000, 0)


def test_takt_negative_available_rejected():
    with pytest.raises(ValueError, match="available"):
        takt_time(-100, 450)


def test_takt_zero_shifts_rejected():
    with pytest.raises(ValueError, match="shifts"):
        takt_time(27000, 450, shifts=0)


# ---------- oee ----------

def test_oee_reference_example():
    # planned 480, downtime 30 -> runtime 450 min = 27000 s
    # A = 450/480 = 0.9375 ; P = 50*500/27000 = 0.925925... ; Q = 480/500 = 0.96
    r = oee(planned_minutes=480, downtime_minutes=30, ideal_cycle_seconds=50,
            total_count=500, good_count=480)
    assert r["runtime_minutes"] == 450
    assert r["availability"] == pytest.approx(0.9375)
    assert r["performance"] == pytest.approx(25000 / 27000)
    assert r["quality"] == pytest.approx(0.96)
    assert r["oee"] == pytest.approx(0.9375 * (25000 / 27000) * 0.96)


def test_oee_perfect_line_is_100_percent():
    r = oee(planned_minutes=60, downtime_minutes=0, ideal_cycle_seconds=60,
            total_count=60, good_count=60)
    assert r["oee"] == pytest.approx(1.0)


def test_oee_downtime_over_planned_rejected():
    with pytest.raises(ValueError, match="downtime"):
        oee(480, 481, 50, 500, 480)


def test_oee_good_over_total_rejected():
    with pytest.raises(ValueError, match="good"):
        oee(480, 30, 50, 500, 501)


def test_oee_zero_runtime_rejected():
    with pytest.raises(ValueError, match="runtime is zero"):
        oee(480, 480, 50, 500, 480)


def test_oee_zero_total_rejected():
    with pytest.raises(ValueError, match="total count"):
        oee(480, 30, 50, 0, 0)


# ---------- balance ----------

def test_balance_worked_example():
    r = line_balance([12.5, 10.2, 15.0], takt_seconds=20)
    assert r["total_work_content"] == pytest.approx(37.7)
    assert r["bottleneck_station"] == 3
    assert r["bottleneck_time"] == pytest.approx(15.0)
    assert r["line_efficiency"] == pytest.approx(37.7 / 45.0)
    assert r["line_efficiency"] * 100 == pytest.approx(83.78, abs=0.01)
    assert r["idle_time_per_cycle"] == pytest.approx(45.0 - 37.7)
    assert r["min_stations"] == 2
    assert r["within_takt"] is True
    assert r["violators"] == []


def test_balance_violators_listed():
    r = line_balance([25.0, 10.0], takt_seconds=20)
    assert r["within_takt"] is False
    assert r["violators"] == [1]
    assert r["min_stations"] == math.ceil(35.0 / 20)


def test_balance_single_station():
    r = line_balance([18.0], takt_seconds=20)
    assert r["line_efficiency"] == pytest.approx(1.0)
    assert r["idle_time_per_cycle"] == pytest.approx(0.0)


def test_parse_stations_ok():
    assert parse_stations("12.5, 10.2,15.0") == [12.5, 10.2, 15.0]


@pytest.mark.parametrize("bad", ["", "abc", "12,,10", "12.5,xyz", ","])
def test_parse_stations_malformed_rejected(bad):
    with pytest.raises(ValueError):
        parse_stations(bad)


def test_balance_negative_station_rejected():
    with pytest.raises(ValueError, match="positive"):
        parse_stations("12.5,-3,15.0")


def test_balance_nonpositive_takt_rejected():
    with pytest.raises(ValueError, match="takt"):
        line_balance([10.0, 12.0], takt_seconds=0)


# ---------- capacity ----------

def test_capacity_basic_with_yield():
    r = capacity(cycle_seconds=30, available_seconds=27000, yield_rate=0.98)
    assert r["gross_units"] == 900
    assert r["good_units"] == 882  # floor(900 * 0.98)


def test_capacity_default_yield_is_one():
    r = capacity(cycle_seconds=30, available_seconds=27000)
    assert r["yield_rate"] == 1.0
    assert r["good_units"] == r["gross_units"] == 900


def test_capacity_floors_partial_units():
    r = capacity(cycle_seconds=7, available_seconds=100)
    assert r["gross_units"] == 14


def test_capacity_zero_cycle_rejected():
    with pytest.raises(ValueError, match="cycle"):
        capacity(0, 27000)


def test_capacity_zero_available_rejected():
    with pytest.raises(ValueError, match="available"):
        capacity(30, 0)


@pytest.mark.parametrize("bad_yield", [0, -0.5, 1.5])
def test_capacity_bad_yield_rejected(bad_yield):
    with pytest.raises(ValueError, match="yield"):
        capacity(30, 27000, yield_rate=bad_yield)

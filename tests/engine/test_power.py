"""Hand arithmetic for explicitly synthetic panel and electrical bus profiles."""
import pytest
from soma.power import fixed_panel_power, integrate_battery, AU_M


def profile(**changes):
    return dict(capacity_wh=100, initial_energy_wh=50, reserve_wh=10,
                max_charge_w=20, max_discharge_w=30,
                charge_efficiency=0.8, discharge_efficiency=0.5, **changes)


def battery(**changes):
    p=profile()
    p.update(changes)
    return p


def bins(*powers):
    return [{"start_utc":f"2026-11-14T{i:02}:00:00Z", "end_utc":f"2026-11-14T{i+1:02}:00:00Z",
             "generation_w": generation, "incremental_load_w":load} for i,(generation,load) in enumerate(powers)]


def test_panel_projection_distance_and_unknown():
    panel=dict(kind="fixed",area_m2=2,normal_local_enu=[0,0,1],efficiency=0.2,
               lumped_derating=0.8,irradiance_at_1au_w_m2=1000)
    assert fixed_panel_power(panel,[0,0,AU_M],0.5)["generated_power_w"] == pytest.approx(160)
    assert fixed_panel_power(panel,[0,0,2*AU_M],1)["generated_power_w"] == pytest.approx(80)
    assert fixed_panel_power(panel,[0,0,AU_M],None)["generated_power_w"] is None
    panel["normal_local_enu"]=[0,0,2]
    with pytest.raises(ValueError,match="unit"):
        fixed_panel_power(panel,[0,0,AU_M],1)
    panel["kind"]="tracker"
    with pytest.raises(ValueError,match="tracker"):
        fixed_panel_power(panel,[0,0,AU_M],1)


def test_efficiency_branches_and_shadow_drain():
    result=integrate_battery(battery(),bins((15,0),(0,0)),base_load_w=5)
    assert result["samples"][1]["stored_energy_wh"] == 58
    assert result["samples"][2]["stored_energy_wh"] == 48
    for row in result["intervals"]:
        assert row["charge_bus_w"]*row["discharge_bus_w"] == 0


def test_saturation_and_charge_power_spill():
    result=integrate_battery(battery(initial_energy_wh=99),bins((105,0)),base_load_w=5)
    row=result["intervals"][0]
    assert row["end_energy_wh"] == 100
    assert row["spilled_bus_energy_wh"] == pytest.approx(98.75)
    assert result["status"] == "satisfied_under_piecewise_constant_assumptions"


def test_instantaneous_power_fails_despite_sufficient_energy():
    result=integrate_battery(battery(initial_energy_wh=100),bins((0,30)),base_load_w=5)
    assert result["samples"][-1]["stored_energy_wh"] == 30
    assert result["violations"][0]["reason"] == "instantaneous_discharge_power_exceeded"


def test_internal_split_retains_reserve_violation_despite_final_recovery():
    result=integrate_battery(battery(initial_energy_wh=15),bins((0,0),(25,0)),base_load_w=5)
    assert result["samples"][-1]["stored_energy_wh"] == 21
    assert any(v["reason"] == "reserve_violation" for v in result["violations"])
    assert result["status"] == "violated"


def test_unknown_generation_never_becomes_zero():
    result=integrate_battery(battery(),bins((None,0),(10,0)),base_load_w=5)
    assert result["status"] == "unknown"
    assert all(s["stored_energy_wh"] is None for s in result["samples"][1:])


def test_reject_gap_zero_base_and_varying_bin():
    with pytest.raises(ValueError):
        integrate_battery(battery(),bins((1,0)),base_load_w=0)
    rows=bins((1,0),(1,0)); rows[1]["start_utc"]="2026-11-14T01:01:00Z"
    with pytest.raises(ValueError,match="contiguous"):
        integrate_battery(battery(),rows,base_load_w=5)
    rows=bins((1,0)); rows[0]["power_model"]="linear"
    with pytest.raises(ValueError,match="split"):
        integrate_battery(battery(),rows,base_load_w=5)

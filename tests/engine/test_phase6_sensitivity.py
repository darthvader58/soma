"""Sensitivity evidence must expose actual model changes and replay feasibility."""
from soma.verification.sensitivity import run_sensitivities


def test_phase6_synthetic_sensitivity():
    report = run_sensitivities()
    cases = {row['case_id']:row for row in report['schedule_cases']}
    assert cases['baseline']['delivered_bytes'] == 104857600
    for name in ('baseline', 'scheduler-5s'):
        assert cases[name]['status'] == 'feasible_under_assumptions'
        assert cases[name]['replay']['passed']
        assert cases[name]['replay']['delivered_bytes'] == 104857600
    for name in ('battery-low', 'rate-half', 'service-off', 'scheduler-30s'):
        assert cases[name]['status'] == 'infeasible_in_model'
        assert cases[name]['solver_status'] == 'proven_infeasible_discretized_model'
        assert cases[name]['replay'] is None
        assert cases[name]['final_energy_wh'] is None
    assert cases['rate-half']['scenario_sha256'] == cases['baseline']['scenario_sha256']
    assert cases['rate-half']['analysis_sha256'] != cases['baseline']['analysis_sha256']
    assert cases['service-off']['scenario_sha256'] != cases['baseline']['scenario_sha256']
    terrain = report['terrain_segment_cases']
    assert [r['visibility']['status'] for r in terrain] == ['clear','unknown','clear','unknown']
    assert 'missing_terrain' in terrain[-1]['visibility']['quality_flags']
    assert terrain[-1]['visibility']['minimum_sampled_clearance_m'] is None
    assert report['unresolved_differences']

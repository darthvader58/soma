"""Bounded Phase 6 experiments using declared synthetic inputs and engine replay."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from soma.engine import plan_run
from soma.schedule.replay import replay_schedule
from soma.terrain.dem import SyntheticDEM
from soma.terrain.horizons import finite_segment_visibility
from soma.time import parse_utc
from soma.validation import scenario_sha256


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def run_sensitivities(root=None, *, time_limit_s=20):
    """Return serializable evidence; never mutate fixtures or write artifacts.

    Rates, calendars, dark generation and terrain are synthetic assumptions.
    Vary one control at a time. Geometry experiments are separate from schedule
    experiments: their sampled segments do not predict interval-wide contacts.
    """
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    directory = root / 'fixtures' / 'synthetic-relay'
    baseline = json.loads((directory / 'scenario.json').read_text())
    contacts = json.loads((directory / 'contacts.json').read_text())
    records = []
    cases = [('baseline', 'baseline', None), ('battery-low', 'initial_energy_wh', 11),
             ('rate-half', 'payload_rate_multiplier', .5), ('service-off', 'relay_service_available', False),
             ('scheduler-5s', 'scheduler_bin_s', 5), ('scheduler-30s', 'scheduler_bin_s', 30)]
    for name, control, value in cases:
        scenario, edges = deepcopy(baseline), deepcopy(contacts)
        bin_s = value if control == 'scheduler_bin_s' else 10
        if control == 'initial_energy_wh':
            scenario['profiles']['hardware'][0]['battery']['initial_energy_wh'] = value
        elif control == 'payload_rate_multiplier':
            for edge in edges:
                edge['payload_rate_bps'] *= value
                edge['available_capacity_bits'] = int(edge['available_capacity_bits'] * value)
        elif control == 'relay_service_available':
            scenario['profiles']['relays'][0]['service']['windows'] = []
        generation = [dict(scenario['analysis_horizon'], generation_w=0, power_model='piecewise_constant')]
        analysis = dict(format_version='0.4.0', scenario_sha256=scenario_sha256(scenario), contacts=edges,
                        generation_bins=generation, contacts_complete=True, generation_complete=True,
                        assumptions=['SYNTHETIC fixture contacts; zero generation over the whole horizon; light time disabled for arithmetic.'],
                        warnings=['No numerical lunar terrain or ephemeris; no mission prediction.'],
                        provenance={'input_class':'synthetic', 'experiment':'phase6-one-control-sensitivity-v1'})
        options = dict(bin_s=bin_s, chunk_bytes=16777216, time_limit_s=time_limit_s)
        run = plan_run(scenario, analysis_inputs=analysis, options=options)
        result = run['result']
        replay = None
        if result['status'] == 'feasible_under_assumptions':
            replay = replay_schedule(scenario, edges, result['allocations'], generation)
            if not replay['passed']:
                raise RuntimeError(f'{name}: independent replay rejected feasible result: {replay["errors"]}')
        history = replay['energy_history'] if replay else []
        records.append(dict(case_id=name, changed_control=control, changed_value=value,
                            scenario_sha256=scenario_sha256(scenario), analysis_sha256=_hash(analysis),
                            settings=options, software=run['details']['software'], scenario=scenario, analysis_inputs=analysis,
                            status=result['status'], solver_status=result['solver_status'],
                            delivered_bytes=result['delivered_bytes'], completion_utc=result['final_byte_arrival_utc'],
                            final_energy_wh=history[-1]['stored_energy_wh'] if history else None,
                            minimum_energy_wh=min(r['stored_energy_wh'] for r in history) if history else None,
                            replay=replay, result=result,
                            resolution={'scheduler_bin_s':bin_s, 'geometry_time_sampling_s':None,
                                        'dem_pixel_size_m':None, 'generation':'declared_constant_zero'}))
    reference = records[0]
    for record in records:
        record['changes_from_baseline'] = {
            'status_changed':record['status'] != reference['status'],
            'delivered_bytes':None if record['delivered_bytes'] is None else record['delivered_bytes']-reference['delivered_bytes'],
            'completion_s':(parse_utc(record['completion_utc'])-parse_utc(reference['completion_utc'])).total_seconds() if record['completion_utc'] and reference['completion_utc'] else None,
            'final_energy_wh':record['final_energy_wh']-reference['final_energy_wh'] if record['final_energy_wh'] is not None and reference['final_energy_wh'] is not None else None,
        }
    terrain = []
    radius = baseline['lander']['reference_radius_m']
    for missing, margin, step in [(False,0,100), (False,20,100), (False,0,50), (True,0,100)]:
        identifier = 'phase6-flat-missing-v1' if missing else 'phase6-flat-zero-v1'
        dem = SyntheticDEM(lambda lat, lon: None if missing else 0, identifier=identifier)
        settings = dict(observer_m=[radius+10,0,0], target_m=[radius+10,1000,0], frame='MOON_ME_DE421',
                        step_m=step, clearance_m=margin, body_radius_m=radius-100)
        visibility = finite_segment_visibility(dem, **settings)
        terrain.append(dict(settings=settings, dem_source_hashes=list(dem.source_hashes), input_sha256=_hash([identifier,settings]),
                            visibility=asdict(visibility), input_class='synthetic',
                            dem_pixel_size_m=None, geometry_time_sampling_s=None))
    return dict(artifact_type='soma_phase6_sensitivity', artifact_version='1.0.0',
                schedule_cases=records, terrain_segment_cases=terrain,
                reproduce_command='.venv/bin/python -m soma.verification.sensitivity',
                unresolved_differences=[
                    'All experiments are synthetic software verification; rates and service do not establish RF closure or network access.',
                    'Terrain margin experiments classify one static finite segment only; no terrain perturbation or physical DEM resolution study was performed.',
                    'Scheduler bin changes test conservative discretization only; they do not refine ephemeris sampling, solar disk sampling or numerical DEM pixels.',
                    'Coarse scheduler bins may eliminate a schedule by upward whole-chunk occupancy rounding; this is not physical infeasibility.',
                    'Two segment step sizes and three scheduler bin sizes do not establish physical convergence or a probability of success.',
                    'Infeasible runs have no selected schedule; their energy and completion are unknown, not zero.',
                ])


def main():
    print(json.dumps(run_sensitivities(), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

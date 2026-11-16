"""Recompute mission controls with archived DE421/LOLA physical inputs."""

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import zipfile

from soma.engine import plan_run
from soma.exports import create_run_package, json_bytes
from soma.schedule.replay import replay_schedule
from soma.validation import scenario_sha256
from soma.verification.exports import verify_run_package

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'fixtures/physical-south-pole/relay-later/run.zip'


def build(output=None):
    output = Path(output) if output is not None else ROOT / 'fixtures/demo-constraints'
    with zipfile.ZipFile(SOURCE) as archive:
        baseline = {'scenario':json.loads(archive.read('scenario.json')),
            'analysis_inputs':json.loads(archive.read('analysis-inputs.json')),
            'result':json.loads(archive.read('result.json')),
            'settings':json.loads(archive.read('run-manifest.json'))['details']['scheduler_options']}
    baseline_verification = verify_run_package(SOURCE)
    if not baseline_verification['passed']:
        raise RuntimeError('Archived physical baseline package failed verification')
    baseline_replay = replay_schedule(baseline['scenario'], baseline['analysis_inputs']['contacts'],
        baseline['result']['allocations'], baseline['analysis_inputs']['generation_bins'])
    if not baseline_replay['passed']:
        raise RuntimeError('Archived baseline schedule no longer passes independent replay')
    records = []
    for name in ('battery-low', 'service-off'):
        scenario, analysis = deepcopy(baseline['scenario']), deepcopy(baseline['analysis_inputs'])
        if name == 'battery-low':
            scenario['profiles']['hardware'][0]['battery']['initial_energy_wh'] = 11
            control, value = 'initial_energy_wh', 11
        else:
            scenario['profiles']['relays'][0]['service']['windows'] = []
            control, value = 'relay_service_available', False
        analysis['scenario_sha256'] = scenario_sha256(scenario)
        if analysis.get('environment'):
            analysis['environment']['scenario_sha256'] = scenario_sha256(scenario)
        run = plan_run(scenario, analysis_inputs=analysis, options=baseline['settings'])
        result = run['result']
        if (result['status'], result['solver_status']) != ('unknown', 'unresolved'):
            raise RuntimeError(f'{name}: recomputation must preserve unresolved incomplete contact coverage')
        if result['allocations'] or result['final_byte_arrival_utc'] is not None:
            raise RuntimeError('An unresolved result must not invent a selected schedule or completion')
        counterfactual = replay_schedule(scenario, analysis['contacts'],
            baseline['result']['allocations'], analysis['generation_bins'])
        if counterfactual['passed']:
            raise RuntimeError('Changed constraint did not invalidate the baseline witness schedule')
        package = create_run_package(run)
        verification = verify_run_package(package)
        if not verification['passed']:
            raise RuntimeError(f'{name}: package verification failed: {verification["errors"]}')
        directory = output / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'run.zip').write_bytes(package)
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            for member in archive.namelist():
                if '/' in member or '\\' in member:
                    raise RuntimeError('Unexpected export member path')
                (directory / member).write_bytes(archive.read(member))
        (directory / 'run.json').write_bytes(json_bytes(run))
        (directory / 'verification.json').write_bytes(json_bytes(verification))
        (directory / 'baseline-counterfactual-replay.json').write_bytes(json_bytes(counterfactual))
        if name == 'battery-low':
            explanation = ('Baseline rejected: battery reserve; full delivery remains unresolved under incomplete contact coverage. '
                'Only initial battery energy changes from 80 Wh to 11 Wh, with a 10 Wh reserve. '
                'The archived November 30 DE421/LOLA physical analysis has zero modeled generation. '
                'The 5 W base load over six hours needs 30 Wh of delivered electricity, or '
                '33.333333333333336 Wh removed at 0.9 discharge efficiency, above the 1 Wh initial reserve margin. '
                'The engine nevertheless conservatively retains unknown/unresolved because contact coverage is incomplete.')
        else:
            explanation = ('The baseline schedule cannot use unavailable relay service; full routing remains unresolved. '
                'Only the hypothetical lunar relay service windows change to an empty list. '
                'The same November 30 DE421/LOLA analysis contains no known usable direct contacts. '
                'Unknown opportunities remain unknown, so failure on known contacts is not proof of full-network infeasibility.')
        records.append({'case_id':name, 'scenario_id':scenario['scenario_id'],
            'scenario_sha256':result['scenario_sha256'], 'status':result['status'],
            'solver_status':result['solver_status'], 'model_fidelity':result['model_fidelity'],
            'delivered_bytes':result['delivered_bytes'], 'final_byte_arrival_utc':result['final_byte_arrival_utc'],
            'changed_control':control, 'changed_value':value,
            'limiting_reason':result['provenance']['reason'], 'constraint_explanation':explanation,
            'input_class':'published_geometry_with_assumed_mission',
            'labels':['Hypothetical planned mission, not a flown operation', 'Published LOLA terrain and DE421 ephemerides',
                'Assumed net radio rates, hardware, pointing and station service',
                'Synthetic two-body lunar relay trajectory; not an operational relay',
                'Archived modeled zero generation on November 30',
                'Incomplete contact coverage; unknown is not proven infeasible'],
            'export_verified':True, 'baseline_counterfactual_rejected':True,
            'baseline_counterfactual_errors':counterfactual['errors'],
            'run_ref':f'{name}/run.json', 'package_ref':f'{name}/run.zip',
            'package_sha256':hashlib.sha256(package).hexdigest(),
            'files':{str(p.relative_to(output)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'size_bytes':p.stat().st_size} for p in sorted(directory.iterdir()) if p.is_file()}})
    report = {'artifact_type':'physical_mission_constraint_demonstration', 'version':'1.0.0',
        'source_ref':str(SOURCE.relative_to(ROOT)), 'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'generator_ref':str(Path(__file__).resolve().relative_to(ROOT)),
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'reproduce_command':'.venv/bin/python scripts/build-demo-constraints.py',
        'method':'One mission control changed from the archived physical relay case; numerical analysis and scheduler options preserved, scenario hash bindings refreshed; native outputs unedited; packages independently verified.',
        'baseline_replay_passed':True, 'cases':records,
        'limitations':['Published DE421/LOLA physical inputs support a hypothetical mission with assumed rates, hardware and service and a synthetic two-body relay.',
            'Counterfactual replay rejects the known baseline schedule; incomplete contact coverage prevents a full-network infeasibility conclusion.',
            'No selected schedule exists for unresolved cases; absent energy histories and completion remain unknown.',
            'Exact numerical outcomes are reproducible; ZIP bytes also record current software hashes and versions.']}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'demonstration.json').write_bytes(json_bytes(report))
    return report


if __name__ == '__main__':
    for row in build()['cases']:
        print(row['case_id'], row['status'], row['scenario_sha256'])

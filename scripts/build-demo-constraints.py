"""Recompute two exact archived synthetic controls; never modify native results."""

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
SOURCE = ROOT / 'fixtures/phase-6/sensitivity.json'


def build(output=None):
    output = Path(output) if output is not None else ROOT / 'fixtures/demo-constraints'
    archived = json.loads(SOURCE.read_text())
    cases = {row['case_id']: row for row in archived['schedule_cases']}
    baseline = cases['baseline']
    baseline_replay = replay_schedule(baseline['scenario'], baseline['analysis_inputs']['contacts'],
        baseline['result']['allocations'], baseline['analysis_inputs']['generation_bins'])
    if not baseline_replay['passed']:
        raise RuntimeError('Archived baseline schedule no longer passes independent replay')
    records = []
    for name in ('battery-low', 'service-off'):
        source = cases[name]
        scenario, analysis = deepcopy(source['scenario']), deepcopy(source['analysis_inputs'])
        if scenario_sha256(scenario) != source['scenario_sha256']:
            raise RuntimeError('Archived scenario binding changed')
        run = plan_run(scenario, analysis_inputs=analysis, options=source['settings'])
        result = run['result']
        if (result['status'], result['solver_status']) != ('infeasible_in_model', 'proven_infeasible_discretized_model'):
            raise RuntimeError(f'{name}: recomputation does not prove the archived infeasible outcome')
        if result['allocations'] or result['final_byte_arrival_utc'] is not None:
            raise RuntimeError('An infeasible result must not invent a selected schedule or completion')
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
        hardware = scenario['profiles']['hardware'][0]
        if name == 'battery-low':
            explanation = ('Only initial battery energy changes from 80 Wh to 11 Wh, with a 10 Wh reserve. '
                'Synthetic generation is zero. The 5 W base load alone over 75 minutes needs 6.25 Wh '
                'of delivered electricity, or 6.944444444444445 Wh removed at 0.9 discharge efficiency. '
                'The 1 Wh initial margin above reserve cannot sustain even that base load, before radio use.')
        else:
            explanation = ('Only the synthetic lunar relay service windows change to an empty list. '
                'The relay cannot receive or forward during any interval. The remaining direct contact '
                'can carry 307200000 bits, less than the 838860800-bit (100 MiB) file. '
                'Visibility and assumed rate do not supply missing service permission.')
        records.append({'case_id':name, 'scenario_id':scenario['scenario_id'],
            'scenario_sha256':result['scenario_sha256'], 'status':result['status'],
            'solver_status':result['solver_status'], 'model_fidelity':result['model_fidelity'],
            'delivered_bytes':result['delivered_bytes'], 'final_byte_arrival_utc':result['final_byte_arrival_utc'],
            'changed_control':source['changed_control'], 'changed_value':source['changed_value'],
            'limiting_reason':result['provenance']['reason'], 'constraint_explanation':explanation,
            'input_class':'synthetic', 'labels':['Synthetic contact geometry and service', 'Assumed net radio rates',
                'Declared zero generation', 'Light time disabled for arithmetic', 'No numerical terrain or ephemeris',
                'No spacecraft trajectory; map states remain unknown', 'Not a lunar mission prediction'],
            'export_verified':True, 'baseline_counterfactual_rejected':True,
            'baseline_counterfactual_errors':counterfactual['errors'],
            'run_ref':f'{name}/run.json', 'package_ref':f'{name}/run.zip',
            'package_sha256':hashlib.sha256(package).hexdigest(),
            'files':{str(p.relative_to(output)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'size_bytes':p.stat().st_size} for p in sorted(directory.iterdir()) if p.is_file()}})
    report = {'artifact_type':'synthetic_constraint_demonstration', 'version':'1.0.0',
        'source_ref':str(SOURCE.relative_to(ROOT)), 'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'generator_ref':str(Path(__file__).resolve().relative_to(ROOT)),
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'reproduce_command':'.venv/bin/python scripts/build-demo-constraints.py',
        'method':'Exact archived scenarios, analysis inputs and scheduler options passed to plan_run; native outputs unedited; exported packages independently verified.',
        'baseline_replay_passed':True, 'cases':records,
        'limitations':['All geometry, rates, service and power inputs are synthetic software-test assumptions.',
            'Counterfactual replay rejects one known baseline schedule; MILP proof establishes infeasibility in the stated discretized model.',
            'No selected infeasible schedule exists; absent energy histories and completion remain unknown.',
            'Exact numerical outcomes are reproducible; ZIP bytes also record current software hashes and versions.']}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'demonstration.json').write_bytes(json_bytes(report))
    return report


if __name__ == '__main__':
    for row in build()['cases']:
        print(row['case_id'], row['status'], row['scenario_sha256'])

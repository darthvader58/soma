"""Check Phase 6's recorded engineering evidence independently of deployment."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from soma.geometry.registration import load_renderer_registration
from soma.schedule.replay import replay_schedule
from soma.time import parse_utc
from soma.validation import scenario_sha256, validate_document
from soma.verification.exports import verify_export


def verify_phase6(root=None):
    """Recheck archived results and review receipts; never grant hosting rights."""
    root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    report = {'artifact_type':'soma_phase6_completion', 'version':'1.0.0',
              'scope':'local_integrated_verification_under_declared_assumptions',
              'phase6_complete':False, 'checks':[], 'errors':[],
              'public_deployment_authorized':False, 'phase7_started':False}

    def check(name, passed, detail='Recorded evidence does not satisfy the check'):
        report['checks'].append({'name':name, 'passed':bool(passed)})
        if not passed:
            report['errors'].append({'check':name, 'reason':detail})

    def read(name):
        return json.loads((root/name).read_text())

    def archive(name):
        path = root/name
        verified = verify_export(path)
        check('export:'+name, verified['passed'], str(verified['errors']))
        with zipfile.ZipFile(path) as source:
            return tuple(json.loads(source.read(n)) for n in
                         ('scenario.json','result.json','display-data.json'))

    try:
        evidence = read('data/phase6-evidence.manifest.json')
        files = evidence['files']
        check('declared_completion_scope', evidence['completion_scope'] == report['scope'])
        check('distinct_evidence_bindings', len({f['path'] for f in files}) == len(files))
        required_bindings = {
            'fixtures/phase-6/demo/'+name+'/run.zip'
            for name in ('direct-ready','direct-later','relay-later')
        } | {'fixtures/phase-6/manual-live/run.zip', 'fixtures/phase-6/sensitivity.json',
             'fixtures/phase-6/independent-review.json',
             'soma/docs/phase-6/source-and-license-audit.md',
             'web/docs/phase-6-independent-review.json',
             'soma/verification/completion.py'}
        check('required_evidence_bindings', required_bindings <= {f['path'] for f in files})
        for binding in files:
            path = (root/binding['path']).resolve()
            check('evidence:'+binding['path'], path.is_relative_to(root) and path.is_file()
                  and path.stat().st_size == binding['size_bytes']
                  and hashlib.sha256(path.read_bytes()).hexdigest() == binding['sha256'])

        cases = [archive('fixtures/phase-6/demo/'+name+'/run.zip')
                 for name in ('direct-ready','direct-later','relay-later')]
        scenarios, results, displays = zip(*cases)
        fixed = ('data_volume','hardware_profile_ref','lander','deadline_utc','analysis_horizon',
                 'profiles','relay_refs','station_refs','rate_method','pointing_assumption',
                 'service_assumption_label')
        check('controlled_task_unchanged', all(scenarios[0][key] == scenario[key]
              for scenario in scenarios[1:] for key in fixed))
        check('controlled_readiness_change',
              parse_utc(scenarios[0]['data_ready_utc']) < parse_utc(scenarios[1]['data_ready_utc'])
              and scenarios[1]['data_ready_utc'] == scenarios[2]['data_ready_utc'])
        check('configured_route_enablement',
              all(s['route_families'] == ['direct_to_earth'] for s in scenarios[:2])
              and set(scenarios[2]['route_families']) == {'direct_to_earth','single_lunar_relay'}
              and bool(scenarios[2]['relay_refs']))
        check('computed_demo_outcomes', [r['status'] for r in results] ==
              ['feasible_under_assumptions','infeasible_in_model','feasible_under_assumptions'])
        check('assumed_fidelity_visible', all(r['model_fidelity'] == 'assumed_rate_simulation'
              and r['warnings'] and r['assumptions'] for r in results))

        relay_result, relay_scenario = results[2], scenarios[2]
        contacts = {c['contact_id']:c for c in relay_result['contacts']}
        allocations = relay_result['allocations']
        waited = False
        for outgoing in allocations:
            node = contacts[outgoing['contact_id']]['sender']
            if node not in relay_scenario['relay_refs']:
                continue
            for incoming in allocations:
                if (contacts[incoming['contact_id']]['receiver'] == node
                    and all(incoming[k] == outgoing[k] for k in ('chunk_id','byte_offset','byte_length'))
                    and parse_utc(incoming['byte_available_utc']) <
                        parse_utc(outgoing['source_transmit_interval']['start_utc'])):
                    waited = True
        check('actual_relay_wait_and_storage', waited and any(
              r['node_id'] in relay_scenario['relay_refs'] for r in relay_result['storage_intervals']))
        check('no_fabricated_live_spacecraft_states', all(d['states'] == []
              and d['state_status'] == 'unknown' and d['state_unavailable_reasons'] for d in displays))
        registration = load_renderer_registration(root/'data/renderer-registration.manifest.json')
        check('regional_registration_preserved', registration['release_gate']['map_registration_passed'])

        manual_scenario, manual_result, _ = archive('fixtures/phase-6/manual-live/run.zip')
        receipt = read('fixtures/phase-6/independent-review.json')
        recorded = receipt['archive']
        check('independent_archive_binding', recorded['path'] == 'fixtures/phase-6/manual-live/run.zip'
              and hashlib.sha256((root/recorded['path']).read_bytes()).hexdigest() == recorded['sha256']
              and recorded['scenario_sha256'] == scenario_sha256(manual_scenario))
        check('independent_reoptimization', receipt['export_verification']['passed']
              and not receipt['export_verification']['errors']
              and receipt['reoptimization']['allocations_identical'] is True
              and all(receipt['reoptimization'][key] == manual_result[key] for key in
                      ('status','solver_status','delivered_bytes','final_byte_arrival_utc')))
        check('review_actor_labeled_honestly', receipt['actor']['actor_type'] == 'agent'
              and receipt['actor']['human_usability_study'] is False)

        sensitivity = read('fixtures/phase-6/sensitivity.json')
        records = sensitivity['schedule_cases']
        required = {'baseline','battery-low','rate-half','service-off','scheduler-5s','scheduler-30s'}
        check('sensitivity_controls_covered', {r['case_id'] for r in records} == required
              and bool(sensitivity['unresolved_differences']))
        for case in records:
            scenario, analysis, result = (case[k] for k in ('scenario','analysis_inputs','result'))
            validate_document(scenario, 'scenario')
            validate_document(result, 'result')
            digest = scenario_sha256(scenario)
            check('sensitivity_binding:'+case['case_id'], digest == case['scenario_sha256']
                  == result['scenario_sha256'] == analysis['scenario_sha256'])
            if result['status'] == 'feasible_under_assumptions':
                replay = replay_schedule(scenario, analysis['contacts'], result['allocations'],
                                         analysis['generation_bins'])
                check('sensitivity_replay:'+case['case_id'], replay['passed'] and all(
                      replay[k] == result[k] for k in ('delivered_bytes','final_byte_arrival_utc',
                          'energy_history','buffer_history','storage_intervals')))
            else:
                check('no_false_schedule:'+case['case_id'], not result['allocations']
                      and case['replay'] is None)
        terrain = sensitivity['terrain_segment_cases']
        check('missing_terrain_stays_unknown', len(terrain) == 4
              and [t['visibility']['status'] for t in terrain] == ['clear','unknown','clear','unknown']
              and 'missing_terrain' in terrain[-1]['visibility']['quality_flags']
              and terrain[-1]['visibility']['minimum_sampled_clearance_m'] is None)

        ui = read('web/docs/phase-6-independent-review.json')
        check('independent_interface_walkthrough', ui['passed'] is True
              and ui['actor']['actor_type'] == 'agent'
              and ui['actor']['human_usability_study'] is False
              and all(ui['checks'][key] is True for key in
                      ('same_task_controls','limiting_reason_inspected',
                       'stored_states_unknown','export_verified')))
        check('verification_runs_recorded', evidence['verification']['engine_tests']['passed'] > 0
              and evidence['verification']['engine_tests']['skipped'] == 0
              and evidence['verification']['web_unit_tests'] > 0
              and evidence['verification']['live_browser_checks'] > 0
              and evidence['verification']['fixture_browser_checks'] > 0
              and evidence['verification']['production_build'] == 'passed')
        check('license_review_recorded_for_scope',
              evidence['acceptance']['licensing_review_complete_for_declared_scope'] is True
              and (root/'soma/docs/phase-6/source-and-license-audit.md').is_file())
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        check('required_evidence_readable', False, str(error))
    report['phase6_complete'] = not report['errors']
    report['phase7_prerequisite_met'] = report['phase6_complete']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    result = verify_phase6(args.root)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result['phase6_complete'] else 1)


if __name__ == '__main__':
    main()

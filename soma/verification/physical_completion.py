"""Verify the bounded physical first release from archived numerical evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from soma.schedule.replay import replay_schedule
from soma.time import parse_utc
from soma.verification.exports import verify_export


def verify_physical_release(root=None):
    root = Path(root or Path(__file__).resolve().parents[2]).resolve()
    report = {'artifact_type':'soma_physical_first_release_verification',
        'scope':'required_bounded_first_release_in_plan', 'checks':[], 'errors':[],
        'required_first_release_complete':False, 'optional_phase7_implemented':False}
    def check(name, passed):
        report['checks'].append({'name':name,'passed':bool(passed)})
        if not passed:
            report['errors'].append(name)
    def read(name):
        return json.loads((root/name).read_text())
    try:
        runs = []
        for name in ('direct-ready','direct-later','relay-later'):
            path=root/f'fixtures/physical-south-pole/{name}/run.zip'
            check('export:'+name,verify_export(path)['passed'])
            with zipfile.ZipFile(path) as z:
                runs.append({key:json.loads(z.read(key+'.json')) for key in
                    ('scenario','result','analysis-inputs','display-data')})
        scenarios=[r['scenario'] for r in runs]
        results=[r['result'] for r in runs]
        check('computed_physical_demo_outcomes',[r['status'] for r in results] ==
            ['feasible_under_assumptions','infeasible_in_model','feasible_under_assumptions'])
        check('physical_inputs_and_assumed_rates',all(s['analysis_mode']=='terrain_ephemeris'
            and s['dataset_manifest_ref']=='physical-lola-de421-v1' for s in scenarios)
            and all(r['model_fidelity']=='assumed_rate_simulation' for r in results))
        fixed=('lander','data_volume','hardware_profile_ref','relay_refs','station_refs',
               'rate_method','pointing_assumption','service_assumption_label')
        check('same_task_and_site',all(s[key]==scenarios[0][key] for s in scenarios for key in fixed))
        check('same_hardware_and_initial_battery',all(
            {k:v for k,v in s['profiles']['hardware'][0].items() if k!='service'} ==
            {k:v for k,v in scenarios[0]['profiles']['hardware'][0].items() if k!='service'} for s in scenarios))
        check('six_hour_mission_age_deadline',all((parse_utc(s['deadline_utc'])-
            parse_utc(s['data_ready_utc'])).total_seconds()==21600 for s in scenarios))
        check('direct_then_enabled_configured_relay',all(s['route_families']==['direct_to_earth'] for s in scenarios[:2])
            and set(scenarios[2]['route_families'])=={'direct_to_earth','single_lunar_relay'})
        check('direct_failure_has_no_available_contacts',results[1]['contacts']==[]
              and results[1]['allocations']==[] and results[1]['delivered_bytes']==0)
        for name,r in zip(('direct-ready','direct-later','relay-later'),runs):
            a,d=r['analysis-inputs'],r['display-data']
            check('complete_generation:'+name,a['generation_complete'] is True)
            check('resolved_ground_and_two_heights:'+name,
                d['surface_points'][0]['elevation_m']==a['environment']['analysis_point']['elevation_m']
                and a['environment']['horizons']['antenna']['site']['height_m']==r['scenario']['lander']['antenna_height_m']
                and a['environment']['horizons']['panel']['site']['height_m']==r['scenario']['lander']['panel_height_m'])
            check('real_stored_synthetic_orbit:'+name,bool(d['states']) and d['states']==a['states']
                and len({tuple(s['position']) for s in d['states']})>1
                and all(s['provenance_label']=='synthetic_two_body_lunar_preset' for s in d['states']))
            check('no_full_optimality_over_unknown_contacts:'+name,a['contacts_complete'] or
                  r['result']['solver_status'] in ('feasible_incumbent','unresolved'))
        generation=[r['analysis-inputs']['generation_bins'] for r in runs]
        check('date_changes_solar_inputs',min(b['generation_w'] for b in generation[0])>0
              and all(b['generation_w']==0 for b in generation[1]))
        relay=runs[2]; contacts={c['contact_id']:c for c in relay['result']['contacts']}
        incoming=[a for a in relay['result']['allocations'] if contacts[a['contact_id']]['receiver'] in scenarios[2]['relay_refs']]
        outgoing=[a for a in relay['result']['allocations'] if contacts[a['contact_id']]['sender'] in scenarios[2]['relay_refs']]
        check('causal_relay_wait',bool(incoming) and bool(outgoing) and
            parse_utc(incoming[0]['byte_available_utc'])<parse_utc(outgoing[0]['source_transmit_interval']['start_utc']))
        terrain=read('fixtures/physical-south-pole/terrain-verification.json')
        check('terrain_count_mask_preserved',all(
            role['cases']['release_250km']['quality']['interpolated_samples']>0 and
            role['cases']['release_250km']['quality']['strict_measurements_unknown_samples']>0
            for role in terrain['roles'].values()))
        check('terrain_extent_and_omitted_envelope',all(role['release_profile']['converged'] and
            role['cases']['release_250km']['quality']['unknown_samples']==0 and
            role['far_field_envelope']['omitted_terrain_cannot_raise_sampled_bands_under_cap']
            for role in terrain['roles'].values()))
        check('independent_scalar_horizon',all(max(c['absolute_difference_deg'] for c in role['scalar_reference_checks'])<1e-6
            for role in terrain['roles'].values()))
        sampling=read('fixtures/physical-south-pole/sampling-verification.json')
        check('current_sampling_source',sampling['physical_source_sha256']==hashlib.sha256((root/'soma/physical.py').read_bytes()).hexdigest())
        check('time_resolution_comparison',sampling['same_contact_ids'] and sampling['same_feasibility_status']
              and bool(sampling['unresolved_differences']))
        for case in sampling['cases']:
            a,r=case['analysis_inputs'],case['result']
            replay=replay_schedule(case['scenario'],a['contacts'],r['allocations'],a['generation_bins'])
            check('sampling_replay:'+str(case['time_step_s']),r['status']=='feasible_under_assumptions' and replay['passed'])
        audit=read('fixtures/physical-south-pole/independent-audit.json')
        check('independent_archive_reproduction',len(audit['archive_checks'])==3 and all(
            row['verified'] and row['original_status']==row['reoptimized_status'] and
            row['hash']==hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
            for row in audit['archive_checks']))
        ui=read('web/docs/physical-first-release-verification.json')
        check('physical_interface_walkthrough',ui['passed'] and ui['actor']['actor_type']=='agent'
            and ui['actor']['human_usability_study'] is False and all(ui['checks'][k] for k in
                ('physical_site_date_controls','exact_stored_states','map_failure_text_fallback',
                 'direct_limiting_reason','download_bytes_match')))
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as error:
        report['errors'].append(str(error))
    report['required_first_release_complete']=not report['errors']
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path)
    args=parser.parse_args()
    result=verify_physical_release(args.root)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['required_first_release_complete'] else 1)

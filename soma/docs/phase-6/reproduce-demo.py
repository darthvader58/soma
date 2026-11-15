"""Recompute the controlled same-day demonstration and independently check exports."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from soma.engine import plan_run
from soma.exports import create_run_package, json_bytes, summary
from soma.validation import load_scenario, scenario_sha256
from soma.verification.exports import verify_export


def reproduce(output):
    root = Path(__file__).resolve().parents[3]
    baseline = load_scenario(root/'fixtures/synthetic-relay/scenario.json')
    baseline['data_volume'] = {'value':16,'unit':'MiB'}
    baseline['route_families'] = ['direct_to_earth']
    baseline['input_provenance'].append({
        'scope':'Phase 6 controlled scheduling demonstration', 'input_class':'synthetic',
        'description':'Same declared 16 MiB task, hardware, initial battery, site, absolute deadline and fixed network. Only data-ready time and enabled route family change. No new operating-day or site geometry is claimed.',
        'source_urls':[],
    })
    variants = [('direct-ready','2026-11-14T08:50:00Z',['direct_to_earth']),
                ('direct-later','2026-11-14T09:05:00Z',['direct_to_earth']),
                ('relay-later','2026-11-14T09:05:00Z',['direct_to_earth','single_lunar_relay'])]
    records = []
    for name, ready, routes in variants:
        scenario = deepcopy(baseline)
        scenario.update(scenario_id='phase6-'+name,data_ready_utc=ready,route_families=routes)
        run = plan_run(scenario,options={'bin_s':30,'chunk_bytes':16777216,'time_limit_s':5})
        target = output/name
        target.mkdir(parents=True,exist_ok=True)
        (target/'scenario.json').write_bytes(json_bytes(scenario))
        (target/'run.json').write_bytes(json_bytes(run))
        (target/'run.zip').write_bytes(create_run_package(run))
        verification = verify_export(target/'run.zip')
        (target/'verification.json').write_bytes(json_bytes(verification))
        if not verification['passed']:
            raise RuntimeError('Export verification failed for '+name)
        records.append({'case_id':name,'scenario_sha256':scenario_sha256(scenario),
                        'summary':summary(run),'export_verification_passed':True,
                        'files':{n:hashlib.sha256((target/n).read_bytes()).hexdigest()
                                 for n in ('scenario.json','run.json','run.zip','verification.json')}})
    expected = ['feasible_under_assumptions','infeasible_in_model','feasible_under_assumptions']
    observed = [r['summary']['status'] for r in records]
    if observed != expected:
        raise RuntimeError('Computed demonstration differs from the recorded story: '+str(observed))
    report = {'artifact_type':'soma_phase6_controlled_demo','version':'1.0.0',
              'input_class':'synthetic','changes':['later data-ready time within one operating day','enable the configured lunar relay family'],
              'fixed_controls':['data volume','hardware profile','initial battery state','site','absolute deadline','analysis horizon','configured network profiles'],
              'cases':records,'limitations':['This does not demonstrate a new site or operating-day ephemeris. Unsupported geometry remains unknown.',
                'The configured relay has no trajectory. No spacecraft path is invented.',
                'Thirty-second whole-chunk occupancy is conservative; exact transmission/receive/storage records are in each export.']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'demonstration.json').write_bytes(json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    args = parser.parse_args()
    result = reproduce(args.output_dir)
    print(json.dumps({'cases':[{'id':r['case_id'],'status':r['summary']['status'],'arrival_utc':r['summary']['final_byte_arrival_utc']} for r in result['cases']]},indent=2))

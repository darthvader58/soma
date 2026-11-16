"""Recompute the controlled physical date demonstration and verify its exports."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from soma.engine import plan_run
from soma.exports import create_run_package, json_bytes, summary
from soma.validation import load_scenario
from soma.verification.exports import verify_run_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    before = load_scenario(root/'fixtures/physical-south-pole/scenario.json')
    after = load_scenario(root/'fixtures/physical-south-pole/scenario-later.json')
    cases = [('direct-ready',before,False),('direct-later',after,False),('relay-later',after,True)]
    records = []
    for name, request, relay in cases:
        scenario = deepcopy(request)
        if not relay:
            scenario['route_families'] = ['direct_to_earth']
        directory = Path(args.output_dir)/name
        directory.mkdir(parents=True,exist_ok=True)
        run = plan_run(scenario)
        package = create_run_package(run)
        verification = verify_run_package(package)
        if not verification['passed']:
            raise RuntimeError(str(verification['errors']))
        (directory/'run.zip').write_bytes(package)
        (directory/'scenario.json').write_bytes(json_bytes(scenario))
        record = summary(run)
        record.pop('replay',None)
        record.pop('details',None)
        (directory/'summary.json').write_bytes(json_bytes(record))
        receipt = {key:value for key,value in verification.items() if key != 'replay'}
        (directory/'verification.json').write_bytes(json_bytes(receipt))
        records.append({'case_id':name,'scenario_sha256':run['result']['scenario_sha256'],
            'status':run['result']['status'],'solver_status':run['result']['solver_status'],
            'final_byte_arrival_utc':run['result']['final_byte_arrival_utc'],
            'delivered_bytes':run['result']['delivered_bytes'],
            'zip_sha256':hashlib.sha256(package).hexdigest(),'export_verified':True,
            'generation_min_w':min(b['generation_w'] for b in run['analysis_inputs']['generation_bins']),
            'generation_max_w':max(b['generation_w'] for b in run['analysis_inputs']['generation_bins'])})
        print(json.dumps(records[-1]),flush=True)
    (Path(args.output_dir)/'demonstration.json').write_bytes(json_bytes({
        'artifact_type':'physical_controlled_date_demonstration','cases':records,
        'comparison_rule':'Same site, volume, hardware, initial battery, station locations and synthetic orbit elements; same six-hour mission-age deadline and service duration. UTC operating dates move together.',
        'outcomes_selected_from_computed_results':True}))


if __name__ == '__main__':
    main()

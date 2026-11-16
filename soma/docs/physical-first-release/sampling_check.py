"""Compare the same physical request at two declared geometry sampling steps."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from soma.engine import plan_run
from soma.exports import json_bytes
import soma.physical as physical
from soma.validation import load_scenario


def main():
    root = Path(__file__).resolve().parents[3]
    scenario = load_scenario(root/'fixtures/physical-south-pole/scenario.json')
    cases = []
    original = physical.TIME_STEP_S
    try:
        for step in (60,30):
            physical.TIME_STEP_S = step
            analysis = physical.prepare_physical_analysis(scenario)
            run = plan_run(scenario, analysis_inputs=analysis,
                           options={'bin_s':60,'chunk_bytes':16777216,'time_limit_s':15})
            cases.append({'time_step_s':step,'event_guard_s':step/2,
                'scenario':scenario,'scenario_sha256':analysis['scenario_sha256'],
                'analysis_inputs':{key:analysis[key] for key in ('format_version','scenario_sha256',
                    'contacts','generation_bins','contacts_complete','generation_complete',
                    'assumptions','warnings','provenance')},
                'result':run['result'],'replay':run['validation'],
                'mean_generation_w':sum(b['generation_w'] for b in analysis['generation_bins'])/len(analysis['generation_bins'])})
    finally:
        physical.TIME_STEP_S = original
    first,second = cases
    contacts = [{c['contact_id']:c for c in case['analysis_inputs']['contacts']} for case in cases]
    from soma.time import parse_utc
    common = set(contacts[0]) & set(contacts[1])
    differences = [abs((parse_utc(contacts[0][key]['source_transmit_window'][edge])-
                        parse_utc(contacts[1][key]['source_transmit_window'][edge])).total_seconds())
                   for key in common for edge in ('start_utc','end_utc')]
    report = {'artifact_type':'physical_sampling_sensitivity','cases':cases,
        'physical_source_sha256':hashlib.sha256((root/'soma/physical.py').read_bytes()).hexdigest(),
        'same_contact_ids':contacts[0].keys()==contacts[1].keys(),
        'maximum_common_contact_boundary_difference_s':max(differences,default=None),
        'same_feasibility_status':first['result']['status']==second['result']['status'],
        'unresolved_differences':[
            'Reducing geometry step also scales the declared half-bin contact guard; both values are recorded.',
            'Sampled contact boundaries may differ. Neither run proves absence of every shorter unsampled event.',
            'A time-limited feasible incumbent can select a later allocation; selected completion times do not establish physical convergence or a finer-grid optimum.',
            'Solar generation uses the minimum endpoint/midpoint sample held constant per bin, not a continuous lower bound.']}
    output=root/'fixtures/physical-south-pole/sampling-verification.json'
    output.write_bytes(json_bytes(report))
    print(json.dumps({key:report[key] for key in ('same_contact_ids','maximum_common_contact_boundary_difference_s','same_feasibility_status')}))


if __name__ == '__main__':
    main()

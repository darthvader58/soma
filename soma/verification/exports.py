"""Verify archived handoff records and replay feasibility without an optimizer."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import zipfile

from soma.schedule.replay import replay_schedule
from soma.validation import scenario_sha256, validate_document


def verify_run_package(source):
    """Read a ZIP path or bytes without extraction; return auditable checks/errors."""
    report = {'passed':False, 'checks':[], 'errors':[], 'replay':None,
              'reproduce_command':'.venv/bin/python -m soma.verification.exports RUN_ZIP'}
    def check(name, condition, detail=''):
        report['checks'].append({'name':name, 'passed':bool(condition)})
        if not condition:
            report['errors'].append({'check':name, 'reason':detail or 'exported records disagree'})
    try:
        payload = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
        report['zip_sha256'] = hashlib.sha256(payload).hexdigest()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            check('unique_safe_member_names', len(names)==len(set(names)) and all(
                name and '/' not in name and '\\' not in name and name not in ('.','..') for name in names))
            if report['errors']:
                return report
            files = {name:archive.read(name) for name in names}
        required = {'run-manifest.json','scenario.json','result.json','summary.json','analysis-inputs.json',
                    'contacts.csv','schedule.csv','energy.csv','buffer-history.csv','display.czml','explanation.md'}
        check('required_members', required <= files.keys(), str(sorted(required-files.keys())))
        if report['errors']:
            return report
        document = lambda name: json.loads(files[name])
        manifest, scenario, result = (document(name) for name in ('run-manifest.json','scenario.json','result.json'))
        declared = manifest['files']
        check('manifest_complete', set(declared)==set(files)-{'run-manifest.json'})
        for name, info in declared.items():
            content = files.get(name)
            check('checksum:'+name, content is not None and info['size_bytes']==len(content)
                  and info['sha256']==hashlib.sha256(content).hexdigest())
        for kind, value in [('scenario',scenario), ('result',result)]:
            validate_document(value,kind)
            check('schema:'+kind, True)
        for kind, values in [('contact',result['contacts']), ('allocation',result['allocations'])]:
            for value in values:
                validate_document(value,kind)
            check('schema:'+kind, True)
        digest = scenario_sha256(scenario)
        report.update(scenario_sha256=digest, status=result['status'], solver_status=result['solver_status'])
        analysis, summary = (document(name) for name in ('analysis-inputs.json','summary.json'))
        display = document('display-data.json') if 'display-data.json' in files else None
        check('feasible_display_present', display is not None or result['status']!='feasible_under_assumptions')
        if display is None:
            report['display_status']='legacy_nonfeasible_package_without_display_data; display checks unavailable'
        check('scenario_hash_bindings', all(v['scenario_sha256']==digest for v in (result,manifest,analysis,summary,*([display] if display else []))))
        check('analysis_contacts_equal_native', analysis['contacts']==result['contacts'])
        if display:
            check('display_environment_exact', display.get('environment')==analysis.get('environment'))
        environment = analysis.get('environment')
        if environment:
            epochs={sample['epoch_utc'] for track in environment.get('tracks',[]) for sample in track.get('samples',[])}
            epochs.update(sample['epoch_utc'] for key in ('solar_samples','power_samples') for sample in environment.get(key,[]))
            if display:
                check('display_sample_epochs_exact', display['sample_epochs_utc']==sorted(epochs))
            check('environment_scenario_binding', environment['scenario_sha256']==digest)
            if 'scenario' in environment:
                check('environment_scenario_exact', environment['scenario']==scenario)
        if display:
            for key in ('contacts','allocations','storage_intervals','energy_history','buffer_history','assumptions','warnings'):
                check('display_native:'+key, display[key]==result[key])
        for key in ('scenario_id','scenario_sha256','status','solver_status','model_fidelity','delivered_bytes','final_byte_arrival_utc','assumptions','warnings'):
            check('summary_native:'+key, summary[key]==result[key])
        if display:
            check('display_summary_exact', display['summary']==summary)
        for key in ('warnings','assumptions'):
            check('manifest_native:'+key, manifest[key]==result[key])
            explanation = files['explanation.md'].decode('utf-8')
            check('explanation:'+key, all('- '+text in explanation for text in result[key]))
        check('explanation_outcome', 'Outcome: '+result['status']+'.' in explanation)
        if 'renderer-registration.json' in files:
            check('registration_exact', document('renderer-registration.json')==display['registration'])
        if 'renderer-conversion.json' in files:
            check('conversion_exact', document('renderer-conversion.json')==display.get('renderer_conversion'))
        props = next(row['properties'] for row in document('display.czml') if row.get('id')=='soma-run')
        check('czml_native', props['scenario_sha256']==digest and json.loads(props['allocations_json'])==result['allocations']
              and json.loads(props['warnings_json'])==result['warnings'] and props['model_fidelity']==result['model_fidelity'])
        if display:
            check('czml_registration', props['registration_status']==display['registration']['status'] and props['map_registration_passed']==display['registration']['release_gate']['map_registration_passed'])
        contacts = {c['contact_id']:c for c in result['contacts']}
        def csv_check(name, headers, expected):
            rows = list(csv.reader(io.StringIO(files[name].decode('utf-8'),newline='')))
            check('csv_header:'+name, bool(rows) and rows[0]==headers)
            actual = rows[1:]
            okay = len(actual)==len(expected)
            for row, values in zip(actual,expected):
                if len(row)!=len(values):
                    okay=False
                    continue
                for cell, value in zip(row,values):
                    if value is None:
                        okay = okay and cell==''
                    elif isinstance(value,(int,float)):
                        try:
                            okay = okay and Decimal(cell)==Decimal(str(value))
                        except InvalidOperation:
                            okay=False
                    else:
                        okay = okay and cell==str(value)
            check('csv_native:'+name, okay)
        csv_check('schedule.csv', ['allocation_id','chunk_id','byte_offset_bytes','byte_length_bytes','contact_id','sender','receiver','source_transmit_start_utc','source_transmit_end_utc','receiver_occupancy_start_utc','receiver_occupancy_end_utc','byte_available_utc'],
                  [[a['allocation_id'],a['chunk_id'],a['byte_offset'],a['byte_length'],a['contact_id'],contacts[a['contact_id']]['sender'],contacts[a['contact_id']]['receiver'],a['source_transmit_interval']['start_utc'],a['source_transmit_interval']['end_utc'],a['receiver_occupancy_interval']['start_utc'],a['receiver_occupancy_interval']['end_utc'],a['byte_available_utc']] for a in result['allocations']])
        csv_check('contacts.csv',['contact_id','sender','receiver','sender_terminal_id','receiver_terminal_id','source_transmit_start_utc','source_transmit_end_utc','payload_rate_bits_per_second','available_capacity_bits','one_way_delay_seconds','rate_method','service_provenance','quality_flags_json'],
                  [[c['contact_id'],c['sender'],c['receiver'],c['sender_terminal_id'],c['receiver_terminal_id'],c['source_transmit_window']['start_utc'],c['source_transmit_window']['end_utc'],c['payload_rate_bps'],c['available_capacity_bits'],c['one_way_delay']['seconds'],c['rate_method'],c['service_provenance'],json.dumps(c['quality_flags'])] for c in result['contacts']])
        for name, field, quantity in [('energy.csv','energy_history','stored_energy_wh'),('buffer-history.csv','buffer_history','stored_bytes')]:
            csv_check(name,['node_id','epoch_utc',quantity],[[r['node_id'],r['epoch_utc'],r[quantity]] for r in result[field]])
        if result['status']=='feasible_under_assumptions':
            check('analysis_complete', analysis['contacts_complete'] is True and analysis['generation_complete'] is True)
            replay = replay_schedule(scenario,analysis['contacts'],result['allocations'],analysis['generation_bins'])
            report['replay']=replay
            check('independent_replay', replay['passed'], str(replay['errors']))
            for key in ('delivered_bytes','final_byte_arrival_utc','energy_history','buffer_history','storage_intervals'):
                check('replay_native:'+key, replay[key]==result[key])
            if 'replay.json' in files:
                check('archived_replay', document('replay.json')==replay)
            check('summary_replay', summary.get('replay')==replay)
        else:
            report['replay_status']='no_feasible_schedule_claimed; infeasibility is not independently proved by replay'
            check('no_allocations_without_feasibility', result['allocations']==[])
    except Exception as exc:
        report['errors'].append({'check':'read_or_contract', 'reason':f'{type(exc).__name__}: {exc}'})
    report['passed']=not report['errors']
    return report


def verify_export(path):
    """Verify a run archive using the public Phase 6 handoff entry point."""
    return verify_run_package(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_zip')
    args=parser.parse_args()
    report=verify_run_package(args.run_zip)
    report['reproduce_command']='.venv/bin/python -m soma.verification.exports '+args.run_zip
    print(json.dumps(report,indent=2,allow_nan=False))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()

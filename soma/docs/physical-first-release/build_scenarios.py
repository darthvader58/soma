"""Build declared demonstration requests; outcomes are computed separately."""
from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def scenario(day):
    value = json.loads((ROOT/'fixtures/synthetic-relay/scenario.json').read_text())
    value.update(scenario_id=f'physical-south-pole-nov-{day:02}', analysis_mode='terrain_ephemeris',
                 dataset_manifest_ref='physical-lola-de421-v1')
    date = f'2026-11-{day:02}'
    window = {'start_utc':date+'T08:00:00Z', 'end_utc':date+'T14:00:00Z'}
    value['analysis_horizon'] = deepcopy(window)
    value['data_ready_utc'], value['deadline_utc'] = window.values()
    value['data_volume'] = {'value':16,'unit':'MiB'}
    value['lander']['id'] = 'polar-lander'
    value['lander'].update(latitude_deg=-89.03093035536243, longitude_deg_east=1.389336784014743)
    value['service_assumption_label'] = 'Assumed finite six-hour educational service; no operator allocation'
    hardware = value['profiles']['hardware'][0]
    hardware['input_class'] = 'assumed'
    relay = value['profiles']['relays'][0]
    relay['trajectory'].update(kind='synthetic_two_body_lunar_preset', reference='soma-polar-200km-v1',
                               coverage=deepcopy(window))
    station = value['profiles']['stations'][0]
    stations = []
    for identifier, latitude, longitude in (
            ('educational-americas',35,-117), ('educational-europe',40,-4),
            ('educational-australia',-35,149)):
        item = deepcopy(station)
        item.update(id=identifier, latitude_deg=latitude, longitude_deg_east=longitude,
                    input_class='assumed')
        stations.append(item)
    value['profiles']['stations'] = stations
    value['station_refs'] = [s['id'] for s in stations]
    for item in [hardware, relay, *stations]:
        item['service'] = {'label':value['service_assumption_label'], 'input_class':'assumed',
                           'windows':[deepcopy(window)]}
    value['input_provenance'] = [
        {'scope':'terrain and celestial geometry','input_class':'published',
         'description':'Numerical LOLA near/far products and matched DE421 SPICE; ground elevation resolved by the engine. Published interpolation quality is retained, not relabeled as measured terrain.',
         'source_urls':['https://pgda.gsfc.nasa.gov/products/81','https://naif.jpl.nasa.gov/naif/spiceconcept.html']},
        {'scope':'hardware, rates, pointing and service','input_class':'assumed',
         'description':'Educational lander profile, ideal pointing, assumed net payload rates and finite six-hour service calendars. Three rounded geographic station proxies illustrate diversity; they are not actual DSN antenna coordinates or booked service.',
         'source_urls':[]},
        {'scope':'lunar relay trajectory','input_class':'synthetic',
         'description':'synthetic_two_body_lunar_preset soma-polar-200km-v1. Explicit conic model, not an operational frozen orbit, libration orbit or real relay ephemeris.',
         'source_urls':[]},
        {'scope':'controlled date comparison','input_class':'assumed',
         'description':'Same site, data volume, hardware, initial battery, network and six-hour mission-age deadline. Ready time, horizon, finite service calendars and synthetic trajectory coverage move together with the selected operating day.',
         'source_urls':[]},
    ]
    return value


if __name__ == '__main__':
    directory = ROOT/'fixtures/physical-south-pole'
    directory.mkdir(parents=True, exist_ok=True)
    for name, day in [('scenario.json',24),('scenario-later.json',30)]:
        (directory/name).write_text(json.dumps(scenario(day),indent=2)+'\n')

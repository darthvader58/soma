"""Bounded, sampled physical inputs for the declared LOLA/DE421 planning model.

This module connects existing geometry, disk illumination and contact models.
It never upgrades a sampled assumption into continuous or operational coverage.
"""
from copy import deepcopy
from datetime import timedelta
import hashlib
import math
import os
from pathlib import Path

import numpy as np

from soma.diagnostics import _epochs, _horizon_classification
from soma.geometry import SpiceGeometry, SyntheticTwoBodyLunarPreset, vector_direction
from soma.geometry.surface import segment_intersects_sphere
from soma.illumination import solar_disk_visibility
from soma.links import assess_contact
from soma.power import fixed_panel_power
from soma.time import format_utc, parse_utc
from soma.time.spice import utc_to_et
from soma.validation import load_json, resource_directory, scenario_sha256, validate_document

MODEL_ID = 'physical-lola-de421-v1'
RELAY_REFERENCE = 'soma-polar-200km-v1'
TIME_STEP_S = 60
TERRAIN_ENVELOPE_M = 12000.0
INNER_BODY_RADIUS_M = 1720000.0
SPEED_OF_LIGHT_M_S = 299792458.0
RATES_BPS = {'direct_to_earth': 256000, 'lander_to_relay': 2000000, 'relay_to_earth': 10000000}


def _cancel(event):
    if event is not None and event.is_set():
        raise InterruptedError('Planning canceled during physical input preparation')


def _window(start, end):
    return {'start_utc': format_utc(start), 'end_utc': format_utc(end)}


def _shell_intervals(a, b, radius):
    """Parameter intervals of a finite segment lying in a spherical envelope."""
    d = b-a
    aa, bb, cc = float(d@d), float(2*a@d), float(a@a-radius**2)
    discriminant = bb*bb-4*aa*cc
    if discriminant < 0:
        return []
    low, high = sorted(((-bb-math.sqrt(discriminant))/(2*aa), (-bb+math.sqrt(discriminant))/(2*aa)))
    low, high = max(0.0, low), min(1.0, high)
    return [(low, high)] if high >= low else []


def finite_terrain_test(dem, source_m, target_m, *, clearance_m=0.5, step_m=120.0):
    """Test only low-altitude parts of a finite segment against numerical terrain.

    The 12 km global terrain envelope is an explicit conservative assumption,
    not an extra DEM. Missing samples inside it remain unknown. Terrain beyond
    the endpoint is never consulted. The first 5 km of each low-altitude interval receive 5 m sampling.
    """
    if not math.isfinite(step_m) or step_m <= 0 or not math.isfinite(clearance_m) or clearance_m < 0:
        raise ValueError('Terrain sampling requires positive step and nonnegative finite clearance')
    a, b = np.asarray(source_m, float), np.asarray(target_m, float)
    if a.shape != (3,) or b.shape != (3,) or not np.isfinite([a, b]).all():
        raise ValueError('Finite terrain endpoints require finite meter vectors')
    length = float(np.linalg.norm(b-a))
    if length < 1e-6:
        return {'status': 'unknown', 'reason': 'degenerate_segment', 'sample_count': 0}
    if segment_intersects_sphere(a, b, INNER_BODY_RADIUS_M):
        return {'status': 'blocked', 'reason': 'declared_inner_lunar_body_intersection', 'sample_count': 0}
    intervals = _shell_intervals(a, b, dem.reference_radius_m+TERRAIN_ENVELOPE_M)
    samples = set()
    for lo, hi in intervals:
        count = math.ceil((hi-lo)*length/step_m)
        if count > 20000:
            return {'status': 'unknown', 'reason': 'finite_segment_sampling_budget', 'sample_count': 0}
        samples.update(np.linspace(lo, hi, max(1, count)+1).tolist())
        for endpoint in (lo, hi):
            near = min(5000/length, hi-lo)
            samples.update(np.linspace(endpoint, endpoint+near if endpoint == lo else endpoint-near, max(1,math.ceil(near*length/5))+1).tolist())
    unknown, minimum, flags = False, math.inf, set()
    ordered = np.asarray(sorted(samples))
    if not len(ordered):
        return {'status':'clear','reason':'above_declared_global_terrain_envelope','sample_count':0,
                'tested_range_m':length,'terrain_envelope_m':TERRAIN_ENVELOPE_M,
                'quality_flags':['assumed_global_terrain_upper_bound']}
    points = a[None,:]+ordered[:,None]*(b-a)
    radii = np.linalg.norm(points,axis=1)
    latitudes = np.degrees(np.arcsin(np.clip(points[:,2]/radii,-1,1)))
    longitudes = (np.degrees(np.arctan2(points[:,1],points[:,0]))+180)%360-180
    if hasattr(dem,'sample_many'):
        heights,counts,quality = dem.sample_many(latitudes,longitudes)
        flags.add('published_numerical_LOLA_grid')
        if np.any(quality & 1):
            flags.add('published_interpolated_height_not_measured')
        if np.any(quality & 2):
            flags.add('explicit_coarse_resolution_downgrade')
        if np.any(quality & 4):
            flags.add('missing_terrain_unknown')
    else:
        heights=[]
        for lat,lon in zip(latitudes,longitudes):
            sample=dem.sample(float(lat),float(lon))
            flags.update(sample.quality_flags)
            heights.append(np.nan if sample.elevation_m is None else sample.elevation_m)
        heights=np.asarray(heights)
    gaps=radii-dem.reference_radius_m-heights
    unknown=bool(np.any(~np.isfinite(gaps)))
    known=gaps[np.isfinite(gaps)]
    minimum=float(np.min(known)) if len(known) else math.inf
    if np.any(known < -clearance_m):
        return {'status':'blocked','reason':'finite_sampled_terrain_intersection','sample_count':len(samples),
                'minimum_sampled_clearance_m':minimum,'quality_flags':sorted(flags)}
    unknown |= bool(np.any(known <= clearance_m))
    return {'status': 'unknown' if unknown else 'clear',
            'reason': 'missing_terrain_or_unresolved_clearance' if unknown else 'finite_segment_clear_under_sampling',
            'sample_count': len(samples), 'tested_range_m': length,
            'minimum_sampled_clearance_m': None if minimum == math.inf else minimum,
            'quality_flags': sorted(flags), 'terrain_envelope_m': TERRAIN_ENVELOPE_M,
            'terrain_step_m': step_m, 'near_5000m_step_m': 5.0}


def _state(target, epoch, position, label):
    return {'target': target, 'origin': 'MOON', 'frame': 'MOON_ME_DE421', 'epoch': epoch,
            'epoch_format': 'rfc3339', 'time_scale': 'UTC', 'position': np.asarray(position).tolist(),
            'position_unit': 'm', 'provenance_label': label}


def _relay(geometry, scenario, profile, site):
    trajectory = profile['trajectory']
    if (trajectory['kind'], trajectory['reference'], trajectory['origin'], trajectory['frame'],
        trajectory['time_scale'], trajectory['position_unit']) != (
            'synthetic_two_body_lunar_preset', RELAY_REFERENCE, 'MOON', 'J2000', 'UTC', 'm'):
        raise ValueError('Unsupported relay trajectory: only explicit soma-polar-200km-v1 synthetic preset is implemented')
    preset = SyntheticTwoBodyLunarPreset(target=profile['id'], epoch_utc=scenario['analysis_horizon']['start_utc'],
        coverage=trajectory['coverage'], gm_m3_s2=4.902800066e12, reference_radius_m=site.reference_radius_m,
        semimajor_axis_m=site.reference_radius_m+200000, eccentricity=.01, inclination_deg=90,
        ascending_node_deg=0, argument_periapsis_deg=0, mean_anomaly_deg=0, utc_to_et=utc_to_et)
    return preset


def _station_normal(geometry, station, epoch):
    lat, lon = np.radians([station['latitude_deg'], station['longitude_deg_east']])
    normal = np.array([math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)])
    return geometry.spice.pxform('ITRF93', 'MOON_ME_DE421', geometry._epoch(epoch)) @ normal


def _station_elevation(geometry, station, sender_position, station_position, epoch):
    """Geodetic normal gate also excludes Earth intersection for above-ground stations.

    A positive elevation places the ray in the outward supporting half-space
    of the convex WGS84 ellipsoid. Stations below that ellipsoid are unsupported.
    """
    if station['height_m'] < 0:
        raise ValueError('Physical first release requires stations at or above WGS84 ellipsoid')
    vector = sender_position-station_position
    return math.degrees(math.asin(float(np.clip(vector@_station_normal(geometry, station, epoch)/np.linalg.norm(vector), -1, 1))))


def _light_time_comparison(geometry, site, station, epoch):
    """Independent receiver-epoch recomputation including Moon-origin translation.

    A representative discrepancy check is not an interval-wide error bound.
    Three fixed-point iterations solve the short station transmission delay.
    """
    et=geometry._epoch(epoch)
    source=geometry.transform_position(site.position_m(site.antenna_height_m),epoch,
        from_frame='MOON_ME_DE421',to_frame='J2000')
    same=np.asarray(geometry.station_state(station,epoch,frame='J2000')['position'])-source
    moon_tx=np.asarray(geometry.spice.spkpos('MOON',et,'J2000','NONE','SSB')[0])*1000
    delay=float(np.linalg.norm(same))/SPEED_OF_LIGHT_M_S
    for _ in range(3):
        arrival=geometry.spice.et2utc(et+delay,'ISOC',6)+'Z'
        receiver=np.asarray(geometry.station_state(station,arrival,frame='J2000')['position'])
        moon_rx=np.asarray(geometry.spice.spkpos('MOON',et+delay,'J2000','NONE','SSB')[0])*1000
        corrected=receiver+moon_rx-moon_tx-source
        delay=float(np.linalg.norm(corrected))/SPEED_OF_LIGHT_M_S
    angle=math.degrees(math.atan2(float(np.linalg.norm(np.cross(same,corrected))),float(same@corrected)))
    return {'station_id':station['id'],'source_epoch_utc':epoch,'receiver_epoch_utc':arrival,
        'one_way_light_time_s':delay,'direction_difference_deg':angle,
        'station_elevation_margin_deg':.1,'within_station_angular_margin':angle<.1,
        'method':'receiver_future_state_in_J2000_with_Moon_barycentric_origin_translation_three_iterations',
        'scope':'representative_sample_comparison_not_an_interval_error_bound'}


def _terminal_pairs(sender, receiver):
    pairs = []
    for tx in sender['terminals']:
        for rx in receiver['terminals']:
            modes = sorted(set(tx['mode_ids']) & set(rx['mode_ids']))
            if tx['band'] == rx['band'] and modes:
                if len(modes) != 1:
                    raise ValueError('Physical first release requires one compatible mode per endpoint pair; multiple radio modes are unsupported')
                pairs.append((tx, rx, modes[0]))
    if len(pairs) > 1:
        raise ValueError('Physical first release requires one compatible terminal pair per link; multiple radio alternatives are unsupported')
    return pairs


def prepare_physical_analysis(scenario, *, progress=None, cancel_event=None):
    """Build hash-bound contacts, generation and display tracks for a bounded run.

    All generated contacts use sampled geometry under declared interval
    assumptions. The scheduler and independent replay remain the authorities
    for byte causality, endpoint occupancy, storage and electrical energy.
    """
    if scenario['analysis_mode'] != 'terrain_ephemeris' or scenario['dataset_manifest_ref'] != MODEL_ID:
        raise ValueError('Physical preparation requires terrain_ephemeris and physical-lola-de421-v1')
    start, end = [parse_utc(scenario['analysis_horizon'][k]) for k in ('start_utc', 'end_utc')]
    if not 0 < (end-start).total_seconds() <= 6*3600:
        raise ValueError('Physical first release supports positive horizons of at most six hours')
    if scenario['rate_method'] != 'assumed_net_rate':
        raise ValueError('Physical first release has no complete RF hardware budget; request assumed_net_rate')
    if scenario['pointing_assumption'] != 'ideal_pointing':
        raise ValueError('Physical first release requires explicitly assumed ideal pointing')
    if len(scenario['relay_refs']) > 1 or len(scenario['station_refs']) > 3:
        raise ValueError('Physical first release supports at most one lunar relay and three Earth stations')
    _cancel(cancel_event)
    model_path = resource_directory('data')/'physical-first-release.manifest.json'
    model = load_json(model_path)
    root = Path(os.environ.get('SOMA_DATA_ROOT', '/private/tmp/soma-phase2-data'))
    from soma.terrain.physical import resolve_terrain_site
    if progress:
        progress('horizon_preparation')
    terrain = resolve_terrain_site(scenario, data_root=root, cancel_event=cancel_event)
    dem, site = terrain['dem'], terrain['site']
    try:
        _cancel(cancel_event)
        manifest = load_json(resource_directory('data')/model['kernel_manifest_ref'])
        # Coverage is verified against the actual binaries for this exact run.
        manifest['coverage'] = _window(start, end+timedelta(seconds=5))
        epochs = _epochs(start, end, TIME_STEP_S)
        midpoint_epochs = [format_utc(parse_utc(a)+(parse_utc(b)-parse_utc(a))/2) for a,b in zip(epochs, epochs[1:])]
        all_epochs = sorted(set(epochs+midpoint_epochs), key=parse_utc)
        hardware = next(p for p in scenario['profiles']['hardware'] if p['id'] == scenario['hardware_profile_ref'])
        profiles = {scenario['lander']['id']: hardware}
        profiles.update({p['id']: p for p in scenario['profiles']['relays'] if p['id'] in scenario['relay_refs']})
        stations = {p['id']: p for p in scenario['profiles']['stations'] if p['id'] in scenario['station_refs']}
        profiles.update(stations)
        lander = scenario['lander']['id']
        horizons = {role: terrain[role+'_horizon'].to_dict() for role in ('antenna', 'panel')}
        tracks, records, powers, solar = [], {}, {}, []
        contacts, decisions, opportunities, occupancy, events = [], [], [], [], []
        unknown_geometry = False
        with SpiceGeometry(manifest, root) as geometry:
            presets = {node: _relay(geometry, scenario, profiles[node], site) for node in scenario['relay_refs']}
            if progress:
                progress('ephemeris_sampling')
            for epoch in all_epochs:
                _cancel(cancel_event)
                states = {body: geometry.state(body, epoch) for body in ('SUN','EARTH')}
                states[lander] = _state(lander, epoch, site.position_m(site.antenna_height_m), 'published_LOLA_resolved_site_explicit_antenna_height')
                states.update({node: geometry.station_state(profile, epoch) for node,profile in stations.items()})
                for node, preset in presets.items():
                    inertial = preset.state(epoch)
                    states[node] = _state(node, epoch, geometry.transform_position(inertial['position'], epoch), preset.label)
                records[epoch] = states
                observer = site.position_m(site.panel_height_m)
                sun = site.local_basis()@(np.asarray(states['SUN']['position'])-observer)
                earth = site.local_basis()@(np.asarray(states['EARTH']['position'])-observer)
                visibility = solar_disk_visibility(sun, earth, horizon=horizons['panel'], samples=256, max_samples=2048, tolerance=.01)
                powers[epoch] = {'epoch_utc': epoch, **fixed_panel_power(hardware['panel'], sun, visibility['visible_fraction'])}
                if epoch in epochs:
                    solar.append({'epoch_utc': epoch, **visibility})
            for target in ['SUN','EARTH',*stations,*presets]:
                role = 'panel' if target == 'SUN' else 'antenna'
                track_samples = []
                for epoch in epochs:
                    state = records[epoch][target]
                    direction = vector_direction(np.asarray(state['position'])-site.position_m(getattr(site,role+'_height_m')),site.local_basis())
                    status,reason='unknown','sample_direction_not_a_contact_or_interval_proof'
                    if target in ('SUN','EARTH'):
                        status,reason=_horizon_classification(terrain[role+'_horizon'],direction['azimuth_deg'],direction['elevation_deg'],.1)
                    track_samples.append({'epoch_utc':epoch,'state':state,'direction':direction,
                        'classification':status,'classification_reason':reason})
                tracks.append({'target':target,'target_definition':('synthetic_two_body_lunar_preset' if target in presets else state['provenance_label']),
                    'observer_role':role,'observer_height_m':getattr(site,role+'_height_m'),'samples':track_samples,
                    **({'trajectory_assumptions':presets[target].provenance} if target in presets else {})})
            if progress:
                progress('contact_construction')
            edges = []
            if 'direct_to_earth' in scenario['route_families']:
                edges.extend((lander,node,'direct_to_earth') for node in stations)
            if 'single_lunar_relay' in scenario['route_families']:
                for relay in presets:
                    edges.append((lander,relay,'lander_to_relay'))
                    edges.extend((relay,node,'relay_to_earth') for node in stations)
            geometry_cache = {}
            def sample_states(epoch):
                if epoch in records:
                    return
                states = {'EARTH':geometry.state('EARTH',epoch),
                    lander:_state(lander,epoch,site.position_m(site.antenna_height_m),'published_LOLA_resolved_site_explicit_antenna_height')}
                states.update({node:geometry.station_state(profile,epoch) for node,profile in stations.items()})
                for node,preset in presets.items():
                    inertial=preset.state(epoch)
                    states[node]=_state(node,epoch,geometry.transform_position(inertial['position'],epoch),preset.label)
                records[epoch]=states
            def assess_epoch(sender, receiver, epoch):
                key = sender,receiver,epoch
                if key in geometry_cache:
                    return geometry_cache[key]
                sample_states(epoch)
                a,b = [np.asarray(records[epoch][node]['position']) for node in (sender,receiver)]
                if receiver in stations:
                    elevation = _station_elevation(geometry,stations[receiver],a,b,epoch)
                    if elevation < stations[receiver]['minimum_elevation_deg']+.1:
                        result = {'status':'blocked','reason':'station_below_minimum_elevation_plus_margin','station_elevation_deg':elevation}
                        geometry_cache[key] = result
                        return result
                result = finite_terrain_test(dem,a,b)
                geometry_cache[key] = result
                return result
            for sender,receiver,family in edges:
                _cancel(cancel_event)
                bins = []
                for left,right,mid in zip(epochs,epochs[1:],midpoint_epochs):
                    evidence = [assess_epoch(sender,receiver,epoch) for epoch in (left,mid,right)]
                    statuses = [e['status'] for e in evidence]
                    # Unknown bins are retained as decisions and never carry bytes.
                    status = 'clear' if statuses == ['clear']*3 else ('blocked' if 'blocked' in statuses else 'unknown')
                    unknown_geometry |= status == 'unknown'
                    bins.append({'start':parse_utc(left),'end':parse_utc(right),'status':status,
                        'reasons':sorted(set(e['reason'] for e in evidence))})
                # Refine observed state transitions independently of display sampling.
                # The clear-bin windows below remain inside these event brackets.
                for first,last in zip(all_epochs,all_epochs[1:]):
                    left_status=assess_epoch(sender,receiver,first)['status']
                    right_status=assess_epoch(sender,receiver,last)['status']
                    if left_status == right_status:
                        continue
                    lo,hi=parse_utc(first),parse_utc(last)
                    while (hi-lo).total_seconds()>2:
                        _cancel(cancel_event)
                        middle=lo+(hi-lo)/2
                        if assess_epoch(sender,receiver,format_utc(middle))['status']==left_status:
                            lo=middle
                        else:
                            hi=middle
                    events.append({'sender':sender,'receiver':receiver,'bracket':_window(lo,hi),
                        'before_status':left_status,'after_status':right_status,
                        'boundary_uncertainty_s':(hi-lo).total_seconds(),
                        'method':'bisection_of_observed_sample_state_change_no_short_event_completeness_claim'})
                grouped = []
                for item in bins:
                    if grouped and grouped[-1]['status']==item['status'] and grouped[-1]['end']==item['start']:
                        grouped[-1]['end']=item['end']
                        grouped[-1]['reasons']=sorted(set(grouped[-1]['reasons']+item['reasons']))
                    else:
                        grouped.append(deepcopy(item))
                pairs = _terminal_pairs(profiles[sender],profiles[receiver])
                if not pairs:
                    decisions.append({'candidate_id':f'{sender}-{receiver}','status':'rejected','reasons':['incompatible_terminal_band_or_mode']})
                    continue
                tx,rx,mode = pairs[0]
                for index,item in enumerate(grouped):
                    identifier = f'physical-{sender}-{receiver}-{index}'
                    if item['status'] != 'clear':
                        opportunities.append({'contact_id':identifier,'sender':sender,'receiver':receiver,
                            'source_transmit_window':_window(item['start'],item['end']),
                            'geometry_status':item['status'],'geometry_reason':'; '.join(item['reasons']),
                            'geometry_evidence':{'scope':'sampled_bin_classification','time_step_s':TIME_STEP_S}})
                        decisions.append({'candidate_id':identifier,'status':'unknown' if item['status']=='unknown' else 'rejected','reasons':item['reasons']})
                        continue
                    # Discard half a time bin at each event boundary. This remains
                    # a sampled interval assumption; narrow unobserved events can exist.
                    left,right = item['start']+timedelta(seconds=TIME_STEP_S/2),item['end']-timedelta(seconds=TIME_STEP_S/2)
                    if left >= right:
                        continue
                    ranges = [float(np.linalg.norm(np.asarray(records[e][receiver]['position'])-records[e][sender]['position']))
                              for e in all_epochs if item['start'] <= parse_utc(e) <= item['end']]
                    # Frozen contact schema represents one constant delay. Inflate
                    # the sampled max by one time step at a declared 12 km/s bound.
                    delay = math.ceil((max(ranges)+12000*TIME_STEP_S)/SPEED_OF_LIGHT_M_S*1e6)/1e6
                    candidate = {'contact_id':identifier,'sender':sender,'receiver':receiver,
                        'sender_terminal_id':tx['id'],'receiver_terminal_id':rx['id'],'mode_id':mode,
                        'source_transmit_window':_window(left,right),'rate_method':'assumed_net_rate',
                        'payload_rate_bps':RATES_BPS[family], 'one_way_delay':{'model':'constant_assumed','seconds':delay},
                        'geometry_status':'clear_under_sampling','geometry_reason':'endpoint_midpoint_samples_plus_boundary_guard_assumption',
                        'geometry_evidence':{'scope':'interval_wide','coverage':_window(left,right),'input_class':'assumed',
                            'method':'three_samples_per_declared_time_bin_with_half_bin_boundary_guard_not_continuous_proof'},
                        'pointing_assumption':scenario['pointing_assumption'],'service_assumption_label':scenario['service_assumption_label'],
                        'input_class':'assumed','quality_flags':['real_DE421_ephemeris','real_LOLA_numerical_terrain',
                            'sampled_interval_geometry_assumption','constant_conservative_light_time_assumption',
                            'synthetic_two_body_lunar_preset' if sender in presets or receiver in presets else 'educational_station_proxy_no_service_rights']}
                    assessment = assess_contact(candidate,profiles[sender],profiles[receiver],guard_s=0)
                    contacts.extend(assessment['contacts']); opportunities.append(assessment['opportunity'])
                    occupancy.extend(assessment['endpoint_occupancy'])
                    decisions.append({'candidate_id':identifier,**assessment['decision']})
            for track in tracks:
                if track['target'] in ('SUN','EARTH'):
                    continue
                for sample in track['samples']:
                    key=lander,track['target'],sample['epoch_utc']
                    if key in geometry_cache:
                        evidence=geometry_cache[key]
                        sample['classification']=evidence['status']
                        sample['classification_reason']=evidence['reason']
                        sample['segment_test']=deepcopy(evidence)
            geometry_provenance = deepcopy(geometry.provenance)
            geometry_provenance['transmission_light_time_comparison']=[
                _light_time_comparison(geometry,site,profile,epoch) for profile in stations.values()
                for epoch in (epochs[0],epochs[len(epochs)//2],epochs[-1])] 
        generation = []
        for left,right,mid in zip(epochs,epochs[1:],midpoint_epochs):
            values = [powers[e]['generated_power_w'] for e in (left,mid,right)]
            value = None if any(v is None for v in values) else min(values)
            generation.append({'start_utc':left,'end_utc':right,'generation_w':value,'power_model':'piecewise_constant'})
        assumptions = [
            'Real matched DE421 SPICE states and published LOLA terrain grids; assumed hardware, service, pointing and net radio rates.',
            f'Generation is the minimum of endpoint and midpoint samples per {TIME_STEP_S}-second bin, held constant by assumption; no continuous power guarantee.',
            f'Contacts require clear endpoint and midpoint finite-segment samples per {TIME_STEP_S}-second bin with {TIME_STEP_S/2:g}-second outer guards; unsampled short events may be missed.',
            'Same-epoch geometric rays omit retarded endpoint geometry; a positive constant upper-model delay is separately applied to receiver service and byte arrival.',
            f'Constant contact delay uses maximum sampled geometric range plus {TIME_STEP_S} seconds at an assumed 12 km/s range-rate bound.',
            'Terrain above the reference sphere is bounded by an assumed 12 km global envelope; low-altitude finite ray samples use real numerical DEM values.',
            'Fixed-panel center-ray projection, sampled uniform Sun disk and same-ray spherical Earth eclipse mask; no temperature or self-shadowing model.',
            'Synthetic relay conics omit nonspherical gravity, third bodies and radiation pressure; they are not operational frozen or libration-point orbits.',
            *terrain.get('assumptions',[])]
        warnings = [*terrain.get('warnings',[]),
            'This is an assumed-rate planning simulation, with no RF link closure or operational station/relay access claim.',
            'Geometry and power are discrete sampled approximations; feasible results apply only under these declared assumptions.']
        if len(contacts)>64:
            raise ValueError('Physical contact count exceeds the bounded 64-contact scheduler input')
        for contact in contacts:
            validate_document(contact,'contact')
        provenance = {'model_id':MODEL_ID,'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'geometry':geometry_provenance,'terrain':terrain['provenance'],
            'numerics':{'time_step_s':TIME_STEP_S,'event_guard_s':TIME_STEP_S/2,'rates_bps':RATES_BPS,
                'terrain_envelope_m':TERRAIN_ENVELOPE_M,'inner_body_radius_m':INNER_BODY_RADIUS_M,
                'terrain_segment_step_m':120.0,'terrain_near_extent_m':5000.0,'terrain_near_step_m':5.0,'terrain_clearance_margin_m':0.5,'station_elevation_margin_deg':.1},
            'source_urls':sorted(set(model.get('source_urls',[])) | set(k['source_url'] for k in manifest['kernels']))}
        environment = {'artifact_type':'soma_environment_diagnostic','artifact_version':'0.3.0',
            'scenario_sha256':scenario_sha256(scenario),'scenario_id':scenario['scenario_id'],
            'analysis_point':{**scenario['lander'],'elevation_m':site.elevation_m},'analysis_horizon':scenario['analysis_horizon'],
            'frame':site.frame,'origin':'MOON','position_unit':'m','time_scale':'UTC','horizons':horizons,
            'tracks':tracks,'geometry_events':events,'solar_samples':solar,'power_samples':[powers[e] for e in epochs],
            'contacts':contacts,'opportunities':opportunities,'contact_decisions':decisions,'endpoint_occupancy':occupancy,
            'assumptions':assumptions,'warnings':warnings,'provenance':provenance}
        return {'format_version':'0.4.0','scenario_sha256':scenario_sha256(scenario),'contacts':contacts,
            'generation_bins':generation,'states':[records[e][node] for e in all_epochs for node in scenario['relay_refs']],
            'contacts_complete':not unknown_geometry,
            'generation_complete':all(g['generation_w'] is not None for g in generation),
            'contact_decisions':decisions,'environment':environment,'assumptions':assumptions,
            'warnings':warnings,'provenance':provenance}
    finally:
        dem.close()

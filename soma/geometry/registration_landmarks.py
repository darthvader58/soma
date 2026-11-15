"""Match independently searched terrain features in source and rendered patches."""

import math

import numpy as np


def _peak_band(heights, width, band):
    image = np.asarray(heights).reshape(width, width)
    mask = image >= image.max()-band
    if np.any(mask[[0,-1], :]) or np.any(mask[:, [0,-1]]):
        raise ValueError('Peak is unresolved at the search boundary')
    seen, queue = set(), [tuple(np.unravel_index(np.argmax(image), image.shape))]
    while queue:
        row, col = queue.pop()
        if not (0 <= row < width and 0 <= col < width) or (row,col) in seen or not mask[row,col]:
            continue
        seen.add((row,col))
        queue.extend((row+dr,col+dc) for dr in (-1,0,1) for dc in (-1,0,1) if dr or dc)
    if len(seen) != int(mask.sum()):
        raise ValueError('Several disconnected features share the peak band')
    return mask.ravel()


def match_landmarks(reference, capture):
    """Compare feature centroids; never substitute coordinate rays for a search.

    The source reference and its feature definition are frozen before querying
    the scene. Each renderer peak is found from its own height patch. Sampling
    resolution is a declared allowance in the discrete comparison. It does not
    bound the location of continuous terrain maxima between samples.
    """
    measurement = capture.get('measurement', capture)
    if (measurement.get('status') != 'completed' or measurement.get('asset_id') != 2684829
            or measurement.get('source_frame') != 'MOON_ME_DE421'):
        raise ValueError('Require a completed Moon scene measurement')
    probes = measurement.get('probes', [])
    lookup = {p['id']:p for p in probes}
    if len(lookup) != len(probes):
        raise ValueError('Duplicate measured probe')
    radius = reference['reference_radius_m']
    tolerance = reference['predeclared_tolerance_m']
    grid_allowance = reference['horizontal_grid_resolution_allowance_m']
    if radius != 1737400 or tolerance != 10 or not 0 < grid_allowance <= 5:
        raise ValueError('Unsupported predeclared landmark reference')
    rows, identifiers, used = [], set(), set()
    for landmark in reference['landmarks']:
        if landmark['id'] in identifiers:
            raise ValueError('Duplicate source landmark')
        identifiers.add(landmark['id'])
        samples = landmark['samples']
        width = math.isqrt(len(samples))
        if width*width != len(samples) or width < 5 or width % 2 != 1:
            raise ValueError('Require a complete odd square search patch')
        source, observed, heights, counts = [], [], [], []
        for index, sample in enumerate(samples):
            if (sample['grid_row'],sample['grid_column']) != divmod(index,width) or sample['id'] in used:
                raise ValueError('Incomplete or reused source patch')
            used.add(sample['id'])
            probe = lookup.get(sample['id'])
            if not probe or probe.get('status') != 'measured':
                raise ValueError('Missing mesh samples remain unresolved')
            p, q = np.asarray(sample['source_position_m'],dtype=float), np.asarray(probe['renderer_position_m'],dtype=float)
            if p.shape != (3,) or q.shape != (3,) or not np.isfinite(p).all() or not np.isfinite(q).all():
                raise ValueError('Invalid landmark meter vector')
            lat, lon = math.radians(sample['latitude_deg']), math.radians(sample['longitude_deg_east'])
            expected = (radius+sample['height_m'])*np.array([math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)])
            if np.linalg.norm(expected-p)>1e-6:
                raise ValueError('Source coordinates do not match the declared reference')
            source.append(p);observed.append(q);heights.append(sample['height_m']);counts.append(sample['count'])
        source, observed = np.array(source), np.array(observed)
        source_band = _peak_band(heights,width,landmark['top_band_m'])
        rendered_heights = np.linalg.norm(observed,axis=1)-radius
        rendered_band = _peak_band(rendered_heights,width,landmark['top_band_m'])
        if not np.any(np.asarray(counts)[source_band]>0):
            raise ValueError('Source feature has no measured return support')
        expected, measured = source[source_band].mean(axis=0), observed[rendered_band].mean(axis=0)
        delta = measured-expected
        up = expected/np.linalg.norm(expected)
        radial = float(delta @ up)
        horizontal = float(np.linalg.norm(delta-radial*up))
        residual = float(np.linalg.norm(delta))
        rows.append({'id':landmark['id'],'analysis_position_m':expected.tolist(),
                     'renderer_position_m':measured.tolist(),'residual_m':residual,
                     'radial_residual_m':radial,'resolved_horizontal_residual_m':horizontal,
                     'horizontal_grid_resolution_allowance_m':grid_allowance,
                     'resolution_adjusted_residual_m':residual+grid_allowance,
                     'acceptance_tolerance_m':tolerance,
                     'source_peak_band_pixels':int(source_band.sum()),
                     'renderer_peak_band_pixels':int(rendered_band.sum()),
                     'source_positive_count_peak_pixels':int(np.sum(np.asarray(counts)[source_band]>0)),
                     'passed':residual+grid_allowance<=tolerance})
    if used != set(lookup):
        raise ValueError('Foreign or unused scene samples')
    signs = {(int(np.sign(r['analysis_position_m'][0])),int(np.sign(r['analysis_position_m'][1]))) for r in rows}
    separation = min((math.dist(a['analysis_position_m'],b['analysis_position_m']) for i,a in enumerate(rows) for b in rows[i+1:]),default=0)
    distributed = len(rows)>=4 and signs=={(-1,-1),(-1,1),(1,-1),(1,1)} and separation>=20000
    return {'artifact_type':'soma_terrain_feature_registration','version':'0.1.0',
            'source_frame':'MOON_ME_DE421','renderer_frame':'SOMA_MOON_ME_DE421_CORRECTED_V1',
            'origin':'MOON','position_unit':'m','epoch':None,'time_scale':'static_terrain',
            'tolerance_m':tolerance,'landmarks':rows,'minimum_control_separation_m':separation,
            'distribution_passed':distributed,'registration_passed':distributed and all(r['passed'] for r in rows),
            'warnings':['Horizontal correspondence is resolved at the five-meter search-grid scale; near-zero resolved displacement is not exact lunar geolocation.',
                        'Published interpolated heights identify the surrounding feature; positive-count support is required at its reference peak.',
                        'This validates the corrected representation in the declared region, not the unmodified asset or absolute navigation accuracy.']}

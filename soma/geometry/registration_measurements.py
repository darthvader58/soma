"""Compare radial mesh samples without claiming horizontal registration."""
from copy import deepcopy
import math


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def radial_differences(measurement, reference, *, reference_radius_m=1737400):
    """Return measured radial differences, never a frame-registration verdict.

    A ray seeded at a prescribed longitude/latitude cannot independently find
    a matching terrain feature. These differences therefore do not constitute
    landmark residuals, even when every numerical difference is small.
    """
    if (measurement.get('artifact_type') != 'soma_raw_renderer_measurement'
            or measurement.get('format_version') != '0.1.0'
            or measurement.get('candidate_bridge') != 'identity_for_measurement_only'
            or measurement.get('source_frame') != 'MOON_ME_DE421'):
        raise ValueError('Require the explicit unregistered raw-mesh measurement contract')
    if not _number(reference_radius_m) or reference_radius_m <= 0:
        raise ValueError('Require a finite positive reference radius in meters')
    if not isinstance(reference.get('samples'), list) or not isinstance(measurement.get('probes'), list):
        raise ValueError('Reference samples and measured probes must be arrays')
    samples = {p['id']: p for p in reference['samples']}
    if len(samples) != len(reference['samples']):
        raise ValueError('Duplicate reference identifier')
    identifiers = set()
    rows = []
    for probe in measurement['probes']:
        identifier = probe['id']
        if identifier in identifiers or identifier not in samples:
            raise ValueError('Duplicate or unmatched measured probe identifier')
        identifiers.add(identifier)
        sample = samples[identifier]
        height = sample.get('reference_height_m')
        if height is not None and not _number(height):
            raise ValueError('Reference height must be finite meters or explicit unknown')
        point = probe.get('renderer_position_m')
        if point is not None and (not isinstance(point, list) or len(point) != 3 or not all(_number(v) for v in point)):
            raise ValueError('Renderer sample must be a finite meter vector or unknown')
        if probe.get('status') != 'measured' and point is not None:
            raise ValueError('An unmeasured probe cannot contain a measured position')
        radius = math.hypot(*point) if point is not None else None
        rows.append({'id':identifier, 'renderer_radius_m':radius,
                     'reference_height_m':height,
                     'radial_difference_m':radius-reference_radius_m-height if radius is not None and height is not None else None,
                     'horizontal_landmark_residual_m':None,
                     'reference_quality':deepcopy(sample.get('quality_flags', []))})
    return {'artifact_type':'soma_renderer_radial_diagnostic', 'format_version':'0.1.0',
            'request_id':measurement['request_id'], 'source_frame':'MOON_ME_DE421',
            'renderer_frame':'unregistered_asset_world', 'origin':'MOON', 'position_unit':'m',
            'reference_radius_m':reference_radius_m, 'registration_passed':False,
            'horizontal_correspondence_established':False, 'samples':rows,
            'warnings':['Radial ray queries do not establish independent horizontal terrain-fiducial correspondence.',
                        'A difference can arise from source resolution, pixel sampling, asset conversion or renderer query behavior.',
                        'No visual correction, DEM modification or overlay release is authorized by this diagnostic.']}

from copy import deepcopy
import pytest
from soma.geometry.registration_measurements import radial_differences


def inputs():
    return ({'artifact_type':'soma_raw_renderer_measurement','format_version':'0.1.0',
             'candidate_bridge':'identity_for_measurement_only','source_frame':'MOON_ME_DE421',
             'request_id':'test','probes':[{'id':'a','status':'measured','renderer_position_m':[1737410,0,0]}]},
            {'samples':[{'id':'a','reference_height_m':3,'quality_flags':['published_reference']}]} )


def test_radial_difference_is_not_a_horizontal_registration_claim():
    measured, reference = inputs()
    result = radial_differences(measured, reference)
    assert result['samples'][0]['radial_difference_m'] == 7
    assert result['samples'][0]['horizontal_landmark_residual_m'] is None
    assert not result['registration_passed']
    assert not result['horizontal_correspondence_established']


@pytest.mark.parametrize('missing', ['reference', 'renderer'])
def test_unknown_remains_distinct_from_zero(missing):
    measured, reference = inputs()
    if missing == 'reference':
        reference['samples'][0]['reference_height_m'] = None
    else:
        measured['probes'][0].update(status='no_hit',renderer_position_m=None)
    assert radial_differences(measured, reference)['samples'][0]['radial_difference_m'] is None


@pytest.mark.parametrize('bad', ['duplicate', 'foreign', 'nonfinite', 'unmeasured', 'false_bridge'])
def test_invalid_or_misattributed_measurements_are_rejected(bad):
    measured, reference = inputs()
    if bad == 'duplicate': measured['probes'].append(deepcopy(measured['probes'][0]))
    if bad == 'foreign': measured['probes'][0]['id'] = 'unmatched'
    if bad == 'nonfinite': measured['probes'][0]['renderer_position_m'][0] = float('nan')
    if bad == 'unmeasured': measured['probes'][0]['status'] = 'not_measured'
    if bad == 'false_bridge': measured['candidate_bridge'] = 'registered'
    with pytest.raises(ValueError): radial_differences(measured, reference)

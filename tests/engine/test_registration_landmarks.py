from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from soma.geometry.registration_landmarks import match_landmarks


DATA=Path(__file__).resolve().parents[2]/'data'


def inputs():
    return (json.loads((DATA/'renderer-landmark-reference.manifest.json').read_text()),
            json.loads((DATA/'renderer-landmark-capture.manifest.json').read_text()))


def test_independently_found_peaks_pass_with_grid_allowance():
    reference,capture=inputs();result=match_landmarks(reference,capture)
    assert result['registration_passed'] and len(result['landmarks'])==4
    assert result['minimum_control_separation_m']>20000
    assert all(0<p['residual_m']<.3 and p['resolution_adjusted_residual_m']<4 for p in result['landmarks'])


@pytest.mark.parametrize('error',['horizontal','radial','missing','duplicate','boundary'])
def test_wrong_geometry_or_unresolved_features_cannot_release(error):
    reference,capture=inputs();probes=capture.get('measurement',capture)['probes'];width=21
    if error=='duplicate':probes.append(deepcopy(probes[0]))
    elif error=='missing':probes[0].update(status='no_hit',renderer_position_m=None)
    else:
        values=np.array([p['renderer_position_m'] for p in probes[:width*width]])
        unit=values/np.linalg.norm(values,axis=1)[:,None]
        height=np.linalg.norm(values,axis=1)
        if error=='radial':height+=20
        else:height=np.roll(height.reshape(width,width),3 if error=='horizontal' else 10,axis=1).ravel()
        for p,v in zip(probes,unit*height[:,None]):p['renderer_position_m']=v.tolist()
    if error in ('missing','duplicate','boundary'):
        with pytest.raises(ValueError):match_landmarks(reference,capture)
    else:
        result=match_landmarks(reference,capture)
        assert not result['registration_passed']
        assert result['landmarks'][0]['residual_m']>10

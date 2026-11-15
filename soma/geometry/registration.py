"""Versioned evidence for unresolved raw tiles and a verified corrected scene."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sysconfig


MANIFEST_NAME = "renderer-registration.manifest.json"


def _data_directory():
    local = Path(__file__).resolve().parents[2] / "data"
    if (local / MANIFEST_NAME).is_file():
        return local
    return Path(sysconfig.get_path("data")) / "share" / "soma" / "data"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def catalog_reference_position_m(latitude_deg, longitude_deg_east, reference_radius_m):
    """Algebraic sphere candidate, not a DE421 or Cesium landmark position.

    Input catalog angles are evaluated on a declared sphere (where graphic and
    centric latitude coincide). Origin is MOON, units m, epoch/time scale are
    not applicable to this static catalog construction. No terrain height or
    control-network transformation is inferred.
    """
    if not all(_number(v) for v in (latitude_deg, longitude_deg_east, reference_radius_m)):
        raise ValueError("catalog sphere requires finite numeric values")
    if not -90 <= latitude_deg <= 90 or not -180 <= longitude_deg_east < 180 or reference_radius_m <= 0:
        raise ValueError("invalid catalog sphere coordinates")
    lat, lon = math.radians(latitude_deg), math.radians(longitude_deg_east)
    c = 0.0 if abs(latitude_deg) == 90 else math.cos(lat)
    return [reference_radius_m*c*math.cos(lon), reference_radius_m*c*math.sin(lon), reference_radius_m*math.sin(lat)]


def validate_renderer_registration(manifest):
    """Validate archived unresolved evidence or the reviewed regional bridge.

    Version 0.2 applies to corrected static terrain only. Dynamic spacecraft
    states require their own time-tagged frame transformation.
    """
    if isinstance(manifest, dict) and manifest.get('version') == '0.2.0':
        return _validate_registered(manifest)
    required = {"version", "authority", "status", "source_frame", "renderer_frame", "asset_id",
                "origin", "position_unit", "epoch", "time_scale", "transform_column_major",
                "transform_meaning", "source_manifest_ref", "source_manifest_sha256", "source_bindings",
                "tolerance_m", "tolerance_justification", "landmarks", "distribution_review", "release_gate"}
    if not isinstance(manifest, dict) or not required <= manifest.keys():
        raise ValueError("registration artifact is missing required metadata")
    expected = {"version": "0.1.0", "authority": "soma_engine", "status": "blocked_pending_asset_registration",
                "source_frame": "MOON_ME_DE421", "asset_id": 2684829, "origin": "MOON", "position_unit": "m",
                "renderer_frame": None, "epoch": None, "time_scale": "not_applicable_static_catalog",
                "transform_column_major": None, "tolerance_m": None}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("unresolved registration cannot assert a frame, transform, tolerance or release")
    digest = manifest["source_manifest_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("source manifest requires a SHA-256 digest")
    landmarks = manifest["landmarks"]
    if not isinstance(landmarks, list) or len(landmarks) < 4:
        raise ValueError("at least four candidate landmarks are required")
    ids = set()
    for point in landmarks:
        if not isinstance(point, dict) or not {"id", "source_ref", "catalog_coordinates", "catalog_reference_position_m", "analysis_position_m", "renderer_position_m", "residual_m"} <= point.keys():
            raise ValueError("landmark metadata is incomplete")
        if not isinstance(point["id"], str) or not point["id"] or point["id"] in ids:
            raise ValueError("landmarks require distinct IDs")
        ids.add(point["id"])
        if any(point[key] is not None for key in ("analysis_position_m", "renderer_position_m", "residual_m")):
            raise ValueError("unmeasured landmark positions and asset residuals must remain null")
        catalog = point["catalog_coordinates"]
        candidate = catalog_reference_position_m(catalog["latitude_deg"], catalog["longitude_deg_east"], catalog["reference_radius_m"])
        actual = point["catalog_reference_position_m"]
        if not isinstance(actual, list) or len(actual) != 3 or not all(_number(v) for v in actual) or math.dist(candidate, actual) > 1e-6:
            raise ValueError("catalog sphere Cartesian construction is inconsistent")
    review = manifest["distribution_review"]
    gate = manifest["release_gate"]
    if review.get("accepted") is not False or gate.get("overlays_allowed") is not False or not gate.get("blockers"):
        raise ValueError("unresolved registration must block overlays and retain blockers")
    return deepcopy(manifest)


def _validate_registered(manifest):
    expected = {'authority':'soma_engine','status':'registered_for_region',
                'source_frame':'MOON_ME_DE421','renderer_frame':'SOMA_MOON_ME_DE421_CORRECTED_V1',
                'asset_id':2684829,'origin':'MOON','position_unit':'m',
                'representation':'engine_corrected_mesh','epoch':None,
                'time_scale':'not_applicable_static_terrain','tolerance_m':10}
    if any(manifest.get(k)!=v for k,v in expected.items()):
        raise ValueError('Unsupported corrected renderer registration')
    identity=[1 if i%5==0 else 0 for i in range(16)]
    if manifest.get('transform_column_major')!=identity or not manifest.get('tolerance_justification'):
        raise ValueError('Corrected representation requires its explicit identity bridge and tolerance')
    for key in ('source_manifest_sha256','conversion_manifest_sha256'):
        value=manifest.get(key)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Registration requires pinned source and conversion hashes')
    if manifest.get('certified_region')!={'latitude_deg':[-90,-87.5],'longitude_deg_east':[-180,180]}:
        raise ValueError('Unsupported registration coverage')
    for key in ('conversion_manifest_ref','evidence_manifest_ref','source_manifest_ref'):
        if not isinstance(manifest.get(key),str) or Path(manifest[key]).name!=manifest[key]:
            raise ValueError('Registration manifests must be sibling data files')
    landmarks=manifest.get('landmarks')
    if not isinstance(landmarks,list) or len(landmarks)<4:
        raise ValueError('Require four measured feature controls')
    identifiers,quadrants=set(),set()
    for point in landmarks:
        if not point.get('id') or point['id'] in identifiers or not point.get('source_ref'):
            raise ValueError('Measured landmarks require distinct identifiers and sources')
        identifiers.add(point['id'])
        p,q=point.get('analysis_position_m'),point.get('renderer_position_m')
        if any(not isinstance(v,list) or len(v)!=3 or not all(_number(x) for x in v) for v in (p,q)):
            raise ValueError('Measured landmark positions must be finite meter vectors')
        residual=point.get('residual_m');bound=point.get('horizontal_grid_resolution_allowance_m')
        if (not _number(residual) or not _number(bound) or not 0<bound<=5 or residual<0
                or not math.isclose(math.dist(p,q),residual,abs_tol=1e-6,rel_tol=1e-8)
                or residual+bound>manifest['tolerance_m']):
            raise ValueError('Landmark residual or sampling bound fails the declared tolerance')
        latitude=math.degrees(math.atan2(p[2],math.hypot(*p[:2])))
        if not -90<=latitude<=-87.5:
            raise ValueError('Landmark is outside the certified region')
        quadrants.add((1 if p[0]>0 else -1,1 if p[1]>0 else -1))
    if quadrants!={(-1,-1),(-1,1),(1,-1),(1,1)} or min(math.dist(a['analysis_position_m'],b['analysis_position_m']) for i,a in enumerate(landmarks) for b in landmarks[i+1:])<20000:
        raise ValueError('Landmark distribution does not cover the polar region')
    gate=manifest.get('release_gate',{})
    allowed=manifest.get('scope_application',{}).get('site_inside_certified_region') is not False
    if (gate.get('overlays_allowed') is not allowed or gate.get('map_registration_passed') is not allowed
            or manifest.get('distribution_review',{}).get('accepted') is not True
            or not manifest['distribution_review'].get('evidence_ref')):
        raise ValueError('Corrected registration review has not passed')
    return deepcopy(manifest)


@lru_cache(maxsize=4)
def _feature_proof(reference_text,capture_text):
    from soma.geometry.registration_landmarks import match_landmarks
    return match_landmarks(json.loads(reference_text),json.loads(capture_text))


def load_renderer_registration(path=None):
    """Load immutable-by-copy evidence and verify pinned local source bindings."""
    path = Path(path) if path is not None else _data_directory() / MANIFEST_NAME
    manifest = validate_renderer_registration(json.loads(path.read_text()))
    references = [{"path": manifest["source_manifest_ref"], "sha256": manifest["source_manifest_sha256"]}, *manifest["source_bindings"]]
    for ref in references:
        name = ref["path"]
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("registration source bindings must be sibling manifest names")
        if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError(f"registration source checksum mismatch: {name}")
    if manifest['version']=='0.2.0':
        conversion_name=manifest['conversion_manifest_ref']
        if Path(conversion_name).name!=conversion_name or hashlib.sha256((path.parent/conversion_name).read_bytes()).hexdigest()!=manifest['conversion_manifest_sha256']:
            raise ValueError('Corrected renderer conversion checksum mismatch')
        conversion=json.loads((path.parent/conversion_name).read_text())
        if conversion.get('status')!='validated_for_region' or conversion.get('asset_id')!=2684829:
            raise ValueError('Renderer conversion has not passed its regional review')
        evidence=json.loads((path.parent/manifest['evidence_manifest_ref']).read_text())
        root=path.parent.parent
        for binding in evidence['files']:
            name=binding['path']
            if name.startswith('soma/'):
                boundary=Path(__file__).resolve().parents[1]
                target=(boundary/name.removeprefix('soma/')).resolve()
            else:
                boundary=root.resolve()
                target=(boundary/name).resolve()
            if not target.is_relative_to(boundary) or hashlib.sha256(target.read_bytes()).hexdigest()!=binding['sha256']:
                raise ValueError('Registration evidence checksum mismatch')
        reference_text=(root/evidence['reference_path']).read_text()
        capture_text=(root/evidence['capture_path']).read_text()
        capture=json.loads(capture_text)
        if 'conversion' in capture:
            measured_model=capture['conversion']['model']
            keys=('version','asset_id','asset_revision_path','semimajor_m','eccentricity_squared',
                  'reference_radius_m','global_root_scale')
            if (any(measured_model.get(k)!=conversion.get(k) for k in keys)
                    or measured_model['geoid']['sha256']!=conversion['geoid']['sha256']):
                raise ValueError('Approved conversion differs from the measured scene parameters')
        elif capture.get('conversion_manifest_sha256')!=manifest['conversion_manifest_sha256']:
            raise ValueError('Measured scene conversion checksum differs from the certificate')
        proof=_feature_proof(reference_text,capture_text)
        if not proof['registration_passed']:
            raise ValueError('Independent terrain feature check did not pass')
        for actual,expected in zip(manifest['landmarks'],proof['landmarks'],strict=True):
            if any(actual[key]!=expected[key] for key in ('id','analysis_position_m','renderer_position_m','residual_m')):
                raise ValueError('Registration certificate differs from recomputed feature measurements')
    return manifest


def registration_release_gate(manifest=None):
    """Return the reviewed display gate without changing the scientific result."""
    checked = load_renderer_registration() if manifest is None else validate_renderer_registration(manifest)
    return deepcopy(checked["release_gate"])


def load_renderer_conversion(manifest=None):
    """Include the pinned display conversion in an auditable run export."""
    checked = load_renderer_registration() if manifest is None else validate_renderer_registration(manifest)
    if checked['version'] != '0.2.0':
        return None
    content = (_data_directory() / checked['conversion_manifest_ref']).read_bytes()
    if hashlib.sha256(content).hexdigest() != checked['conversion_manifest_sha256']:
        raise ValueError('Corrected renderer conversion checksum mismatch')
    return json.loads(content)


def renderer_registration_for_site(lander):
    manifest=load_renderer_registration()
    if manifest['version']=='0.2.0':
        region=manifest['certified_region']
        inside=(region['latitude_deg'][0]<=lander['latitude_deg']<=region['latitude_deg'][1]
                and region['longitude_deg_east'][0]<=lander['longitude_deg_east']<region['longitude_deg_east'][1])
        manifest['scope_application']={'site_inside_certified_region':inside}
        if not inside:
            manifest['release_gate'].update(overlays_allowed=False,map_registration_passed=False,
                blockers=['Site is outside the verified south-polar renderer registration region'])
    return manifest

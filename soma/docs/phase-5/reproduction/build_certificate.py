"""Recompute the regional certificate from pinned source and scene evidence."""
from pathlib import Path
import hashlib,json,math
from soma.geometry.registration_landmarks import match_landmarks

ROOT=Path(__file__).resolve().parents[4];DATA=ROOT/'data';FIXTURE=ROOT/'fixtures/registration'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
reference_path=DATA/'renderer-landmark-reference.manifest.json';capture_path=DATA/'renderer-landmark-capture.manifest.json'
reference=json.loads(reference_path.read_text());capture=json.loads(capture_path.read_text());matches=match_landmarks(reference,capture)
if not matches['registration_passed']:raise ValueError('Cannot issue a failing registration certificate')
transect_reference=json.loads((DATA/'renderer-transect-reference.manifest.json').read_text())['samples']
transect_capture=json.loads((DATA/'renderer-transect-capture.manifest.json').read_text())
transect_capture=transect_capture.get('measurement',transect_capture)
transect_lookup={p['id']:p for p in transect_capture['probes']}
if len(transect_lookup)!=48 or transect_capture['status']!='completed':raise ValueError('Incomplete height transect')
transect_error=max(abs(math.hypot(*transect_lookup[p['id']]['renderer_position_m'])-1737400-p['reference_height_m']) for p in transect_reference)
if transect_error>=.18:raise ValueError('Recorded corrected height transect changed')
source=json.loads((FIXTURE/'inner-polar-5m-positive-reference.json').read_text())['sources']
fit=json.loads((DATA/'renderer-uv-fit.manifest.json').read_text());model=json.loads((DATA/'renderer-conversion.manifest.json').read_text())
for control in model['source_control_tiles']:
    if control['path'] in {x['path'] for x in fit['source_tiles']}:raise ValueError('Landmark tile was used to fit the conversion')
files=['data/renderer-landmark-reference.manifest.json','data/renderer-landmark-capture.manifest.json',
       'data/renderer-conversion.manifest.json','data/renderer-uv-fit.manifest.json',
       'soma/geometry/renderer_mesh.py','soma/geometry/registration_landmarks.py',
       'soma/geometry/registration.py','soma/api/moon.py','soma/exports/display.py',
       'data/renderer-transect-reference.manifest.json','data/renderer-transect-capture.manifest.json']
evidence={'version':'0.1.0','purpose':'Measured corrected Moon representation in the declared south-polar region',
    'registration_passed':True,'reference_path':str(reference_path.relative_to(ROOT)),
    'capture_path':str(capture_path.relative_to(ROOT)),
    'files':[{'path':name,'sha256':sha(ROOT/name)} for name in files],
    'reference_products':source,'parameter_fit_vertices':fit['sample_count'],'parameter_fit_tiles':fit['tile_count'],
    'landmark_tiles_held_out_from_parameter_fit':True,'landmark_search_queries':1764,
    'independent_transect_queries':48,'corrected_transect_max_height_error_m':transect_error,
    'predeclared_tolerance_m':10,'feature_search_sampling_m':5,
    'resolved_residuals_m':[p['residual_m'] for p in matches['landmarks']],
    'maximum_sampling_resolution_adjusted_residual_m':max(p['resolution_adjusted_residual_m'] for p in matches['landmarks']),
    'minimum_control_separation_m':matches['minimum_control_separation_m'],
    'absolute_navigation_accuracy_claimed':False,'unmodified_asset_registered':False,
    'localization_scope':'Discrete five-meter grid-feature comparison; resolution allowance is not a continuous-peak error bound',
    'tested_mesh_geometric_error_m':5.21,
    'source_snapshot_scope':'Root and four held-out control tiles checked at runtime; not a checksum of every streamed object',
    'evidence_ref':'soma/docs/phase-5/map-alignment.md'}
write(DATA/'renderer-alignment-evidence.manifest.json',evidence)
landmarks=[]
for matched,feature in zip(matches['landmarks'],reference['landmarks'],strict=True):
    point=dict(matched);point['name']='LOLA source-defined polar terrain peak '+str(feature['quadrant']+1)
    point['source_ref']='https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEM_875S_5M_JP2.LBL'
    point['source_pixel_center']={k:feature[k] for k in ['source_center_row','source_center_column']}
    point['source_positive_count_peak_pixels']=feature['positive_count_peak_band_pixels']
    p=point['analysis_position_m'];point['coordinates']={'latitude_deg':math.degrees(math.atan2(p[2],math.hypot(*p[:2]))),
        'longitude_deg_east':math.degrees(math.atan2(p[1],p[0])),'elevation_m':math.hypot(*p)-1737400}
    point['reference_interpretation']='Identifiable peak in the pinned published numerical product, with a measured laser-return pixel; inherits source geolocation uncertainty'
    landmarks.append(point)
bindings=['de421-phase2.manifest.json','lola-phase2.manifest.json','renderer-conversion.manifest.json','renderer-alignment-evidence.manifest.json']
certificate={'version':'0.2.0','authority':'soma_engine','status':'registered_for_region',
    'source_frame':'MOON_ME_DE421','renderer_frame':'SOMA_MOON_ME_DE421_CORRECTED_V1','asset_id':2684829,
    'representation':'engine_corrected_mesh','origin':'MOON','position_unit':'m','epoch':None,'time_scale':'not_applicable_static_terrain',
    'transform_column_major':[1 if i%5==0 else 0 for i in range(16)],
    'transform_meaning':'Moon-centered DE421 mean-Earth Cartesian source columns map identically to the corrected renderer. The streamed asset vertices are first converted by the versioned engine display conversion; this identity never applies to raw ion tiles.',
    'source_manifest_ref':'renderer-registration-sources.manifest.json','source_manifest_sha256':sha(DATA/'renderer-registration-sources.manifest.json'),
    'source_bindings':[{'path':p,'sha256':sha(DATA/p)} for p in bindings],
    'conversion_manifest_ref':'renderer-conversion.manifest.json','conversion_manifest_sha256':sha(DATA/'renderer-conversion.manifest.json'),
    'evidence_manifest_ref':'renderer-alignment-evidence.manifest.json','certified_region':model['certified_region'],
    'tolerance_m':10,'tolerance_justification':'Declared before corrected-scene landmark queries: 10 m relative display tolerance for the pinned 5 m source grid and detailed 5.21 m mesh. Resolved grid-feature residual plus a 3.54 m grid-resolution allowance must pass. This is a discrete relative-registration acceptance test, not a bound on continuous-peak localization, absolute navigation accuracy, or uncertainty probability.',
    'landmarks':landmarks,'distribution_review':{'accepted':True,'evidence_ref':'soma/docs/phase-5/map-alignment.md',
        'extent':'Four source-defined terrain peaks across four polar quadrants; minimum separation 57.47 km. Additional 48 height controls span -87.6 to -89.8 degrees.'},
    'release_gate':{'overlays_allowed':True,'map_registration_passed':True,'text_schedule_available':True,'blockers':[]},
    'limitations':['Registration is applied only for latitude -90 to -87.5 degrees in the corrected representation, based on four grid features and 48 height checks at the detailed mesh level; this is not an all-location or all-LOD accuracy guarantee.',
        'The 3.54 m grid-resolution allowance does not bound continuous terrain-peak localization between samples.',
        'Only the root and control tile fingerprints are checked at runtime; other streamed content is not completely checksum-pinned.',
        'LOLA reference and mesh may share source observations. Independent extraction validates the display conversion, not independent absolute geodesy.',
        'Unmodified streamed coordinates remain unregistered. Numerical DEM quality and coverage are independent of rendering.',
        'No spacecraft ephemeris is invented for the synthetic contact-only relay fixture.']}
write(DATA/'renderer-registration.manifest.json',certificate)
write(FIXTURE/'landmarks-matched.json',matches)
print(json.dumps({'registration_passed':True,'residuals_m':evidence['resolved_residuals_m'],'bounded_max_m':evidence['maximum_sampling_resolution_adjusted_residual_m']}))

"""Bounded numerical LOLA terrain models with explicit interpolation policy.

The existing strict RasterDEM API is unchanged. ``published_grid`` uses finite
published interpolated heights as model values, never as measured elevations.
Missing fine-grid coverage can be resolved by the separately identified coarse
LOLA grid; a missing value in both sources remains unknown.
"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
from threading import Lock

import numpy as np

from soma.geometry import SurfacePoint, local_basis, surface_position
from soma.validation import load_json, resource_directory, physical_dataset_manifest
from .dem import DATUM, FRAME, RADIUS_M, RasterDEM, GeographicRasterDEM, TerrainSample
from .horizons import HorizonBand, HorizonProfile, HorizonSampling, HorizonSite, _distances

VERSION = 'physical-published-grid-horizon-1'
INTERPOLATED, COARSE, UNKNOWN, POLAR_PATCH = 1, 2, 4, 8
_PROFILE_CACHE = OrderedDict()
_CACHE_LOCK = Lock()
DEFAULT_SAMPLING = dict(azimuth_step_deg=1, near_step_m=5, far_step_m=120,
                        near_extent_m=5000, extents_m=(100000, 200000, 250000),
                        convergence_tolerance_deg=.01, required_max_extent_m=250000)


def _check_cancel(event):
    if event is not None and event.is_set():
        raise InterruptedError('Planning canceled during numerical terrain preparation')


class _MemoryGrid:
    def __init__(self, source, *, geographic=False):
        self.source_id = source.source_id
        self.geographic = geographic
        self.transform = source._elevation.transform
        self.project = None if geographic else source._project
        # Masks and NaN are retained separately from zero return counts.
        h = source._elevation.read(1, masked=True)
        n = source._counts.read(1, masked=True)
        self.heights = np.asarray(h.data)
        self.counts = np.asarray(n.data)
        self.invalid = np.ma.getmaskarray(h) | np.ma.getmaskarray(n) | ~np.isfinite(h.data) | ~np.isfinite(n.data) | (n.data < 0)
        self.shape = h.shape
        if self.heights.size > 20_000_000:
            raise ValueError('Physical terrain grid exceeds the bounded twenty-million-cell workload')

    def sample_many(self, lat, lon, policy):
        lat, lon = np.broadcast_arrays(np.asarray(lat, dtype=float), np.asarray(lon, dtype=float))
        if not np.all(np.isfinite(lat)) or not np.all(np.isfinite(lon)) or np.any(abs(lat)>90):
            raise ValueError('Terrain coordinates must be finite lunar latitude and longitude')
        x, y = ((lon % 360, lat) if self.geographic else self.project.transform(lon, lat))
        t = self.transform
        col, row = (x-t.c)/t.a-.5, (y-t.f)/t.e-.5
        col = np.where(abs(col-np.rint(col)) < 1e-8, np.rint(col), col)
        row = np.where(abs(row-np.rint(row)) < 1e-8, np.rint(row), row)
        c0, r0 = np.floor(col).astype(int), np.floor(row).astype(int)
        height, count = np.zeros(lat.shape), np.zeros(lat.shape)
        invalid, interpolated = np.zeros(lat.shape, dtype=bool), np.zeros(lat.shape, dtype=bool)
        for dr in (0,1):
            for dc in (0,1):
                rr, cc = r0+dr, c0+dc
                weight = (1-abs(row-rr))*(1-abs(col-cc))
                active = weight > 0
                outside = (rr < 0) | (rr >= self.shape[0])
                if self.geographic:
                    cc = cc % self.shape[1]
                else:
                    outside |= (cc < 0) | (cc >= self.shape[1])
                rr = np.clip(rr, 0, self.shape[0]-1)
                cc = np.clip(cc, 0, self.shape[1]-1)
                missing = outside | self.invalid[rr,cc]
                zero = self.counts[rr,cc] <= 0
                invalid |= active & (missing | (zero if policy == 'strict_measurements' else False))
                interpolated |= active & zero & ~missing
                height += np.where(active & ~missing, weight*self.heights[rr,cc], 0)
                count += np.where(active & ~missing, weight*self.counts[rr,cc], 0)
        height = np.where(invalid, np.nan, height)
        flags = np.where(interpolated, INTERPOLATED, 0).astype(np.uint8)
        flags |= np.where(invalid, UNKNOWN, 0).astype(np.uint8)
        return height, count, flags


class PhysicalDEM:
    """A manifest-selected model, with an explicit fine-to-coarse downgrade.

    Scalar sample flags retain interpolation and spatial-resolution provenance.
    ``close`` releases arrays; no open GDAL objects survive construction.
    """
    frame, reference_radius_m, elevation_datum = FRAME, RADIUS_M, DATUM

    def __init__(self, near, far, *, policy, source_hashes, polar=None):
        if policy not in ('published_grid', 'strict_measurements'):
            raise ValueError('Select published_grid or strict_measurements explicitly')
        self.near, self.far, self.policy, self.polar = near, far, policy, polar
        self.source_hashes = tuple(source_hashes) + (hashlib.sha256((VERSION+policy).encode()).hexdigest(),)
        self.source_id = 'explicit_LOLA_near_far_' + policy

    def sample_many(self, lat, lon, *, policy=None):
        policy = self.policy if policy is None else policy
        height, count, flags = self.near.sample_many(lat, lon, policy)
        missing = ~np.isfinite(height)
        if self.polar is not None and np.any(missing):
            ph,pn,pf = self.polar.sample_many(np.asarray(lat)[missing],np.asarray(lon)[missing],policy)
            height[missing],count[missing],flags[missing] = ph,pn,pf | POLAR_PATCH
            missing = ~np.isfinite(height)
        if np.any(missing):
            fh, fn, ff = self.far.sample_many(np.asarray(lat)[missing], np.asarray(lon)[missing], policy)
            height[missing], count[missing] = fh, fn
            flags[missing] = ff | COARSE
        return height, count, flags

    def sample(self, latitude_deg, longitude_deg_east):
        if not -180 <= longitude_deg_east < 180:
            raise ValueError('Expected east longitude [-180,180)')
        h,n,f = self.sample_many(np.array([latitude_deg]), np.array([longitude_deg_east]))
        flags = ['published_numerical_LOLA_grid', self.policy]
        if f[0] & INTERPOLATED:
            flags.append('published_interpolated_height_not_measured')
        if f[0] & COARSE:
            flags.append('explicit_coarse_resolution_downgrade')
        if f[0] & POLAR_PATCH:
            flags.append('official_5m_polar_coverage_patch')
        if f[0] & UNKNOWN:
            flags.append('missing_terrain_unknown')
        return TerrainSample(None if not np.isfinite(h[0]) else float(h[0]), tuple(flags), float(n[0]), self.source_id)

    def close(self):
        self.near = self.far = self.polar = None


def _safe_file(root, entry):
    path = (root/entry['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Terrain path escapes data_root')
    return path


def open_physical_dem(data_root, near_manifest, far_manifest, *, policy, polar_manifest=None):
    root = Path(data_root).resolve()
    grids, hashes = [], []
    for manifest, cls in ((near_manifest, RasterDEM), (far_manifest, GeographicRasterDEM)):
        files = {x['role']: _safe_file(root,x) for x in manifest['files']}
        # Existing readers validate hashes, frame, CRS, alignment, units and scale.
        with cls(files['elevation'], files['count'], manifest) as source:
            grids.append(_MemoryGrid(source, geographic=cls is GeographicRasterDEM))
            hashes.extend(source.source_hashes)
    polar = None
    if polar_manifest is not None:
        files = {x['role']: _safe_file(root,x) for x in polar_manifest['files']}
        with RasterDEM(files['elevation'],files['count'],polar_manifest) as source:
            polar = _MemoryGrid(source)
            hashes.extend(source.source_hashes)
    return PhysicalDEM(*grids, policy=policy, source_hashes=hashes,polar=polar)


def _profile(dem, site, sampling, *, cancel_event=None):
    _check_cancel(cancel_event)
    key_payload = {'algorithm_version':VERSION,'site':asdict(site),'sampling':asdict(sampling),
                   'source_hashes':dem.source_hashes,'policy':dem.policy}
    key = hashlib.sha256(json.dumps(key_payload,sort_keys=True).encode()).hexdigest()
    with _CACHE_LOCK:
        cached = _PROFILE_CACHE.get(key)
        if cached is not None:
            _PROFILE_CACHE.move_to_end(key)
            return cached[0], deepcopy(cached[1])
    basis = local_basis(site.latitude_deg, site.longitude_deg_east, site.pole_reference_meridian_deg_east)
    observer = surface_position(site.latitude_deg, site.longitude_deg_east, RADIUS_M, site.elevation_m+site.height_m)
    distances = np.asarray(_distances(sampling))
    arc = distances/RADIUS_M
    bands, changes = [], []
    totals = dict(samples=0, interpolated_samples=0, coarse_samples=0, unknown_samples=0,
                  strict_measurements_unknown_samples=0, polar_patch_samples=0)
    for azimuth in np.arange(0,360,sampling.azimuth_step_deg):
        _check_cancel(cancel_event)
        a = math.radians(azimuth)
        tangent = basis[0]*math.sin(a)+basis[1]*math.cos(a)
        unit = basis[2,:,None]*np.cos(arc)+tangent[:,None]*np.sin(arc)
        lat = np.degrees(np.arctan2(unit[2],np.hypot(unit[0],unit[1])))
        lon = (np.degrees(np.arctan2(unit[1],unit[0]))+180)%360-180
        heights,_,quality = dem.sample_many(lat,lon)
        strict,_,_ = dem.sample_many(lat,lon,policy='strict_measurements')
        unknown = int(np.count_nonzero(~np.isfinite(heights)))
        totals['samples'] += len(distances)
        totals['interpolated_samples'] += int(np.count_nonzero(quality & INTERPOLATED))
        totals['polar_patch_samples'] += int(np.count_nonzero(quality & POLAR_PATCH))
        totals['coarse_samples'] += int(np.count_nonzero(quality & COARSE))
        totals['unknown_samples'] += unknown
        totals['strict_measurements_unknown_samples'] += int(np.count_nonzero(~np.isfinite(strict)))
        vectors = unit*(RADIUS_M+heights)-observer[:,None]
        enu = basis @ vectors
        angles = np.degrees(np.arctan2(enu[2],np.hypot(enu[0],enu[1])))
        lower = float(np.nanmax(angles)) if np.any(np.isfinite(angles)) else None
        flags = ['sampled_horizon','no_atmospheric_refraction',dem.policy]
        if np.any(quality & INTERPOLATED):
            flags.append('contains_published_interpolated_heights_not_measurements')
        if np.any(quality & COARSE):
            flags.append('contains_explicit_coarse_resolution_downgrade')
        if unknown or lower is None:
            flags.append('unknown_horizon')
        else:
            levels = [float(np.max(angles[distances<=extent])) for extent in sampling.extents_m]
            change = abs(levels[-1]-levels[-2])
            changes.append(change)
            if change <= sampling.convergence_tolerance_deg:
                flags.append('known_band_extent_converged')
        bands.append(HorizonBand(float(azimuth),None if unknown else lower,lower,unknown,tuple(flags)))
    totals['known_bands_extent_converged'] = bool(changes) and max(changes)<=sampling.convergence_tolerance_deg
    totals['maximum_known_change_deg'] = max(changes) if changes else None
    maximum = max(changes) if len(changes)==len(bands) else None
    profile = HorizonProfile(key,site,sampling,tuple(bands),maximum is not None and maximum<=sampling.convergence_tolerance_deg,
                             maximum,algorithm_version=VERSION)
    for name in ('interpolated','coarse','unknown'):
        totals[name+'_fraction'] = totals[name+'_samples']/totals['samples']
    totals['strict_measurements_unknown_fraction'] = totals['strict_measurements_unknown_samples']/totals['samples']
    with _CACHE_LOCK:
        _PROFILE_CACHE[key] = (profile, deepcopy(totals))
        while len(_PROFILE_CACHE) > 16:
            _PROFILE_CACHE.popitem(last=False)
    return profile, totals


def far_field_envelope(profile, *, maximum_terrain_height_m):
    """Bound omitted terrain using an explicitly assumed global height cap."""
    if not math.isfinite(maximum_terrain_height_m):
        raise ValueError('Far-field envelope height cap must be finite')
    site = profile.site
    outer = site.reference_radius_m+maximum_terrain_height_m
    observer = site.reference_radius_m+site.elevation_m+site.height_m
    if outer <= observer:
        raise ValueError('Far-field envelope requires a maximum radius above the observer')
    extent = profile.sampling.extents_m[-1]
    arc = extent/site.reference_radius_m
    bound = math.degrees(math.atan2(outer*math.cos(arc)-observer,outer*math.sin(arc)))
    known = [b.elevation_deg for b in profile.bands if b.elevation_deg is not None]
    minimum = min(known) if known else None
    return {'maximum_terrain_height_m':maximum_terrain_height_m,'height_cap_input_class':'assumed',
            'omitted_surface_distances_start_m':extent,'maximum_omitted_elevation_deg':bound,
            'minimum_sampled_horizon_deg':minimum,
            'omitted_terrain_cannot_raise_sampled_bands_under_cap':len(known)==len(profile.bands) and minimum>bound,
            'proof_scope':'For terrain radius at most the declared outer radius, apparent elevation is bounded by the outer sphere and decreases beyond this extent. The cap is an assumption, not a measured global guarantee.'}


def resolve_terrain_site(scenario, *, data_root=None, progress=None, cancel_event=None):
    """Resolve the caller's actual site; never relocate it to a favorable pixel.

    Return ``site``, ``dem``, ``antenna_horizon``, ``panel_horizon``, ``complete``,
    ``provenance`` and ``warnings``. The caller owns ``dem.close()``.
    """
    _check_cancel(cancel_event)
    root = Path(data_root or os.environ.get('SOMA_DATA_ROOT', '/private/tmp/soma-phase2-data')).resolve()
    manifest, manifest_path = physical_dataset_manifest(scenario['dataset_manifest_ref'])
    point = scenario['lander']
    lat_bounds = manifest['latitude_bounds_deg']
    lon_bounds = manifest['longitude_bounds_deg_east']
    if not (lat_bounds[0] <= point['latitude_deg'] <= lat_bounds[1] and lon_bounds[0] <= point['longitude_deg_east'] <= lon_bounds[1]):
        raise ValueError('Selected site is outside the explicitly bounded physical terrain region')
    policy = manifest['terrain_policy']
    near = load_json(resource_directory('data')/manifest['near_manifest_ref'])
    far = load_json(resource_directory('data')/manifest['far_manifest_ref'])
    polar_ref = manifest.get('polar_manifest_ref')
    polar = load_json(resource_directory('data')/polar_ref) if polar_ref else None
    sampling = HorizonSampling(**manifest.get('horizon_sampling',DEFAULT_SAMPLING))
    if progress:
        progress('horizon_preparation')
    dem = open_physical_dem(root,near,far,policy=policy,polar_manifest=polar)
    try:
        point = scenario['lander']
        sample = dem.sample(point['latitude_deg'],point['longitude_deg_east'])
        if sample.elevation_m is None:
            raise ValueError('Selected site has unknown terrain in both declared numerical grids')
        site = SurfacePoint.from_lander({**point,'elevation_m':sample.elevation_m})
        if site.reference_radius_m != RADIUS_M:
            raise ValueError('Physical terrain requires the declared 1737400 m reference sphere')
        profiles, quality = {}, {}
        for role,height in (('antenna',site.antenna_height_m),('panel',site.panel_height_m)):
            hs = HorizonSite(site.latitude_deg,site.longitude_deg_east,site.elevation_m,height,
                             site.pole_reference_meridian_deg_east,site.frame,RADIUS_M,site.elevation_datum)
            profiles[role],quality[role] = _profile(dem,hs,sampling,cancel_event=cancel_event)
        warnings = ['Published grid interpolation is modeled terrain, not a measured surface at every pixel.',
                    'Fine-grid gaps use the explicitly declared coarse LOLA grid; both-source gaps remain unknown.',
                    'Extent convergence does not prove radial or angular sampling completeness.']
        if any(not h.converged for h in profiles.values()):
            warnings.append('Terrain horizon unknown or final extent increment exceeds the declared convergence tolerance.')
        return {'site':site,'dem':dem,'antenna_horizon':profiles['antenna'],'panel_horizon':profiles['panel'],
                'complete':all(h.converged for h in profiles.values()),'warnings':warnings,
                'provenance':{'algorithm_version':VERSION,'terrain_policy':policy,
                              'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                              'source_hashes':list(dem.source_hashes),'datasets':[near,far]+([polar] if polar else []),
                              'requested_elevation_m':point['elevation_m'],'resolved_elevation_m':site.elevation_m,
                              'site_quality':asdict(sample),'sampling':asdict(sampling),'sample_quality':quality,
                              'far_field_envelopes':{role:far_field_envelope(profile,maximum_terrain_height_m=manifest['terrain_upper_bound_m']) for role,profile in profiles.items()},
                              'spatial_resolution':{'near_pixel_size_m':near['pixel_size_m'],
                                  'far_pixels_per_degree':far['pixels_per_degree'],
                                  'far_latitude_spacing_m':math.pi*RADIUS_M/(180*far['pixels_per_degree'])}}}
    except BaseException:
        dem.close()
        raise


def acquire_polar_window(data_root, *, manifest=None, cancel_event=None):
    """Reproduce the pinned 2 km PGDA polar patch with bounded HTTP ranges.

    GDAL's remote BigTIFF directory reads fail on this server. Download the small
    directory and exactly four compressed tiles instead, reconstructing a sparse
    temporary parent solely for local GDAL decoding. The sparse file is removed
    on success or failure. Neither the full parent nor resampled data is fetched.
    """
    import struct
    from tempfile import NamedTemporaryFile
    from urllib.request import Request, urlopen
    import rasterio
    from rasterio.windows import Window
    from soma.datasets import _remote_identity, sha256, canonical_raster_profile, verify_raster_artifact

    manifest = manifest or load_json(resource_directory('data')/'physical-polar-window.manifest.json')
    root = Path(data_root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    metadata_size = 396153
    for entry in manifest['files']:
        _check_cancel(cancel_event)
        output = _safe_file(root,entry)
        if output.is_file() and sha256(output)==entry['sha256']:
            continue
        parent = entry['parent']
        url = parent['url']
        if url not in ('https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif',
                        'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldec_87s_5mpp.tif'):
            raise ValueError('Unrecognized official polar terrain source')
        if _remote_identity(url) != parent:
            raise ValueError('Official polar terrain parent changed; review a new manifest')
        transferred = 0
        def bounded_read(start,length):
            nonlocal transferred
            _check_cancel(cancel_event)
            if start < 0 or length <= 0 or start+length > parent['size_bytes'] or transferred+length > 8*1024*1024:
                raise ValueError('Polar extraction exceeds the bounded eight-MiB per-source transfer')
            for attempt in range(3):
                try:
                    request = Request(url,headers={'Range':f'bytes={start}-{start+length-1}'})
                    with urlopen(request,timeout=45) as response:
                        expected = f"bytes {start}-{start+length-1}/{parent['size_bytes']}"
                        if response.status != 206 or response.headers.get('Content-Range') != expected:
                            raise ValueError('Official terrain server did not honor bounded byte range')
                        content = response.read(length+1)
                    if len(content) != length:
                        raise ValueError('Official terrain byte range is incomplete')
                    transferred += length
                    return content
                except (OSError,ValueError):
                    if attempt==2:
                        raise
        metadata = bounded_read(0,metadata_size)
        if metadata[:8] != b'II+\x00\x08\x00\x00\x00':
            raise ValueError('Unexpected polar BigTIFF format')
        offset = struct.unpack_from('<Q',metadata,8)[0]
        count = struct.unpack_from('<Q',metadata,offset)[0]
        if offset != 16 or count != 20:
            raise ValueError('Polar BigTIFF directory revision changed')
        tags = {record[0]:record[1:] for record in (
            struct.unpack_from('<HHQQ',metadata,offset+8+i*20) for i in range(count))}
        if any(tags[tag] != expected for tag,expected in {
                256:(3,1,40000),257:(3,1,40000),322:(3,1,256),323:(3,1,256),
                324:(16,24649,197624),325:(16,24649,432)}.items()):
            raise ValueError('Unexpected polar BigTIFF tiling')
        offsets = struct.unpack_from('<24649Q',metadata,tags[324][2])
        sizes = struct.unpack_from('<24649Q',metadata,tags[325][2])
        window = Window(*entry['source_pixel_window'])
        if tuple(entry['source_pixel_window']) != (19800,19800,400,400):
            raise ValueError('Only the pinned bounded polar window is supported')
        indexes = [row*157+col for row in (77,78) for col in (77,78)]
        temporary = None
        partial = output.with_suffix('.partial.tif')
        try:
            with NamedTemporaryFile(prefix='soma-polar-',suffix='.sparse.tif',dir=root,delete=False) as sparse:
                temporary = Path(sparse.name)
                sparse.truncate(parent['size_bytes'])
                sparse.write(metadata)
                for index in indexes:
                    content = bounded_read(offsets[index],sizes[index])
                    sparse.seek(offsets[index]);sparse.write(content)
            with rasterio.open(temporary) as source:
                values = source.read(1,window=window)
                profile = source.profile.copy()
                profile.update(driver='GTiff',width=400,height=400,count=1,
                               transform=source.window_transform(window),compress='deflate',
                               tiled=True,blockxsize=256,blockysize=256)
                profile = canonical_raster_profile(profile, entry)
                with rasterio.open(partial,'w',**profile) as target:
                    target.write(values,1)
            verify_raster_artifact(partial, values, profile, entry)
            if _remote_identity(url) != parent:
                raise ValueError('Official terrain parent changed during polar extraction')
            partial.replace(output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            partial.unlink(missing_ok=True)
    return manifest

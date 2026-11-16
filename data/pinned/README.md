# Retained NAIF source

`earth_000101_270208_261113.bpc` is an unmodified copy of the Earth-orientation
kernel already pinned by `data/de421-phase2.manifest.json`.

- Original producer/distributor: NASA NAIF / Caltech Jet Propulsion Laboratory.
- Original source: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/earth_000101_270208_261113.bpc>.
- Size: 5,163,008 bytes.
- SHA-256: `6e77690ba455a644e509b0b9cb308b0dec1a7154ceecf3355659b917b21ca45e`.
- Preservation reviewed: 18 November 2026. The original and `a_old_versions` URLs
  returned HTTP 404; the then-current rolling product was a different file.

The [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html), read in full for this
change, permit redistribution of NAIF-distributed kernels when unmodified. The
file's embedded producer comments and attribution are preserved. This permission
is specific to NAIF kernels; it does not apply to the separate Toolkit mirror
restriction or establish redistribution rights for other providers' data.

SOMA's acquisition function verifies these bytes against the original manifest
before copying them to the requested data directory. The hosted build uses that
same function. No scientific input, expected outcome or historic result is
replaced. This file is a retained source, not a generated kernel or a NASA
endorsement of SOMA. All numerical LOLA rasters remain separately acquired inputs.

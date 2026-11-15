# Contact construction

`assess_contact(candidate, sender_profile, receiver_profile, guard_s=...)`
keeps its geometric opportunity separate from emitted frozen-schema contacts.
A candidate supplies interval-wide geometry status and evidence, explicit endpoint
terminal identifiers, mode, net payload rate, constant delay model, ideal-pointing
assumption, input class, and service label. Geometry evidence is a caller assertion:
a single clear geometry sample cannot establish an entire clear interval. The
constructor enforces `geometry_evidence.scope: interval_wide` and a `coverage`
interval containing the proposed source-transmit interval. Missing or partial
evidence cannot produce contact capacity.

The payload interval is the intersection of guarded geometry, sender service after
sender acquisition/before sender teardown, and receiver service after receiver
acquisition/before receiver teardown shifted backward by one-way delay. Acquisition
and teardown must also fit inside the guarded geometric interval. Overlapping
service windows are merged before trimming, avoiding duplicate capacity. Capacity
is floored in bits; the sidecar also gives whole-byte capacity. An assumed net rate
already includes overhead and is never reduced by a second overhead factor.

The endpoint sidecar records setup-inclusive occupancy at both endpoints, payload
last-byte availability, duplex restrictions and electrical loads. Constant
light time is rounded upward to the exported one-microsecond resolution, never
downward. Last-byte
availability excludes receiver teardown; relay processing is a later scheduling
constraint. Contacts are available resources, not a collision-free, energy-feasible
schedule. No radio or battery feasibility is implied here.

`evaluate_geometry` checks one common-epoch finite segment against numerical lunar
terrain, a conservative lunar sphere, optional explicitly declared body spheres
or ellipsoids with a supplied orthonormal rotation into the body's own frame,
and an actual receiving station's explicit Earth-ellipsoid normal transformed into
the common frame. No Earth-center visibility shortcut is used. Missing terrain,
grazing clearance, or exhausted sampling budgets remain unknown. Same-epoch
geometry is an approximation; light-time-corrected event validation is still needed
before tight boundary accuracy can be claimed.

The optional `link_budget={profile,mode}` argument evaluates an explicit bounded
Friis model. The profile declares interval-wide range bound, frequency, RF power,
gains, noise temperature, pointing/polarization/implementation/Earth-atmosphere/
other losses, the telemetry fraction of RF power, provenance and a justified
far-field minimum range. The mode declares gross binary coded-channel rate,
code rate, protocol payload fraction, required Eb/N0 and engineering margin.
The threshold convention is `pre_fec_bits_including_protocol`. Payload rate is
gross rate times code rate times payload fraction, applied once. RF power and
radio electrical demand are separate fields; a radiated power exceeding the
declared transmitter electrical draw returns unknown as inconsistent input. Missing budget inputs return
unknown; a negative remaining margin rejects the interval. A sufficient modeled
margin cannot override blocked geometry, incompatible radios or missing service.
An assumed net rate never receives the modeled-budget fidelity label.

Primary references inspected during implementation of the budget:
[Friis's original paper](https://capmimo.ece.wisc.edu/capmimo_papers/friis_original_1946.pdf),
including its far-field/free-space limitations, and
[DSN 810-005 module 206E section 2.3](https://deepspace.jpl.nasa.gov/dsndocs/810-005/206/206E.pdf)
for telemetry power allocation and bit/symbol SNR conventions, alongside
[module 101I](https://deepspace.jpl.nasa.gov/dsndocs/810-005/101/101I.pdf)
for the separation of gain, noise and pointing inputs. No DSN antenna values,
thresholds or access rights are adopted by default.

Inputs with omitted service, setup, pointing,
terminal mode, delay, or electrical fields return unknown. Zero light time is
accepted only for an explicitly synthetic arithmetic candidate.

Method and scope follow plan/03 and plan/05, particularly their endpoint-time,
finite-segment, and assumed-rate rules. Existing terrain implementation and its
method attribution remain in soma/terrain/horizons.py. Tests are synthetic and
are not lunar mission predictions.

# Independent schedule replay

`replay_schedule(scenario, contacts, allocations, generation_bins,
require_complete=True)` returns JSON with `passed`, structured `errors`,
recomputed histories, reserved storage intervals, unique Earth bytes and the
physical final payload arrival. Invalid input is returned as a failed replay.
It imports neither the optimizer nor its intermediate state.

This implements the independent validation gate in plan Parts 3, 4 and 5.
It treats native contact epochs as source transmit times. Constant light time
is rounded upward to microseconds, then applied to receiver payload occupancy.
Acquisition and teardown expand both endpoint occupancies for service calendars,
terminal duplex conflicts and electrical demand. Setup and teardown explicitly
use the respective profile TX/RX electrical watts. Assumed rates require their
assumed-rate evidence flags; replay cannot establish geometry or RF closure
from a contact record alone.

A chunk retains its identifier and byte range through a single configured
store-and-forward lunar relay. It becomes forwardable only after complete
arrival, receiver processing and any conservatively delayed declared byte
availability. Re-labeling overlapping file bytes cannot bypass duplicate-byte
checks. The entire plan uses one family: direct, or one selected lunar relay.
Earth counts unique file ranges across configured receiving stations; repeated
ranges still fail validation. Final Earth payload arrival, rather than relay
processing or an artificially delayed availability label, determines deadline.
Earth byte availability must exactly equal physical final-payload arrival;
only relay availability may add a conservative delay. Disabled propagation
is accepted only in `synthetic_fixture` analysis, never `terrain_ephemeris`.

Buffer reservations are conservative: the entire incoming chunk occupies room
from first payload arrival until outgoing payload completion. Initial lander
file occupancy begins at data-ready. At simultaneous boundaries releases and
new reservations are aggregated. Ground stations retain delivered bytes through
the analysis horizon, and their individual finite storage is checked.
Each source chunk also has an explicit lander storage interval from data-ready
through outgoing payload completion, so the exported explanation includes its
initial wait on the lander.

Generation must be known, nonnegative, piecewise constant and contiguous over
the entire analysis horizon. Replay independently partitions time at generation
and lander radio events. It integrates base load through the horizon end,
including waiting and time after delivery. Per terminal/direction radio demand
uses occupancy unions; full duplex adds TX and RX. Each interval either charges
or discharges. Surplus is charge-power limited, efficiency is applied only to
stored energy, and capacity overflow is curtailed. Bus-side discharge power is
checked against the declared limit and stored energy decreases by deficit
energy divided by discharge efficiency, consistent with the Phase 3 power
model. Linear monotone intervals allow endpoint checks to bound reserve between
events. Relay and station power remain the explicit external-power assumption
in their profiles; this replay does not infer their batteries.

`tests/engine/test_replay.py` includes the hand-calculated 100 MiB relay schedule,
whole-horizon energy arithmetic, surplus saturation, and deliberately corrupted
capacity, availability, byte identity, storage, radio, band, deadline, service,
energy and malformed-input cases. These are synthetic software tests, not lunar
mission predictions or flight protocol validation.

# Synthetic relay capacity and waiting test

All scenario values and service windows are invented or explicitly assumed.
This is a Phase 1 contract fixture, not a lunar prediction or computed plan.
`scenario.json` embeds all profiles; `contacts.json` lists assumed native
source-transmit windows. `expected.json` is a hand calculation outside the
result schema. Its allocations are examples for later independent replay;
the current planner must still return `unknown`.

100 MiB = 104,857,600 bytes = 838,860,800 bits. The unchanged direct contact
08:50 to 09:10 UTC at 256,000 net payload bits/s carries 307,200,000 bits,
which is insufficient. The additional synthetic relay contacts give:

- Lander to relay, 09:00 to 09:10 at 2,000,000 net payload bits/s:
  1,200,000,000-bit capacity; full-file duration 419.4304 s;
  transmit and receiver occupancy 09:00:00 to 09:06:59.4304 UTC.
- Whole-file chunk waits on the relay from 09:06:59.4304 until 10:00:00 UTC.
  The 104,857,600-byte relay buffer can hold exactly the entire file.
  Reception consumes buffer space while receiving; the listed storage
  interval specifically identifies the wait after complete reception.
- Relay to ground, 10:00 to 10:03 at 10,000,000 net payload bits/s:
  1,800,000,000-bit capacity; duration 83.88608 s;
  transmit and receiver occupancy 10:00:00 to 10:01:23.88608 UTC.

The final byte would arrive before 10:05 under this disabled-delay arithmetic.
Timing and capacity are sufficient only conditional on future energy analysis,
constraint scheduling, and independent replay. No feasibility or optimality
has yet been proved. The entire file is one named chunk with byte offset zero
on both hops: this is forwarding the same bytes, not two datasets delivered.
The hand schedule leaves the direct contact unused.

The lander and station profiles match the direct fixture exactly: finite
200 MiB storage, explicit service calendars, the same lander battery and fixed
panel, and nonzero lander base load. All terminals share the explicitly
synthetic band; each hop's mode appears in both endpoint terminal profiles.
The relay's single half-duplex terminal receives and transmits at disjoint
times. Store-and-forward and finite storage are explicit relay capabilities.
External relay power is an explicit service assumption, not an invented
battery model. Ideal pointing and zero acquisition/teardown/processing are
assumptions; net payload overhead is applied once. Radio electrical draw is
not a statement about radiated RF power. Solar generation is not computed.

Light time is `disabled_for_synthetic_test` solely for hand arithmetic.
Physical propagation delay is additional when enabled. If an assumed uplink
delay were d1 and downlink delay d2 seconds, receiver occupancy shifts by the
respective delay, the full chunk becomes available after uplink completion
plus d1 (and processing), and final delivery shifts by d2 if forwarding still
starts at 10:00. Recheck receiver calendars, occupancy, energy and deadline;
do not assume unchanged feasibility. No actual delays are predicted here.

`synthetic_contact_fixture` supplies no trajectory or physical geometry. It
is neither an operational relay nor a two-body orbit, frozen orbit, or
libration-point ephemeris. The station is an educational proxy with no booked
service. No terrain, Sun, link budget or battery trajectory is evaluated.

Source for the worked arithmetic: repository `plan/03-Communications-Relays-and-Scheduling.md`.

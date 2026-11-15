# Bounded scheduler

`solve_schedule(scenario, contacts, generation_bins, *, chunk_bytes=16777216,
bin_s=5, time_limit_s=15, cancel_event=None)` returns a candidate schedule for
independent replay. Contacts are already assessed usable contact records. Every
generation bin explicitly declares `piecewise_constant`, covers the full analysis
horizon contiguously, and has finite nonnegative generation watts. Unknown
illumination returns unresolved.

PuLP with CBC solves binary chunk/contact/start choices. Exactly one route family
carries the complete dataset: direct to the configured ground network, or through
one configured store-and-forward lunar relay. There are no Earth-orbit relays.
All chunks select exactly one source transmission and, for a relay family,
exactly one causal outgoing transmission. Separate constraints enforce declared
contact bits, terminal compatibility and service, radio occupancy at both ends,
finite relay reservation and ground storage, and deadline arrival of every chunk.

Candidate starts lie on the union of regular bins, contact boundaries, service
boundaries and generation changes. Payload ends round upward to that grid.
Padding consumes radio time and electrical power; it does not create bytes.
Propagation shifts the payload receiver interval; receiver processing shifts chunk
availability. Acquisition and teardown expand terminal reservation and must fit
endpoint service. The frozen receiver interval remains payload-only.

The lander battery is part of the MILP across the entire horizon. Bus-side charge
and discharge are mutually exclusive. A net-power sign branch requires generation
to supply demand first: a deficit has exact bus discharge and no curtailment;
a surplus can charge or curtail with no discharge. The branch bound uses the
configured lander terminal electrical maxima and base demand. The balance includes generation, nonzero
base load, selected terminal electrical load, efficiency, curtailment, finite
capacity, reserve and charge/discharge limits. Terminal occupancy reserves every
intersected grid bin, giving conservative interior power and reserve bounds.
Selected histories are then recomputed on exact selected power-change times.
Relay power is the explicit profile assumption; externally powered ground service
is reported as an assumption because the frozen station profile has no battery.

The policy uses three sequential solves: fewer relay hops, earlier final arrival,
then lower lander communications energy. Each proven objective becomes a bound
before the next solve. The shared wall-time budget bounds solver work. A time
limit with a solver-reported integer solution returns `feasible_incumbent`;
without one it returns `unresolved`. Proven infeasibility applies only to this
discretized, bounded family model. Chunk count is limited to 32, contacts to 64,
regular bins to 5000, candidate allocations to 25000, and candidate-bin pairs to 8000000; excess
returns unresolved.
Cancellation is checked before formulation and between solves. Service workers
can terminate the isolated process during a CBC solve.

The synthetic 100 MiB fixture checks the direct contact's insufficient 307,200,000
bits and the relay's store-and-forward delivery. Perturbations check finite
storage, incompatible radios, service, reserve and discharge power. These are
synthetic assumed-rate calculations, not lunar mission predictions. CBC optimality
does not establish physical fidelity or remove the independent replay gate.

Documentation consulted: [PuLP CBC implementation](https://github.com/coin-or/pulp/blob/master/pulp/apis/coin_api.py)
and [PuLP solution statuses](https://github.com/coin-or/pulp/blob/master/pulp/constants.py).

Chunk-count bounds are checked before materializing chunks, including for enormous
MiB inputs. Boolean and nonfinite scheduling controls and generation are rejected.
The numeric MILP energy-interval snapshot is retained in diagnostics so tests can
check surplus curtailment and exact deficit discharge in the solved formulation.

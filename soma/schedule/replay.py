"""Independent whole-chunk replay of source-epoch contact allocations.

No solver state, buffer history, or energy history is accepted as evidence.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
import math

from soma.time import parse_utc, format_utc
from soma.validation import validate_document, data_volume_bytes


def _interval(value):
    a, b = parse_utc(value['start_utc']), parse_utc(value['end_utc'])
    if a >= b:
        raise ValueError('interval must have positive duration')
    return a, b


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('duration or power must be finite and nonnegative')
    return timedelta(microseconds=int((Decimal(str(value))*1000000).to_integral_value(rounding=ROUND_CEILING)))


def _window(a, b):
    return {'start_utc': format_utc(a), 'end_utc': format_utc(b)}


def replay_schedule(scenario, contacts, allocations, generation_bins, *, require_complete=True):
    """Return errors and independently derived histories, including invalid inputs.

    Incoming chunks reserve their full buffer at first payload arrival, and
    remain reserved until their outgoing payload ends. Setup draws the profile's
    respective TX/RX electrical power. Relay/ground external power is assumed.
    """
    out = dict(passed=False, errors=[], energy_history=[], buffer_history=[],
               storage_intervals=[], delivered_bytes=0, final_byte_arrival_utc=None,
               details={'algorithm': 'independent_whole_chunk_replay_v1',
                        'buffer_conservatism': 'reserve incoming whole chunk at first arrival; release at transmit end',
                        'setup_power_assumption': 'acquisition and teardown draw the respective TX/RX electrical watts',
                        'availability_policy': 'declared availability may conservatively delay physical availability',
                        'external_power': 'relay and station power follows explicit profile assumptions'})

    def error(code, reason, allocation=None):
        item = {'code': code, 'reason': str(reason)}
        if isinstance(allocation, dict) and isinstance(allocation.get('allocation_id'), str):
            item['allocation_id'] = allocation['allocation_id']
        out['errors'].append(item)

    try:
        if not isinstance(contacts, list) or not isinstance(allocations, list):
            raise ValueError('contacts and allocations must be arrays')
        validate_document(scenario, 'scenario')
        begin, finish = _interval(scenario['analysis_horizon'])
        ready, deadline = parse_utc(scenario['data_ready_utc']), parse_utc(scenario['deadline_utc'])
        if not begin <= ready < deadline <= finish:
            raise ValueError('invalid data-ready/deadline/horizon order')
        total = data_volume_bytes(scenario['data_volume'])
        lander = scenario['lander']['id']
        hardware = next(p for p in scenario['profiles']['hardware'] if p['id'] == scenario['hardware_profile_ref'])
        nodes = {lander: hardware}
        for kind, refs in [('relays', 'relay_refs'), ('stations', 'station_refs')]:
            for profile in scenario['profiles'][kind]:
                if profile['id'] in scenario[refs]:
                    if profile['id'] in nodes:
                        raise ValueError('duplicate node identifier')
                    nodes[profile['id']] = profile
        relays, stations = set(scenario['relay_refs']), set(scenario['station_refs'])
        if not stations <= nodes.keys() or not relays <= nodes.keys():
            raise ValueError('unresolved profile reference')
        battery = hardware['battery']
        if not battery['reserve_wh'] <= battery['initial_energy_wh'] <= battery['capacity_wh']:
            raise ValueError('battery initial energy outside reserve/capacity')
        contact_map = {}
        for contact in contacts:
            validate_document(contact, 'contact')
            if contact['contact_id'] in contact_map:
                raise ValueError('duplicate contact identifier')
            _interval(contact['source_transmit_window'])
            contact_map[contact['contact_id']] = contact
    except (ValueError, TypeError, KeyError, StopIteration, OverflowError) as exc:
        error('invalid_input', exc)
        return out

    bins = []
    try:
        previous = begin
        for item in generation_bins:
            a, b = _interval(item)
            power = item['generation_w']
            if item['power_model'] != 'piecewise_constant' or type(power) not in (int, float) or not math.isfinite(power) or power < 0:
                raise ValueError('unknown or unsupported generation input')
            if a != previous or b > finish:
                raise ValueError('generation must be contiguous and cover the entire analysis horizon')
            bins.append((a, b, power))
            previous = b
        if previous != finish or not bins:
            raise ValueError('generation must cover the entire analysis horizon')
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        error('unknown_inputs', exc)
        return out

    records, occupancy, ids, usage = [], [], set(), {}
    for allocation in allocations:
        try:
            validate_document(allocation, 'allocation')
            aid = allocation['allocation_id']
            if aid in ids:
                error('duplicate_allocation', 'allocation identifier repeated', allocation)
            ids.add(aid)
            c = contact_map.get(allocation['contact_id'])
            if c is None:
                error('unknown_contact', 'contact reference does not resolve', allocation)
                continue
            sender, receiver = c['sender'], c['receiver']
            if sender not in nodes or receiver not in nodes:
                raise ValueError('unconfigured endpoint')
            a, b = _interval(allocation['source_transmit_interval'])
            ca, cb = _interval(c['source_transmit_window'])
            delay = _seconds(c['one_way_delay']['seconds'])
            if c['one_way_delay']['model'] == 'disabled_for_synthetic_test' and scenario['analysis_mode'] != 'synthetic_fixture':
                error('disabled_light_time', 'disabled light time is restricted to synthetic fixture analysis', allocation)
            ra, rb = a+delay, b+delay
            if _interval(allocation['receiver_occupancy_interval']) != (ra, rb):
                error('receiver_interval', 'receiver payload interval differs from source plus light time', allocation)
            available = parse_utc(allocation['byte_available_utc'])
            physical = rb + _seconds(nodes[receiver]['processing_delay_s'] if receiver in relays else 0)
            if available < physical:
                error('availability', 'bytes declared available before physical completion/processing', allocation)
            if receiver in stations and available != rb:
                error('earth_availability', 'Earth byte availability must equal physical payload arrival without processing delay', allocation)
            if not begin <= a < b <= finish or ra < begin or rb > finish:
                error('outside_horizon', 'payload occupancy outside analysis horizon', allocation)
            if not ca <= a < b <= cb:
                error('contact_window', 'transmit payload outside contact source window', allocation)
            if sender == lander and a < ready:
                error('before_data_ready', 'source transmits before file is ready', allocation)
            offset, length = allocation['byte_offset'], allocation['byte_length']
            if offset+length > total:
                error('byte_range', 'byte range exceeds source file', allocation)
            bits = length*8
            elapsed = Decimal(str((b-a).total_seconds()))
            if Decimal(bits) > elapsed*Decimal(str(c['payload_rate_bps'])):
                error('payload_capacity', 'payload exceeds integrated net rate', allocation)
            usage[c['contact_id']] = usage.get(c['contact_id'], 0)+bits
            if c['rate_method'] != scenario['rate_method'] or scenario['pointing_assumption'] != 'ideal_pointing' or 'ideal_pointing' not in c['quality_flags']:
                error('contact_assumptions', 'unsupported or inconsistent rate/pointing assumptions', allocation)
            needed = ('assumed_net_rate', 'link_budget_not_computed') if c['rate_method'] == 'assumed_net_rate' else ('modeled_link_budget', 'margin_met_under_declared_assumptions')
            if any(flag not in c['quality_flags'] for flag in needed):
                error('rate_evidence', 'contact lacks required rate evidence flags', allocation)
            terminals = []
            for node, field, left, right, direction in [(sender, 'sender_terminal_id', a, b, 'tx'), (receiver, 'receiver_terminal_id', ra, rb, 'rx')]:
                terminal = next(t for t in nodes[node]['terminals'] if t['id'] == c[field])
                terminals.append(terminal)
                if c['mode_id'] not in terminal['mode_ids']:
                    error('incompatible_mode', 'endpoint mode unsupported', allocation)
                left -= _seconds(terminal['acquisition_s'])
                right += _seconds(terminal['teardown_s'])
                if left < begin or right > finish:
                    error('outside_horizon', 'setup/teardown outside analysis horizon', allocation)
                windows = sorted(_interval(w) for w in nodes[node]['service']['windows'])
                merged = []
                for x, y in windows:
                    if merged and x <= merged[-1][1]:
                        merged[-1] = (merged[-1][0], max(y, merged[-1][1]))
                    else:
                        merged.append((x, y))
                if not any(x <= left and right <= y for x, y in merged):
                    error('service_unavailable', f'{node} lacks service over expanded {direction} occupancy', allocation)
                occupancy.append((node, terminal, direction, left, right, allocation))
            if terminals[0]['band'] != terminals[1]['band']:
                error('incompatible_band', 'endpoint bands differ', allocation)
            records.append(dict(allocation=allocation, sender=sender, receiver=receiver, a=a, b=b, ra=ra, rb=rb,
                                available=available, key=(allocation['chunk_id'], offset, length), offset=offset, length=length))
        except (ValueError, TypeError, KeyError, StopIteration, OverflowError) as exc:
            error('invalid_allocation', exc, allocation)

    for cid, bits in usage.items():
        c = contact_map[cid]
        ca, cb = _interval(c['source_transmit_window'])
        bound = Decimal(str((cb-ca).total_seconds()))*Decimal(str(c['payload_rate_bps']))
        if bits > c['available_capacity_bits'] or Decimal(bits) > bound:
            error('contact_capacity', f'{cid} aggregate capacity exceeded')
    for i, item in enumerate(occupancy):
        node, terminal, direction, a, b, allocation = item
        for n2, t2, d2, x, y, other in occupancy[i+1:]:
            if node == n2 and terminal['id'] == t2['id'] and max(a, x) < min(b, y) and (terminal['duplex'] == 'half_duplex' or direction == d2):
                error('radio_conflict', f"overlaps {other['allocation_id']} at {node}/{terminal['id']}", allocation)

    families, selected = set(), set()
    for r in records:
        s, t = r['sender'], r['receiver']
        if s == lander and t in stations:
            families.add('direct_to_earth')
        elif (s == lander and t in relays) or (s in relays and t in stations):
            families.add('single_lunar_relay')
            selected.add(t if t in relays else s)
        else:
            error('unsupported_route', 'only direct or one lunar store-and-forward relay is supported', r['allocation'])
    if len(families) > 1 or len(selected) > 1 or not families <= set(scenario['route_families']):
        error('route_family', 'plan mixes route families or selected relays, or uses disabled family')
    for node in selected:
        if nodes[node]['behavior'] != 'store_and_forward':
            error('store_and_forward_required', f'{node} cannot hold chunks; bent-pipe replay unsupported')

    # Whole-chunk identity must be preserved through the relay. Different chunk
    # labels never permit overlapping ranges to be injected at the source.
    source_records = [r for r in records if r['sender'] == lander]
    sink_records = [r for r in records if r['receiver'] in stations]
    for group, label in [(source_records, 'source'), (sink_records, 'earth')]:
        for i, r in enumerate(group):
            for q in group[i+1:]:
                if max(r['offset'], q['offset']) < min(r['offset']+r['length'], q['offset']+q['length']):
                    error('duplicate_bytes', f'overlapping file bytes at {label}', q['allocation'])
    chunk_ranges = {}
    for r in records:
        chunk = r['key'][0]
        if chunk in chunk_ranges and chunk_ranges[chunk] != r['key'][1:]:
            error('chunk_identity', 'chunk identifier has inconsistent byte range', r['allocation'])
        chunk_ranges[chunk] = r['key'][1:]
        if r['sender'] in relays:
            incoming = [q for q in records if q['receiver'] == r['sender'] and q['key'] == r['key']]
            if len(incoming) != 1 or incoming[0]['available'] > r['a']:
                error('causality', 'whole matching chunk unavailable at relay transmit start', r['allocation'])

    # Capacity reservation differs deliberately from byte availability: a
    # receiver must have room before receiving, not merely after the last byte.
    events = {node: [(begin, 0)] for node in nodes}
    events[lander].append((ready, total))
    for r in records:
        if r['sender'] == lander and ready < r['b']:
            out['storage_intervals'].append({'node_id': lander, 'chunk_id': r['key'][0],
                'byte_length': r['length'], 'interval': _window(ready, r['b'])})
        events[r['sender']].append((r['b'], -r['length']))
        events[r['receiver']].append((r['ra'], r['length']))
        outgoing = [q for q in records if q['sender'] == r['receiver'] and q['key'] == r['key']]
        end = outgoing[0]['b'] if len(outgoing) == 1 else finish
        if r['ra'] < end:
            out['storage_intervals'].append({'node_id': r['receiver'], 'chunk_id': r['key'][0],
                'byte_length': r['length'], 'interval': _window(r['ra'], end)})
    for node, changes in events.items():
        level = 0
        for epoch in sorted({t for t, _ in changes} | {finish}):
            level += sum(delta for t, delta in changes if t == epoch)
            if level < 0:
                error('buffer_underflow', f'{node} releases bytes absent from buffer')
            if level > nodes[node]['storage_capacity_bytes']:
                error('storage_overflow', f'{node} finite storage exceeded')
            out['buffer_history'].append({'node_id': node, 'epoch_utc': format_utc(epoch), 'stored_bytes': max(0, level)})

    ranges = sorted((r['offset'], r['offset']+r['length']) for r in sink_records)
    merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    out['delivered_bytes'] = sum(b-a for a, b in merged)
    if sink_records:
        arrival = max(r['rb'] for r in sink_records)
        out['final_byte_arrival_utc'] = format_utc(arrival)
        if arrival > deadline:
            error('deadline', 'last payload byte arrives after deadline')
    if require_complete and out['delivered_bytes'] != total:
        error('incomplete_delivery', 'Earth unique bytes differ from complete file size')

    energy = battery['initial_energy_wh']
    out['energy_history'].append({'node_id': lander, 'epoch_utc': format_utc(begin), 'stored_energy_wh': energy})
    boundaries = {begin, finish}
    for a, b, _ in bins:
        boundaries.update((a, b))
    for node, terminal, direction, a, b, allocation in occupancy:
        if node == lander:
            boundaries.update((max(begin, min(finish, a)), max(begin, min(finish, b))))
    times = sorted(boundaries)
    for a, b in zip(times, times[1:]):
        generation = next(w for x, y, w in bins if x <= a < y)
        active = {(t['id'], d): t[f'{d}_electrical_w'] for n, t, d, x, y, _ in occupancy if n == lander and x <= a < y}
        load = hardware['base_load_w'] + sum(active.values())
        surplus = generation-load
        hours = (b-a).total_seconds()/3600
        if surplus >= 0:
            energy = min(battery['capacity_wh'], energy+min(surplus, battery['max_charge_w'])*battery['charge_efficiency']*hours)
        else:
            deficit = -surplus
            if deficit > battery['max_discharge_w']+1e-9:
                error('discharge_power', f'bus-side discharge power exceeded at {format_utc(a)}')
            energy -= deficit*hours/battery['discharge_efficiency']
        if energy < battery['reserve_wh']-1e-9:
            error('energy_reserve', f'energy below reserve at {format_utc(b)}')
        out['energy_history'].append({'node_id': lander, 'epoch_utc': format_utc(b), 'stored_energy_wh': max(0, energy)})
    out['passed'] = not out['errors']
    return out

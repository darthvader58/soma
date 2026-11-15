"""Bounded chunk MILP for direct and single lunar store-and-forward families."""
from bisect import bisect_left
from datetime import timedelta
import math
import time

from soma.time import parse_utc, format_utc
from soma.power import integrate_battery


def solve_schedule(scenario, contacts, generation_bins, *, chunk_bytes=16777216,
                   bin_s=5, time_limit_s=15, cancel_event=None):
    """Solve a conservative discretized model; the caller must independently replay it."""
    import pulp
    output = dict(solver_status='unresolved', allocations=[], storage_intervals=[],
                  energy_history=[], buffer_history=[], delivered_bytes=None,
                  final_byte_arrival_utc=None, assumptions=[], warnings=[], details={})
    def stop(reason, status='unresolved'):
        output['solver_status'] = status
        output['warnings'].append(reason)
        return output
    if cancel_event is not None and cancel_event.is_set():
        return stop('canceled_before_scheduling')
    if isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int) or chunk_bytes <= 0:
        raise ValueError('chunk_bytes must be a positive integer')
    for value, name in ((bin_s, 'bin_s'), (time_limit_s, 'time_limit_s')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be a finite number')
    if bin_s <= 0:
        raise ValueError('bin_s must be positive')
    if time_limit_s <= 0:
        return stop('solver_time_limit_without_incumbent')
    origin = parse_utc(scenario['analysis_horizon']['start_utc'])
    seconds = lambda value: (parse_utc(value)-origin).total_seconds()
    stamp = lambda value: format_utc(origin+timedelta(seconds=value))
    interval = lambda a,b: {'start_utc': stamp(a), 'end_utc': stamp(b)}
    horizon = seconds(scenario['analysis_horizon']['end_utc'])
    ready, deadline = seconds(scenario['data_ready_utc']), seconds(scenario['deadline_utc'])
    if horizon <= 0 or not math.isfinite(horizon/bin_s) or math.ceil(horizon/bin_s) > 5000:
        return stop('bounded_model_limit: maximum 5000 scheduling bins')
    generation = []
    cursor = 0.
    for item in generation_bins:
        a,b = seconds(item['start_utc']),seconds(item['end_utc'])
        g = item['generation_w']
        if item.get('power_model') != 'piecewise_constant' or a != cursor or b <= a:
            return stop('generation_requires_contiguous_explicit_piecewise_constant_horizon')
        if g is None:
            return stop('unknown_generation_prevents_energy_constraint')
        if isinstance(g, bool) or not isinstance(g,(int,float)) or not math.isfinite(g) or g < 0:
            raise ValueError('generation_w must be finite and nonnegative')
        generation.append((a,b,g)); cursor=b
    if cursor != horizon:
        return stop('generation_does_not_cover_analysis_horizon')
    lander = scenario['lander']['id']
    hardware = next(p for p in scenario['profiles']['hardware'] if p['id']==scenario['hardware_profile_ref'])
    profiles = {lander: hardware}
    profiles.update({p['id']:p for p in scenario['profiles']['relays'] if p['id'] in scenario['relay_refs']})
    profiles.update({p['id']:p for p in scenario['profiles']['stations'] if p['id'] in scenario['station_refs']})
    stations = set(scenario['station_refs'])
    relays = set(scenario['relay_refs'])
    total = scenario['data_volume']['value'] * (1048576 if scenario['data_volume']['unit']=='MiB' else 1)
    chunk_count = (total + chunk_bytes - 1) // chunk_bytes
    if chunk_count > 32 or len(contacts)>64:
        return stop('bounded_model_limit: maximum 32 chunks and 64 contacts')
    chunks = [(offset,min(chunk_bytes,total-offset)) for offset in range(0,total,chunk_bytes)]
    if hardware['storage_capacity_bytes'] < total:
        return stop('lander_initial_file_exceeds_storage', 'proven_infeasible_discretized_model')
    output['assumptions'] = [
        'Whole dataset uses direct contacts or one selected lunar store-and-forward relay; Earth-orbit relays disabled.',
        'Payload durations rounded upward to an event-grid boundary; padded payload occupancy consumes declared radio power.',
        'Radio conflicts and electrical loads conservatively reserve every intersected event bin.',
        'Acquisition and teardown use the terminal TX or RX electrical draw respectively.',
        'Relay buffer reserves a complete chunk at reception start and releases it after outgoing payload completion.',
        'Ground sink retains all received chunks with finite configured station storage.',
        'Policy: satisfy deadline and constraints, then fewer relay hops, earlier final arrival, lower lander communications energy.'
    ]
    for relay in relays:
        output['assumptions'].append(profiles[relay]['power_assumption_label'])
    output['assumptions'].append('Ground stations use externally powered service; station battery/base loads are outside the frozen profile.')
    events={0.,horizon,ready,deadline}
    events.update(min(horizon,i*bin_s) for i in range(math.ceil(horizon/bin_s)+1))
    for a,b,_ in generation: events.update((a,b))
    for c in contacts:
        events.update(seconds(c['source_transmit_window'][key]) for key in ('start_utc','end_utc'))
    for p in profiles.values():
        for w in p['service']['windows']: events.update(seconds(w[key]) for key in ('start_utc','end_utc'))
    grid=sorted(t for t in events if 0<=t<=horizon)
    candidates=[]
    for ci,c in enumerate(contacts):
        if c['sender'] not in profiles or c['receiver'] not in profiles: continue
        sender,receiver=profiles[c['sender']],profiles[c['receiver']]
        tx=next((t for t in sender['terminals'] if t['id']==c['sender_terminal_id']),None)
        rx=next((t for t in receiver['terminals'] if t['id']==c['receiver_terminal_id']),None)
        if tx is None or rx is None or tx['band']!=rx['band'] or any(c['mode_id'] not in t['mode_ids'] for t in (tx,rx)): continue
        if c['sender']==lander and c['receiver'] in stations and 'direct_to_earth' in scenario['route_families']: family='direct'
        elif 'single_lunar_relay' in scenario['route_families'] and ((c['sender']==lander and c['receiver'] in relays) or (c['sender'] in relays and c['receiver'] in stations)):
            family=c['receiver'] if c['sender']==lander else c['sender']
            if profiles[family]['behavior']!='store_and_forward': continue
        else: continue
        delay=c['one_way_delay']['seconds']
        if c['one_way_delay']['model'] not in ('constant_assumed','disabled_for_synthetic_test'): return stop('unsupported_delay_model')
        left,right=(seconds(c['source_transmit_window'][key]) for key in ('start_utc','end_utc'))
        for k,(offset,size) in enumerate(chunks):
            duration=size*8/c['payload_rate_bps']
            for start in grid:
                if start < max(left,ready) or start+duration>right+1e-9: continue
                j=bisect_left(grid,start+duration-1e-9)
                if j==len(grid): continue
                end=grid[j]
                if end>right+1e-9: continue
                arrival=end+delay
                available=arrival+receiver.get('processing_delay_s',0)
                if arrival>deadline or available>horizon: continue
                occupancies=[]
                valid=True
                for node,terminal,mode,a,b in ((c['sender'],tx,'tx',start-tx['acquisition_s'],end+tx['teardown_s']), (c['receiver'],rx,'rx',start+delay-rx['acquisition_s'],arrival+rx['teardown_s'])):
                    if a<0 or b>horizon or not any(seconds(w['start_utc'])<=a and seconds(w['end_utc'])>=b for w in profiles[node]['service']['windows']): valid=False; break
                    occupancies.append((node,terminal,mode,a,b))
                if valid:
                    candidates.append(dict(ci=ci,k=k,size=size,start=start,end=end,arrival=arrival,available=available,family=family,occ=occupancies))
    if len(candidates)>25000 or len(candidates)*(len(grid)-1)>8000000:
        return stop('bounded_model_limit: maximum 25000 candidates and 8000000 candidate-bin pairs')
    output['details'].update(candidate_count=len(candidates), chunk_bytes=chunk_bytes,bin_s=bin_s, generation_bins=generation_bins)
    model=pulp.LpProblem('soma_delivery',pulp.LpMinimize)
    x=[pulp.LpVariable(f'x{i}',cat='Binary') for i in range(len(candidates))]
    families=sorted({v['family'] for v in candidates})
    y={f:pulp.LpVariable(f'family{j}',cat='Binary') for j,f in enumerate(families)}
    model += pulp.lpSum(y.values())==1
    for k in range(len(chunks)):
        for f in families:
            for source in ([lander] if f=='direct' else [lander,f]):
                model += pulp.lpSum(x[i] for i,v in enumerate(candidates) if v['k']==k and v['family']==f and contacts[v['ci']]['sender']==source)==y[f]
            if f!='direct':
                model += pulp.lpSum(x[i]*(v['start'] if contacts[v['ci']]['sender']==f else -v['available']) for i,v in enumerate(candidates) if v['k']==k and v['family']==f)>=0
    # Equal-size chunks are interchangeable; chronological ordering removes symmetry.
    for k in range(len(chunks)-1):
        if chunks[k][1] != chunks[k+1][1]:
            continue
        for source in [lander]+sorted(relays):
            model += pulp.lpSum(x[i]*v['start'] for i,v in enumerate(candidates) if v['k']==k and contacts[v['ci']]['sender']==source) <= pulp.lpSum(x[i]*v['start'] for i,v in enumerate(candidates) if v['k']==k+1 and contacts[v['ci']]['sender']==source)
    for ci,c in enumerate(contacts): model += pulp.lpSum(x[i]*v['size']*8 for i,v in enumerate(candidates) if v['ci']==ci)<=c['available_capacity_bits']
    completion=pulp.LpVariable('completion',0,horizon)
    for i,v in enumerate(candidates):
        if contacts[v['ci']]['receiver'] in stations: model += completion>=v['arrival']*x[i]
    # Reserve resources on the grid, including any partial overlap.
    loads=[[] for _ in grid[:-1]]
    for j,(a,b) in enumerate(zip(grid,grid[1:])):
        occupancy={}
        for i,v in enumerate(candidates):
            for node,t,mode,left,right in v['occ']:
                if left < b-1e-9 and right > a+1e-9:
                    key=(node,t['id'],'both' if t['duplex']=='half_duplex' else mode)
                    occupancy.setdefault(key,[]).append(x[i])
                    if node==lander: loads[j].append(x[i]*t[f'{mode}_electrical_w'])
        for values in occupancy.values(): model += pulp.lpSum(values)<=1
        for node,p in profiles.items():
            if node==lander: continue
            terms=[]
            for i,v in enumerate(candidates):
                c=contacts[v['ci']]
                if c['receiver']==node and v['start']+c['one_way_delay']['seconds']<b-1e-9: terms.append(x[i]*v['size'])
                if c['sender']==node and v['end']<=a+1e-9: terms.append(-x[i]*v['size'])
            model += pulp.lpSum(terms)<=p['storage_capacity_bytes']
    battery=hardware['battery']; cap=battery['capacity_wh']
    energy=[pulp.LpVariable(f'e{j}',battery['reserve_wh'],cap) for j in range(len(grid))]
    model += energy[0]==battery['initial_energy_wh']
    maximum_demand = hardware['base_load_w'] + sum(
        t['tx_electrical_w'] + t['rx_electrical_w'] if t['duplex']=='full_duplex'
        else max(t['tx_electrical_w'], t['rx_electrical_w'])
        for t in hardware['terminals'])
    battery_bins = []
    for j,(a,b) in enumerate(zip(grid,grid[1:])):
        gen=next(g for left,right,g in generation if left<=a and right>=b)
        charge=pulp.LpVariable(f'charge{j}',0,battery['max_charge_w'])
        discharge=pulp.LpVariable(f'discharge{j}',0,battery['max_discharge_w'])
        spill=pulp.LpVariable(f'spill{j}',0,gen)
        charging=pulp.LpVariable(f'charging{j}',cat='Binary')
        model += charge<=battery['max_charge_w']*charging
        model += discharge<=battery['max_discharge_w']*(1-charging)
        demand = hardware['base_load_w'] + pulp.lpSum(loads[j])
        surplus = gen - demand
        # The sign branch makes generation serve demand before storage can discharge.
        model += surplus >= -maximum_demand*(1-charging)
        model += surplus <= gen*charging
        model += spill <= gen*charging
        model += gen+discharge==demand+charge+spill
        battery_bins.append((a,b,gen,demand,charge,discharge,spill))
        model += energy[j+1]==energy[j]+(b-a)/3600*(charge*battery['charge_efficiency']-discharge/battery['discharge_efficiency'])
    comm_energy=pulp.lpSum(x[i]*sum((b-a)*t[f'{mode}_electrical_w']/3600 for node,t,mode,a,b in v['occ'] if node==lander) for i,v in enumerate(candidates))
    started=time.monotonic(); selected=None; optimal=True
    for objective in (pulp.lpSum(y[f] for f in families if f!='direct'),completion,comm_energy):
        if cancel_event is not None and cancel_event.is_set(): return stop('canceled_during_scheduling')
        remaining=time_limit_s-(time.monotonic()-started)
        if remaining<=0: optimal=False; break
        model.setObjective(objective)
        model.solve(pulp.PULP_CBC_CMD(msg=False,timeLimit=remaining,threads=1,options=['randomSeed 1']))
        solution_status=getattr(model,'sol_status',None)
        if model.status==pulp.LpStatusInfeasible:
            if selected is not None:
                optimal=False
                output['warnings'].append('Later policy solve contradicted an earlier incumbent; retaining incumbent for independent replay.')
                break
            return stop('No complete dataset schedule satisfies the declared discrete route, capacity, storage, service, radio and energy constraints.', 'proven_infeasible_discretized_model')
        if solution_status not in (pulp.LpSolutionOptimal,pulp.LpSolutionIntegerFeasible):
            optimal=False; break
        selected=[i for i,value in enumerate(x) if value.value() is not None and value.value()>0.5]
        output['details']['milp_energy_intervals'] = [dict(
            **interval(a,b), generation_w=gen, electrical_load_w=pulp.value(demand),
            charge_bus_w=charge.value(), discharge_bus_w=discharge.value(),
            curtailed_bus_w=spill.value())
            for a,b,gen,demand,charge,discharge,spill in battery_bins]
        if solution_status!=pulp.LpSolutionOptimal: optimal=False; break
        model += objective<=(pulp.value(objective) or 0.)+1e-7
    if selected is None: return stop('solver_stopped_without_feasible_incumbent')
    chosen=[candidates[i] for i in selected]
    output['solver_status']='proven_optimum' if optimal else 'feasible_incumbent'
    output['delivered_bytes']=total
    output['final_byte_arrival_utc']=stamp(max(v['arrival'] for v in chosen if contacts[v['ci']]['receiver'] in stations))
    for i,v in enumerate(sorted(chosen,key=lambda v:(v['start'],v['k']))):
        c=contacts[v['ci']]; offset,size=chunks[v['k']]
        output['allocations'].append(dict(allocation_id=f'allocation-{i}',chunk_id=f'chunk-{v["k"]}',byte_offset=offset,byte_length=size,contact_id=c['contact_id'],source_transmit_interval=interval(v['start'],v['end']),receiver_occupancy_interval=interval(v['start']+c['one_way_delay']['seconds'],v['arrival']),byte_available_utc=stamp(v['available'])))
    for k,(offset,size) in enumerate(chunks):
        hops=sorted((v for v in chosen if v['k']==k),key=lambda v:v['start'])
        output['storage_intervals'].append(dict(node_id=lander,chunk_id=f'chunk-{k}',byte_length=size,interval=interval(ready,hops[0]['end'])))
        if len(hops)==2:
            first,last=hops
            output['storage_intervals'].append(dict(node_id=contacts[first['ci']]['receiver'],chunk_id=f'chunk-{k}',byte_length=size,interval=interval(first['start']+contacts[first['ci']]['one_way_delay']['seconds'],last['end'])))
    # Histories use exact selected occupancy edges, independently of conservative MILP bins.
    exact={0.,horizon}
    for a,b,g in generation: exact.update((a,b))
    for v in chosen:
        for node,t,mode,a,b in v['occ']:
            if node==lander: exact.update((a,b))
    exact=sorted(exact); power=[]
    for a,b in zip(exact,exact[1:]):
        load=sum(t[f'{mode}_electrical_w'] for v in chosen for node,t,mode,left,right in v['occ'] if node==lander and left<b-1e-9 and right>a+1e-9)
        power.append(dict(**interval(a,b),generation_w=next(g for left,right,g in generation if left<=a and right>=b),incremental_load_w=load,power_model='piecewise_constant'))
    traced=integrate_battery(battery,power,base_load_w=hardware['base_load_w'])
    output['energy_history']=[dict(node_id=lander,**sample) for sample in traced['samples']]
    output['details']['energy_intervals']=traced['intervals']
    times=sorted({0.,horizon,ready}|{t for v in chosen for t in (v['start']+contacts[v['ci']]['one_way_delay']['seconds'],v['end'])})
    for t in times:
        for node in profiles:
            count=total if node==lander and t>=ready else 0
            for v in chosen:
                c=contacts[v['ci']]
                if c['receiver']==node and v['start']+c['one_way_delay']['seconds']<=t+1e-9: count+=v['size']
                if c['sender']==node and v['end']<=t+1e-9: count-=v['size']
            output['buffer_history'].append(dict(node_id=node,epoch_utc=stamp(t),stored_bytes=count))
    return output

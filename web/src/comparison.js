const known = value => value !== undefined && value !== null && value !== '';
const display = value => {
  if (!known(value)) return 'Unknown';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
};
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const hardware = scenario => scenario?.profiles?.hardware?.find(item => item.id === scenario.hardware_profile_ref);
const network = scenario => ({
  relays: scenario.relay_refs,
  stations: scenario.station_refs,
  routes: scenario.route_families,
  relayProfiles: scenario.profiles?.relays,
  stationProfiles: scenario.profiles?.stations,
  rate: scenario.rate_method,
  pointing: scenario.pointing_assumption,
  service: scenario.service_assumption_label,
});

export function comparisonViewModel(entries = []) {
  const selected = entries.slice(0, 2);
  const rows = selected.map(({ name, scenario = {}, result, summary }) => {
    const supplied = summary?.artifact_type === 'soma_run_summary' && summary?.format_version === '0.4.0'
      && /^[a-f0-9]{64}$/.test(summary.scenario_sha256 ?? '')
      && summary.scenario_sha256 === result?.scenario_sha256 && summary.status === result?.status
      && summary.solver_status === result?.solver_status && result?.status === 'feasible_under_assumptions'
      && summary.replay?.passed === true ? summary : undefined;
    return ({
    name,
    status: result?.status,
    solver: result?.solver_status,
    fidelity: result?.model_fidelity,
    route: Array.isArray(supplied?.route_nodes) ? supplied.route_nodes.join(' → ') : undefined,
    wait: supplied?.mean_relay_wait_s,
    energy: supplied?.lander_communications_energy_wh,
    minimumReserve: supplied?.minimum_margin_above_reserve_wh,
    completion: result?.final_byte_arrival_utc,
    limitingReason: result?.provenance?.reason,
    scenario,
  });
  });
  const a = selected[0]?.scenario;
  const b = selected[1]?.scenario;
  const differences = [];
  if (a && b) {
    const checks = [
      ['Data volume', a.data_volume, b.data_volume],
      ['Deadline (fixed absolute UTC)', a.deadline_utc, b.deadline_utc],
      ['Hardware profile', a.hardware_profile_ref, b.hardware_profile_ref],
      ['Hardware configuration', hardware(a), hardware(b)],
      ['Initial battery energy (Wh)', hardware(a)?.battery?.initial_energy_wh, hardware(b)?.battery?.initial_energy_wh],
      ['Network configuration', network(a), network(b)],
    ];
    for (const [label, left, right] of checks) {
      const equal = label.startsWith('Deadline') ? sameDisplayEpoch(left, right) : same(left, right);
      differences.push({ label, left, right, changed: !equal, unknown: !known(left) || !known(right) });
    }
  }
  return {
    rows,
    differences,
    dateChanged: !!a && !!b && !sameDisplayEpoch(a.data_ready_utc, b.data_ready_utc),
    deadlineChanged: !!a && !!b && !sameDisplayEpoch(a.deadline_utc, b.deadline_utc),
  };
}

export function renderComparison(container, { entries = [] }) {
  const el = (tag, value) => {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = display(value);
    return node;
  };
  function render() {
    container.replaceChildren();
    container.classList.add('comparison-display');
    const model = comparisonViewModel(entries);
    container.append(el('p', 'Two saved engine results. Comparison does not rank sites or run an analysis. Missing engine metrics remain Unknown.'));
    if (model.rows.length !== 2) {
      container.append(el('p', 'Save two scenario results to inspect task differences.'));
    }
    container.append(el('p', 'Deadline rule: fixed absolute UTC. No deadline moves automatically with the data-ready date.'));
    if (model.dateChanged) {
      container.append(el('p', model.deadlineChanged
        ? 'Data-ready time changed; the absolute deadline also changed.'
        : 'Data-ready time changed; the absolute deadline is unchanged.'));
    }
    const wrapper = el('div');
    wrapper.className = 'science-table-scroll';
    const table = el('table');
    const head = el('thead');
    const headings = el('tr');
    for (const label of ['Engine output', ...model.rows.map(row => row.name)]) {
      const th = el('th', label);
      th.scope = 'col';
      headings.append(th);
    }
    head.append(headings);
    table.append(head);
    const body = el('tbody');
    const metrics = [
      ['Delivery status', 'status'],
      ['Solver status', 'solver'],
      ['Model fidelity', 'fidelity'],
      ['Selected route', 'route'],
      ['Final byte arrival (UTC)', 'completion'],
      ['Mean relay wait per byte (s)', 'wait'],
      ['Communications energy (Wh)', 'energy'],
      ['Minimum margin above reserve (Wh)', 'minimumReserve'],
      ['Limiting reason', 'limitingReason'],
    ];
    for (const [label, key] of metrics) {
      const tr = el('tr');
      const th = el('th', label);
      th.scope = 'row';
      tr.append(th);
      for (const row of model.rows) tr.append(el('td', display(row[key])));
      body.append(tr);
    }
    table.append(body);
    wrapper.append(table);
    container.append(wrapper, el('h3', 'Task controls'));
    const controls = el('ul');
    for (const item of model.differences) {
      const status = item.unknown ? 'Unknown' : item.changed ? 'Changed' : 'Unchanged';
      const values = ['Hardware configuration', 'Network configuration'].includes(item.label)
        ? 'Inspect the saved scenario JSON for the complete configuration.'
        : `${display(item.left)} / ${display(item.right)}`;
      const line = el('li', `${item.label}: ${status}. ${values}`);
      if (item.changed) line.className = 'comparison-changed';
      controls.append(line);
    }
    container.append(controls);
    container.append(el('p', 'Changed task controls prevent attributing an outcome to site or date alone. Metrics read a versioned, scenario-matched Python summary; missing summaries remain Unknown. Relay wait is a byte-weighted mean after chunk availability and before forwarding.'));
  }
  render();
  return {
    setEntries(value) { entries = value; render(); },
    destroy() { container.replaceChildren(); },
  };
}
import { sameDisplayEpoch } from './display-time.js';


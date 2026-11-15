"""Independent linear Friis arithmetic and contact-gate checks."""

from copy import deepcopy
import math

import pytest

from soma.links import link_budget, assess_contact
from soma.validation import load_json, validate_document


def budget_inputs():
    profile = dict(range_bound_m=1e6, far_field_min_range_m=10000, frequency_hz=8e9,
                   tx_rf_power_w=10, tx_gain_dbi=30, rx_gain_dbi=40,
                   system_noise_temperature_k=100, data_power_fraction=0.8,
                   losses_db=dict(pointing=1, polarization=0.5, implementation=1.5, earth_atmosphere=0, other=0),
                   provenance_label="SYNTHETIC RF test; not an operational antenna",
                   coverage=dict(start_utc="2026-11-14T08:50:00Z", end_utc="2026-11-14T09:10:00Z"))
    mode = dict(mode_id="synthetic-direct-256k", gross_channel_bps=2e6, code_rate=0.5,
                payload_fraction=0.8, required_ebn0_db=3, engineering_margin_db=2,
                threshold_bit_rate_definition="pre_fec_bits_including_protocol")
    return profile, mode


def test_friis_and_noise_match_independent_linear_power_arithmetic():
    p, mode = budget_inputs()
    report = link_budget(p, mode)
    wavelength = 299792458 / p['frequency_hz']
    received_w = p['tx_rf_power_w']*1000*10000*(wavelength/(4*math.pi*p['range_bound_m']))**2 / 10**0.3
    ratio = received_w*0.8/(1.380649e-23*100*1e6)
    assert report['received_rf_power_dbw'] == pytest.approx(10*math.log10(received_w))
    assert report['ebn0_db'] == pytest.approx(10*math.log10(ratio))
    assert report['payload_rate_bps'] == 800000
    assert report['remaining_margin_db'] == pytest.approx(10*math.log10(ratio)-5)
    p['range_bound_m'] *= 2
    assert link_budget(p, mode)['remaining_margin_db'] == pytest.approx(report['remaining_margin_db']-20*math.log10(2))


def candidate():
    scenario = load_json('fixtures/synthetic-direct/scenario.json')
    c = load_json('fixtures/synthetic-direct/contacts.json')[0]
    c.update(rate_method='link_budget', geometry_status='clear_under_sampling',
             geometry_reason='synthetic_interval_geometry_assumption',
             geometry_evidence={'scope':'interval_wide', 'coverage':deepcopy(c['source_transmit_window'])},
             pointing_assumption='ideal_pointing', input_class='synthetic', service_assumption_label='Synthetic service')
    return c, scenario['profiles']['hardware'][0], scenario['profiles']['stations'][0]


def test_budget_contacts_require_geometry_and_margin_and_apply_overhead_once():
    c, sender, receiver = candidate()
    p, mode = budget_inputs()
    kwargs = dict(guard_s=0, link_budget=dict(profile=p, mode=mode))
    result = assess_contact(c, sender, receiver, **kwargs)
    contact = result['contacts'][0]
    validate_document(contact, 'contact')
    assert contact['payload_rate_bps'] == 800000
    assert contact['available_capacity_bits'] == 800000*1200
    assert result['model_fidelity'] == 'modeled_link_budget'
    assert 'assumed_net_rate' not in contact['quality_flags']
    mode['required_ebn0_db'] = 100
    assert assess_contact(c, sender, receiver, **kwargs)['decision']['reasons'] == ['insufficient_link_margin']
    c['geometry_status'] = 'blocked'
    assert not assess_contact(c, sender, receiver, **kwargs)['contacts']


def test_missing_noise_near_field_or_wrong_threshold_convention_is_not_closure():
    p, mode = budget_inputs()
    del p['system_noise_temperature_k']
    with pytest.raises(KeyError):
        link_budget(p, mode)
    p, mode = budget_inputs()
    p['range_bound_m'] = 1
    with pytest.raises(ValueError, match='far-field'):
        link_budget(p, mode)
    p, mode = budget_inputs()
    mode['threshold_bit_rate_definition'] = 'payload_bits'
    with pytest.raises(ValueError, match='pre-FEC'):
        link_budget(p, mode)


def test_rf_power_cannot_exceed_the_declared_transmitter_electrical_draw():
    c, sender, receiver = candidate()
    p, mode = budget_inputs()
    p['tx_rf_power_w'] = 1000
    report = assess_contact(c, sender, receiver, guard_s=0, link_budget=dict(profile=p, mode=mode))
    assert report['contacts'] == []
    assert report['decision']['reasons'] == ['radiated_power_exceeds_declared_radio_electrical_draw']

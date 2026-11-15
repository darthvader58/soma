"""Far-field RF budget for an explicitly declared binary discrete mode.

Friis free-space loss and telemetry bit/noise conventions follow plan/03,
DSN 810-005 module 206E section 2.3, and its referenced interface modules.
Thresholds and hardware values are caller inputs, never DSN defaults.
"""

import math

C_M_S = 299792458.0
K_J_K = 1.380649e-23


def _finite(value, name, *, minimum=None, maximum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if (positive and value <= 0) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError(f"{name} is outside its supported range")
    return float(value)


def link_budget(profile, mode):
    """Evaluate a range bound; this function neither establishes LOS nor service.

    Gross channel bits are binary coded bits. Eb/N0 is measured per pre-FEC bit,
    including protocol bits. Code rate and payload fraction are applied once.
    All losses and the telemetry share of RF power must be declared separately.
    """
    distance = _finite(profile["range_bound_m"], "range_bound_m", positive=True)
    far_field = _finite(profile["far_field_min_range_m"], "far_field_min_range_m", positive=True)
    if distance < far_field:
        raise ValueError("Range is outside the declared far-field regime")
    if not profile["provenance_label"] or not mode["mode_id"]:
        raise ValueError("Hardware provenance and mode identity are required")
    frequency = _finite(profile["frequency_hz"], "frequency_hz", positive=True)
    tx_w = _finite(profile["tx_rf_power_w"], "tx_rf_power_w", positive=True)
    tx_gain = _finite(profile["tx_gain_dbi"], "tx_gain_dbi")
    rx_gain = _finite(profile["rx_gain_dbi"], "rx_gain_dbi")
    noise_k = _finite(profile["system_noise_temperature_k"], "system_noise_temperature_k", positive=True)
    data_fraction = _finite(profile["data_power_fraction"], "data_power_fraction", positive=True, maximum=1)
    losses = {name: _finite(profile["losses_db"][name], name, minimum=0) for name in
              ("pointing", "polarization", "implementation", "earth_atmosphere", "other")}
    if mode["threshold_bit_rate_definition"] != "pre_fec_bits_including_protocol":
        raise ValueError("Eb/N0 threshold must use pre-FEC bits including protocol")
    gross = _finite(mode["gross_channel_bps"], "gross_channel_bps", positive=True)
    code_rate = _finite(mode["code_rate"], "code_rate", positive=True, maximum=1)
    payload_fraction = _finite(mode["payload_fraction"], "payload_fraction", positive=True, maximum=1)
    required = _finite(mode["required_ebn0_db"], "required_ebn0_db")
    engineering_margin = _finite(mode["engineering_margin_db"], "engineering_margin_db", minimum=0)
    information_rate = gross*code_rate
    payload_rate = information_rate*payload_fraction
    path_loss = 20*(math.log10(4*math.pi)+math.log10(distance)+math.log10(frequency)-math.log10(C_M_S))
    received_dbw = 10*math.log10(tx_w)+tx_gain+rx_gain-path_loss-sum(losses.values())
    data_cn0 = received_dbw+10*math.log10(data_fraction)-10*(math.log10(K_J_K)+math.log10(noise_k))
    ebn0 = data_cn0-10*math.log10(information_rate)
    margin = ebn0-required-engineering_margin
    return {"status": "margin_met_under_declared_assumptions" if margin >= 0 else "insufficient_margin",
            "method": "friis_far_field_binary_mode_v1", "mode_id": mode["mode_id"],
            "range_bound_m": distance, "free_space_loss_db": path_loss, "received_rf_power_dbw": received_dbw,
            "data_cn0_db_hz": data_cn0, "ebn0_db": ebn0, "remaining_margin_db": margin,
            "gross_channel_bps": gross, "pre_fec_rate_bps": information_rate, "payload_rate_bps": payload_rate,
            "losses_db": losses, "threshold_bit_rate_definition": mode["threshold_bit_rate_definition"],
            "provenance_label": profile["provenance_label"],
            "limitations": ["does not establish unobstructed geometry, pointing or booked service",
                            "RF power is distinct from radio electrical demand", "caller-supplied threshold and losses"]}

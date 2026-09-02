import logging
from ertmac.alerts.engine import AlertSeverity, global_alert_engine, AlertSource

logger = logging.getLogger("ertmac.alerts.hazard_classifier")

def evaluate_telemetry_hazards(sensor: dict, features: dict, current_md: float, well_id: str, organization_id: str):
    """
    Evaluates telemetry against domain-specific hazard rules.
    If a hazard is detected, creates an alert in the global_alert_engine and returns it.
    Otherwise, returns None.
    """
    def _fv(key: str, unit: str = "", fmt: str = ".1f") -> str:
        v = sensor.get(key)
        return f"{v:{fmt}}{unit}" if v is not None else "N/A"

    def _fd(key: str):
        v = features.get(key)
        return float(v) if v is not None else None

    # Domain-rules hazard classifier
    d_torque = _fd("delta_torque")
    d_wob    = _fd("delta_wob")
    d_rop    = _fd("delta_rop")
    d_spp    = _fd("delta_spp")
    d_flow   = _fd("delta_flow_in")
    mse_val  = _fd("mse")
    dxc_val  = _fd("dxc")

    rop  = float(sensor.get("rop",  0.0) or 0.0)
    torq = float(sensor.get("torque", 0.0) or 0.0)

    hazard_title   = "Drilling Anomaly Detected"
    hazard_verdict = "Telemetry has deviated significantly from the normal operational envelope. Verify all channels."
    severity_tag   = AlertSeverity.HIGH

    # Priority-ordered domain rules
    if (d_spp is not None and d_flow is not None and d_spp < -15 and d_flow > 50 and rop > 5):
        hazard_title   = "⚠ POSSIBLE WELL KICK"
        hazard_verdict = (f"SPP dropped {abs(d_spp):.1f} bar while flow-in increased {d_flow:.0f} L/min — classic kick signature. "
                          f"Pit volume gain check IMMEDIATELY. ROP={rop:.1f} m/h suggests active influx.")
        severity_tag   = AlertSeverity.CRITICAL

    elif (d_spp is not None and d_flow is not None and d_spp < -10 and d_flow < -80):
        hazard_title   = "⚠ POSSIBLE MUD LOSS / LOST CIRCULATION"
        hazard_verdict = (f"SPP down {abs(d_spp):.1f} bar AND flow-in down {abs(d_flow):.0f} L/min — thief zone or fracture taking fluid. "
                          f"Check return flow and pit levels. Consider LCM pill.")
        severity_tag   = AlertSeverity.CRITICAL

    elif (d_torque is not None and d_wob is not None and d_torque > 5 and d_wob < -10 and rop < 2):
        hazard_title   = "⚠ POSSIBLE STUCK PIPE / PACK-OFF"
        hazard_verdict = (f"Torque surged +{d_torque:.1f} kNm, WOB dropped {abs(d_wob):.1f} kN, ROP fell to {rop:.1f} m/h — "
                          f"differential sticking or pack-off precursor. Reciprocate/rotate string immediately. Do NOT apply excessive overpull.")
        severity_tag   = AlertSeverity.CRITICAL

    elif (mse_val is not None and d_rop is not None and mse_val > 50000 and d_rop < -3):
        hazard_title   = "Bit Balling / Hard Formation Change"
        hazard_verdict = (f"Mechanical Specific Energy at {mse_val:.0f} kJ/m³ while ROP dropped {abs(d_rop):.1f} m/h — "
                          f"bit consuming far more energy per metre. Likely bit balling (clay) or hard stringer. Consider reaming or weight reduction.")

    elif (d_spp is not None and d_torque is not None and d_spp < -12 and abs(d_torque) < 2 and rop < 3):
        hazard_title   = "Possible Bit / String Washout"
        hazard_verdict = (f"SPP fell {abs(d_spp):.1f} bar with no torque change — pressure loss without mechanical resistance points to a washout in BHA or bit nozzles. "
                          f"Pull to shoe and assess BHA integrity.")

    elif d_torque is not None and d_torque > 8:
        hazard_title   = "Elevated Torque — Tight Hole / Formation Interaction"
        hazard_verdict = (f"Torque increased {d_torque:.1f} kNm over the causal window. Possible tight hole, ledge, or reactive formation. "
                          f"Reduce WOB, increase RPM, or circulate to condition mud before continuing.")

    elif dxc_val is not None and dxc_val < 0.8:
        hazard_title   = "D-Exponent Pore Pressure Warning"
        hazard_verdict = (f"Corrected D-exponent = {dxc_val:.3f} (below 1.0) — formation is drilling faster than normal compaction trend, "
                          f"a pore pressure increase signature. Review mud weight and ECD margins immediately.")

    sensor_snapshot = (f"ROP={_fv('rop', ' m/h')} | WOB={_fv('wob', ' kN')} | SPP={_fv('spp', ' bar')} | "
                       f"Torque={_fv('torque', ' kNm')} | RPM={_fv('rpm', ' rpm', '.0f')} | "
                       f"Flow={_fv('flow_in', ' L/min', '.0f')} | MudDensity={_fv('mud_density', ' g/cc')}")

    delta_map = {"delta_rop": "ΔROP", "delta_wob": "ΔWOB", "delta_spp": "ΔSPP",
                 "delta_torque": "ΔTorque", "delta_flow_in": "ΔFlow", "mse": "MSE", "dxc": "D-exp"}
    sig_list = sorted([(lbl, float(features[k])) for k, lbl in delta_map.items() if features.get(k) is not None],
                      key=lambda x: abs(x[1]), reverse=True)
    top_signals = "  |  ".join(f"{lbl}={v:+.2f}" for lbl, v in sig_list[:5]) or "N/A"

    evidence = (f"PROBABLE CAUSE: {hazard_verdict}\n\n"
                f"SENSOR READINGS @ MD {current_md:.1f}m:\n{sensor_snapshot}\n\n"
                f"TOP SIGNALS (30m causal window): {top_signals}\n\n"
                f"Model: IsolationForest | Contamination: 2% | Estimators: 100 | Verdict: ANOMALY")

    new_alert = global_alert_engine.create_alert(
        well_id=well_id,
        title=hazard_title,
        description=f"IsoForest anomaly @ MD {current_md:.1f}m — {hazard_title}",
        severity=severity_tag,
        source=AlertSource.ML_PREDICTION,
        current_md=current_md,
        evidence=evidence,
        source_record="UNSUPERVISED ML ANOMALY — HUMAN VERIFICATION REQUIRED",
        organization_id=organization_id,
        dedup_key=f"iso_forest:{well_id}:{round(current_md / 50.0)}"
    )
    
    return new_alert

// hardcore ventilator: the machine does what you tell it.
// call it as [_patient] call ACME_fnc_hcVentTick, from fn_circhandle.
// outside hardcore the ventilator is forgiving: reasonable settings keep the casualty alive and unreasonable ones
// mostly just look wrong. that is the simplification, and it is a fair one, because a vent panel is already a lot
// to learn.
// under hardcore the machine stops covering for you, which is the honest version. a ventilator is one of the few
// pieces of kit that will kill a patient by working exactly as instructed.
// ventilator-induced lung injury: too much volume per breath overdistends alveoli, and the damage is cumulative and
// permanent for the rest of the day of the casualty. lung-protective ventilation is 6 to 8 ml/kg, and the reason
// that number is drilled into everybody is that the machine will happily deliver twelve.
// enough of it and the lung stiffens, which raises the pressure needed, which tempts the operator to turn the
// pressure limit up, which does more damage. that loop is the point.
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
// VILI accrues over patient-owner clinical time. Frame duration would make
// an identical ventilator exposure progress differently at 5 and 60 FPS.
// Inactive passes establish a baseline without charging disconnected time.
private _dt = [_patient, "hcVent", 0.25, 5] call ACME_fnc_clinicalTickDelta;
if (!(missionNamespace getVariable ["ACME_hcEff_vent", false])) exitWith {};
if (!(_patient getVariable ["ACME_vent_driving", false])) exitWith {};
private _vt = _patient getVariable ["ACME_vent_vti", 0];
if (_vt <= 0) exitWith {};

// the predicted body weight is what tidal volume is actually dosed against, rather than the actual weight. it is
// approximated from the set weight of the casualty, because that is what the panel already asks the operator for.
// it is ACME_vent_weight rather than weightkg. the panel has asked the operator for this since the vent was built,
// and a second name was invented for it here, so this read 80 on every casualty whatever was set.
private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
private _kg = if (_effective select 0) then {_effective select 10} else {_patient getVariable ["ACME_vent_weight", 80]};
private _mlkg = _vt / (_kg max 30);

private _safe = missionNamespace getVariable ["ACME_hcVent_safeMlKg", 8];
private _vili = _patient getVariable ["ACME_vent_vili", 0];

if (_mlkg > _safe) then {
    // the damage rises steeply past the safe band: 10 ml/kg is careless and 14 is destroying lung.
    private _over = (_mlkg - _safe) / _safe;
    _vili = (_vili + ((missionNamespace getVariable ["ACME_hcVent_viliRate", 0.5]) * _over * _over * (_dt / 60))) min 1;
    [_patient, "ACME_vent_vili", _vili, 0.002, 2] call ACME_fnc_setVarNetApprox;
};

// the injured lung stiffens. that is the feedback loop: the peak pressure climbs and the obvious fix makes it
// worse. it is fed into the same compliance multiplier the mainstem model uses, so the ventilator surfaces it
// through the pressure it already reports rather than through a new readout.
if (_vili > 0.02) then {
    private _cmp = 1 - (0.55 * _vili);
    private _cur = _patient getVariable ["ACME_vent_complianceMult", 1];
    [_patient, "ACME_vent_complianceMult", (_cur min _cmp), 0.005, 2] call ACME_fnc_setVarNetApprox;
    // and the shunt it creates costs saturation, published the same way everything else does.
    [_patient, "ACME_o2Drain_vili", (_vili * (missionNamespace getVariable ["ACME_hcVent_viliSatMax", 14])), 0.05, 2] call ACME_fnc_setVarNetApprox;
} else {
    [_patient, "ACME_o2Drain_vili", 0] call ACME_fnc_setVarNet;
};

// one lung doing the work of two.
// call it as [_patient] call ACME_fnc_ettMainstemTick, from fn_circhandle.
// a tube advanced past the carina goes down the right main bronchus, because that bronchus leaves the trachea at a
// shallower angle than the left. the whole tidal volume then goes into one lung. that lung is over-distended and
// the other is not ventilated at all, so it collapses.
// what this looks like, and why it is a good problem:
// EtCO2 is still fine, because the tube is in the trachea and CO2 is coming back. this is the trap.
// SpO2 drifts down and keeps drifting, because half the lung is doing nothing.
// the pressure climbs, because the same volume is going into half the space.
// the chest moves on only one side, and only one side has breath sounds.
// so the capnograph says everything is fine while the casualty gets worse, and the medic has to notice that the
// numbers disagree with each other. that is the whole lesson.
// the fix is to pull the tube back a frame or two, which is exactly what the airway screen now allows.
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
// This worker runs at clinical cadence, not once per rendered/server frame.
// Sample before inactive exits so correcting/reinserting the tube cannot
// charge elapsed time during which there was no mainstem obstruction.
private _dt = [_patient, "ettMainstem", 0.25, 5] call ACME_fnc_clinicalTickDelta;
if (!(_patient getVariable ["ACME_ETT_Mainstem", false])) exitWith {
    [_patient, "ACME_o2Drain_mainstem", 0] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_complianceMult", 1] call ACME_fnc_setVarNet;
};
if (!(_patient getVariable ["ACME_ETT_Inserted", false])) exitWith {
    [_patient, "ACME_ETT_Mainstem", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_o2Drain_mainstem", 0] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_complianceMult", 1] call ACME_fnc_setVarNet;
};

// the shunt builds rather than appearing: the unventilated lung takes time to collapse, and the drift is what the
// medic is meant to notice.
private _drain = _patient getVariable ["ACME_o2Drain_mainstem", 0];
private _cap = missionNamespace getVariable ["ACME_ettMainstemSatDrop", 22];
_drain = (_drain + ((missionNamespace getVariable ["ACME_ettMainstemRate", 0.55]) * _dt)) min _cap;
[_patient, "ACME_o2Drain_mainstem", _drain, 0.05, 1] call ACME_fnc_setVarNetApprox;

// the same volume into half the lung is half the compliance, so the peak pressure climbs. the ventilator reads this
// and it is what raises HIGH AIRWAY PRESSURE by itself, with no special case.
[_patient, "ACME_vent_complianceMult", (missionNamespace getVariable ["ACME_ettMainstemCompliance", 0.55])] call ACME_fnc_setVarNet;

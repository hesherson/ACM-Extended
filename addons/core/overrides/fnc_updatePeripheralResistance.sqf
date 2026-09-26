#include "..\script_component.hpp"
/* Fork-native peripheral resistance composition. */
params ["_unit", "_peripheralResistanceAdjustment", "_deltaT", "_syncValue"];
if (!local _unit) exitWith {};

_unit setVariable ["ACME_nativeResistance", 1 max (DEFAULT_PERIPH_RES + _peripheralResistanceAdjustment), false];
private _circResist = if (missionNamespace getVariable ["ACME_sys_circ", true]) then {_unit getVariable ["ACME_circ_resistDelta", 0]} else {0};
private _pressorAdd = if (missionNamespace getVariable ["ACME_sys_circ", true]) then {_unit getVariable ["ACME_pressorResistAdd", 0]} else {0};
private _lidoToxResist = if (missionNamespace getVariable ["ACME_sys_circ", true]) then {_unit getVariable ["ACME_lidoTox_resistDelta", 0]} else {0};
private _esmToxResist = if (missionNamespace getVariable ["ACME_sys_circ", true]) then {_unit getVariable ["ACME_esmololTox_resistDelta", 0]} else {0};
private _infToxResist = if (missionNamespace getVariable ["ACME_sys_circ", true]) then {_unit getVariable ["ACME_infusionTox_resistDelta", 0]} else {0};
private _awakeResist = if (missionNamespace getVariable ["ACME_sys_paralytic", true]) then {_unit getVariable ["ACME_roc_awakeResistAdd", 0]} else {0};
private _tbiResist = if (missionNamespace getVariable ["ACME_sys_tbi", true]) then {_unit getVariable ["ACME_tbi_resistAdd", 0]} else {0};
private _flightG = if (missionNamespace getVariable ["ACME_sys_flight", true]) then {_unit getVariable ["ACME_flightG_resistAdd", 0]} else {0};
private _shockResist = _unit getVariable ["ACME_shock_resistDelta", 0];
private _infectionResist = _unit getVariable ["ACM_infection_Resistance_Delta", 0];
private _burnResist = _unit getVariable ["ACM_burns_Resistance_Delta", 0];
private _laryngoVagalResist = 0;
if (CBA_missionTime < (_unit getVariable ["ACME_laryngo_vagalUntil",-1])) then {
    private _sev = (_unit getVariable ["ACME_laryngo_vagalSeverity",0]) max 0 min 1;
    _laryngoVagalResist = -((missionNamespace getVariable ["ACME_laryngo_vagalResistDrop",28]) * _sev);
};

private _autoPeepDrop = 0;
private _apVal = _unit getVariable ["ACME_vent_autoPEEP", 0];
if (_apVal > 2 && {missionNamespace getVariable ["ACME_sys_vent", true]} && {_unit getVariable ["ACME_vent_driving", false]}) then {
    _autoPeepDrop = -((linearConversion [2, 15, _apVal, 0, 1, true]) * (missionNamespace getVariable ["ACME_vent_autoPeepBPDrop", 35]));
};

_unit setVariable [VAR_PERIPH_RES,
    1 max (DEFAULT_PERIPH_RES + _peripheralResistanceAdjustment + _circResist + _pressorAdd + _lidoToxResist + _esmToxResist + _infToxResist + _awakeResist + _tbiResist + _flightG + _shockResist + _infectionResist + _burnResist + _laryngoVagalResist + _autoPeepDrop),
    _syncValue
];
_unit setVariable ["ACME_resistanceApplied_tbi", _tbiResist, false];

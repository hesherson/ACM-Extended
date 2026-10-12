/* Read-only UI contract [attached, usable, liters, class, status]. No cargo scans per frame. */
params [["_patient",objNull,[objNull]]];
private _session=_patient getVariable ["ACME_vent_o2Session",""];
private _source=_patient getVariable ["ACME_vent_o2Source",objNull];
private _attached=_session!="" && {!isNull _source};
private _credit=(_patient getVariable ["ACME_vent_o2Credit",0]) max 0;
private _until=_patient getVariable ["ACME_vent_o2VerifiedUntil",-1];
private _state=_patient getVariable ["ACME_vent_o2Status","NONE"];
private _sourceNear=_attached && {(_source isEqualTo _patient) || {[_source,_patient] call ACME_fnc_ventRecoveryNear}};
private _usable=_attached && {_sourceNear} && {serverTime<=_until} && {_state in ["READY","DRAWING"]}
    && {(_patient getVariable ["ACME_vent_o2Epoch",-1])==([_patient] call ACME_fnc_clinicalEpoch)}
    && {(_patient getVariable ["ACME_vent_o2Custody",""])==(_patient getVariable ["ACME_vent_custodyId",""])};
private _units=_patient getVariable ["ACME_vent_o2ReserveUnits",0];
private _liters=if (_units<0) then {-1} else {_units*(425/283)+_credit};
private _text=switch _state do {
    case "READY": {"Oxygen connected"};
    case "DRAWING": {"Oxygen reserve updating"};
    case "VERIFYING": {"Checking oxygen supply..."};
    case "EMPTY": {"Oxygen tank depleted · Room air"};
    case "UNAVAILABLE": {"Oxygen supply unavailable · Room air"};
    default {"No oxygen tank · Room air"};
};
if (_attached && {!_usable} && {_state in ["READY","DRAWING"]}) then {_text="Checking oxygen supply · Room air";};
[_attached,_usable,_liters,"ACM_OxygenTank_425",_text]

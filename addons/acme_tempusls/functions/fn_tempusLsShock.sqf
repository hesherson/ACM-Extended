/* One identified patient-owner transaction, using ACME's native shock outcome. */
params ["_o", "_medic", "_patient", "_energy", "_sync", "_ptype", "_id", "_epoch", "_sentAt", ["_chargeId", ""]];
if (isNull _o || {isNull _patient} || {isNull _medic} || {!local _patient}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner != owner _medic}) exitWith {};
if (!alive _medic || {!([_medic] call ace_common_fnc_isAwake)}
    || {_medic distance _o > 3} || {_o distance _patient > 6}
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {serverTime - _sentAt > 15} || {_sentAt - serverTime > 2}
    || {(_o getVariable ["acme_tempusls_pat", objNull]) isNotEqualTo _patient}
    || {!((_o getVariable ["acme_tempusls_pw", [false]]) select 0)}
    || {!(_o getVariable ["acme_tempusls_pads",true])}
    || {!(_o getVariable ["acme_tempusls_armed", false])}) exitWith {};
private _deviceValid = _o isKindOf "ACME_TempusLS"
    || {_o isEqualTo _medic && {[_medic, "ACME_TempusLS_Item"] call ace_common_fnc_hasItem}};
if (!_deviceValid || {!finite _energy} || {_energy < 1} || {_energy > 200}) exitWith {};
private _charge = _o getVariable ["acme_tempusls_charge", []];
if (count _charge != 6 || {_chargeId == ""} || {(_charge select 0) != _chargeId}
    || {(_charge select 1) isNotEqualTo _patient} || {(_charge select 2) != _epoch}
    || {(_charge select 3) isNotEqualTo (_o getVariable ["acme_tempusls_pw", [false]])}
    || {abs ((_charge select 4) - _energy) > 0.01} || {serverTime > (_charge select 5)}) exitWith {};
private _history = _o getVariable ["acme_tempusls_shocks", []];
if (_id in _history) exitWith {};
_history pushBack _id;
if (count _history > 64) then {_history deleteRange [0, count _history - 64];};
_o setVariable ["acme_tempusls_shocks", _history, true];
[_o] call ACME_fnc_tempusLsChargeClear;
private _rh = [_patient] call ACME_fnc_rhythmGet;
private _defib = _rh in [2, 3, 102];
private _organized = _rh in [4, 100, 101, 103, 104];
if (_sync && {_defib}) exitWith {[_medic, "No synchronized shock: no suitable R wave. Review SYNC mode."] call ACME_fnc_clinicalNotice;};
private _child = _ptype isEqualTo "Child";
private _minimum = if (_defib) then {[missionNamespace getVariable ["ACME_tempusls_defibJ", 120], missionNamespace getVariable ["ACME_tempusls_defibJChild", 50]] select _child} else {if (_organized && {_sync}) then {[missionNamespace getVariable ["ACME_tempusls_syncJ", 50], missionNamespace getVariable ["ACME_tempusls_syncJChild", 10]] select _child} else {0}};
if (_energy < _minimum) exitWith {
    playSound3D ["\x\ACM\addons\circulation\sound\shock_jolt1.wav", _patient, false, getPosASL _patient, 3, 1, 15];
    [_patient, "activity", "Tempus LS shock %1 J (below configured simulation conversion threshold)", [_energy]] call ace_medical_treatment_fnc_addToLog;
};
// Temporary native pad/charge context is local and is always restored. LS owns its own charge.
private _keys = ["ACM_circulation_AED_Placement_Pads", "ACM_circulation_AED_InUse", "ACM_circulation_AED_Charged"];
private _previous = _keys apply {_patient getVariable [_x, false]};
{_patient setVariable [_x, true];} forEach _keys;
[_medic, _patient, _id, _epoch, _patient getVariable ["ACM_circulation_AED_LastShock", -60], _sync, _sentAt] call ACME_fnc_shockLocal;
{_patient setVariable [_x, _previous select _forEachIndex];} forEach _keys;

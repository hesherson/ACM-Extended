/* [unit,callback,args=[],timeoutSeconds=30] -> local request number, or -1.
 * callback receives [ok,extendedCbaLoadout,args,reason]. No empty save on timeout.
 * One atomic snapshot is handed to the adapter; the callback must save this
 * returned value rather than reread inventory on a later frame. */
params ["_unit","_callback",["_args",[]],["_timeout",30]];
if (isNull _unit || {!local _unit} || {!(_callback isEqualType {})}
    || {!(_timeout isEqualType 0)} || {!finite _timeout} || {_timeout < 0} || {_timeout > 3600}) exitWith {-1};
private _request = 1 + (missionNamespace getVariable ["ACME_persistenceRequest",0]);
missionNamespace setVariable ["ACME_persistenceRequest",_request];
private _context = [_unit,_callback,_args,diag_tickTime + _timeout,_unit getVariable ["ACME_equipmentKitEpoch",0],_unit getVariable ["ACME_providerLocalityEpoch",0]];
[{
    params ["_context","_pfh"];
    _context params ["_unit","_callback","_args","_deadline","_kit","_locality"];
    private _reason = "";
    if (isNull _unit) then {_reason = "deleted";} else {
        if (!local _unit || {_locality != (_unit getVariable ["ACME_providerLocalityEpoch",0])}) then {_reason = "locality changed";};
        if (_kit != (_unit getVariable ["ACME_equipmentKitEpoch",0])) then {_reason = "equipment replaced";};
    };
    private _snapshot = if (_reason == "") then {[_unit] call ACME_fnc_persistenceSnapshot} else {[]};
    if (_snapshot isEqualTo [] && {_reason == ""} && {diag_tickTime < _deadline}) exitWith {};
    if (_snapshot isNotEqualTo [] && {(_unit getVariable ["ACME_persistenceLease",""]) != ""}) then {
        if !([_unit,_snapshot] call ACME_fnc_persistenceCaptureValid) then {_snapshot = []; _reason = "checkpoint facts changed";};
    };
    if (_snapshot isEqualTo [] && {_reason == ""}) then {_reason = _unit getVariable ["ACME_persistenceBlockReason","unsettled custody or invalid metadata"]; if (_reason == "") then {_reason = "unsettled custody or invalid metadata";};};
    [_pfh] call CBA_fnc_removePerFrameHandler;
    [!(_snapshot isEqualTo []),_snapshot,_args,_reason] call _callback;
},0.25,_context] call CBA_fnc_addPerFrameHandler;
// The PFH is intentionally private and bounded; no unit variable/network write is needed.
_request

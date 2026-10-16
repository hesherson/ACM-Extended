/* Patient-owner traumatic seal burp. Vent air; surgical-tract blood drainage belongs to thoracostomy aftercare. */
params ["_medic","_patient",["_bodyPart","body"], ["_epoch", -1], ["_request", []], ["_session", "", [""]]];
if (isNull _patient || {isNull _medic}) exitWith {};
if (_epoch < 0) then {
    _epoch = [_patient] call ACME_fnc_clinicalEpoch;
    _session = uiNamespace getVariable ["ACME_CS_SessionToken", ""];
    private _sequence = (missionNamespace getVariable ["ACME_pleuralDrainSequence", 0]) + 1;
    missionNamespace setVariable ["ACME_pleuralDrainSequence", _sequence];
    _request = [clientOwner, _sequence, serverTime];
};
if (!local _patient) exitWith {["ACME_ownerCommand",[_patient,"burp",[_medic,_patient,_bodyPart,_epoch,_request,_session]],_patient] call CBA_fnc_targetEvent;};
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious",false]}
    || {(_medic distance _patient) > 5}) exitWith {};
if !([_patient,true] call ACME_fnc_chestSealBurpReady) exitWith {};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {};
// Closing a panel retires its token. Late inputs from that panel cannot treat a reopened session.
if (_session == "" || {!(_session in (_patient getVariable ["ACME_CS_ProcedureTokens", []]))}) exitWith {};
private _hasSeal = _patient getVariable ["ACM_breathing_ChestSeal_State", false];
_hasSeal = _hasSeal || {((_patient getVariable ["ACME_CS_holeData", []]) findIf {_x param [4, false]}) >= 0};
if (!_hasSeal) exitWith {};
// B216: keep owner-local replay rejection independent of surgical blood drainage.
// Public receipts survive patient ownership transfer; server time bounds delayed/reordered packets.
if !(_request isEqualType [] && {count _request == 3}) exitWith {};
if ((_request findIf {!(_x isEqualType 0) || {!finite _x}}) >= 0) exitWith {};
_request params ["_origin", "_sequence", "_issued"];
if (_origin < 0 || {_origin != floor _origin} || {_sequence < 1}
    || {_sequence != floor _sequence} || {serverTime - _issued > 15}
    || {_issued - serverTime > 2}) exitWith {};
private _receipts = _patient getVariable ["ACME_CS_burpReceipts", [-1, []]];
private _rows = if ((_receipts param [0, -1]) == _epoch) then {+(_receipts param [1, []])} else {[]};
_rows = _rows select {serverTime - (_x select 2) <= 15};
private _index = _rows findIf {(_x select 0) == _origin};
if (_index >= 0 && {_sequence <= ((_rows select _index) select 1)}) exitWith {};
if (_index < 0 && {count _rows >= 256}) exitWith {};
if (_index < 0) then {_rows pushBack [_origin, _sequence, _issued];}
else {_rows set [_index, [_origin, _sequence, _issued]];};
_patient setVariable ["ACME_CS_burpReceipts", [_epoch, _rows], true];
// A corpse can still be handled, but no physiological worker should restart.
if (alive _patient) then {[_patient,"burp"] call ACME_fnc_ptxTreat; [_patient] call ACM_breathing_fnc_updateLungState;};
_patient setVariable ["ACME_CS_lastBurp",CBA_missionTime,true];
[_patient, "burp", "Burped chest seal", [], _medic, 0, _session] call ACME_fnc_chestSealLogOnce;
// Provider remains in the persistent workspace hold. medic3 is seal-placement-only.

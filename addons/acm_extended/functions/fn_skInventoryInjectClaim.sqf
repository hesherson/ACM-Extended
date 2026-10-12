/* Dispatch only after the server has certified one exact syringe custody claim.
 * Args capture provider, patient, solution and optional remaining solution before
 * the network hop; UI selection changes cannot administer another syringe.
 */
params ["_accepted","_args"];
_args params ["_medic","_patient","_bodyPart","_doses","_site","_row","_remaining","_refundRow","_request",["_successItems",[]]];
private _sid = _row param [11,"",[""]];
if (isNull _medic || {!local _medic}) exitWith {};
private _rows = +(_medic getVariable ["ACME_narcStore",[]]);
private _idx = _rows findIf {(_x param [11,"",[""]]) == _sid};
if (!_accepted || {_idx < 0} || {!alive _medic} || {isNull _patient}) exitWith {
    [_medic,_request,false,[_sid,+_row]] call ACME_fnc_inventoryLedgerSettle;
};
private _current = _rows select _idx;
private _unchanged = (_current param [0,""]) == (_row param [0,""])
    && {(_current param [1,0]) == (_row param [1,0])}
    && {(_current param [2,0]) == (_row param [2,0])}
    && {(_current param [4,0]) == (_row param [4,0])}
    && {(_current param [5,[]]) isEqualTo (_row param [5,[]])};
if (!_unchanged) exitWith {[_medic,_request,false,[_sid,+_current]] call ACME_fnc_inventoryLedgerSettle;};
if (_remaining isEqualTo []) then {_rows deleteAt _idx;} else {_rows set [_idx,+_remaining];};
private _hidden = _medic getVariable ["ACME_syringeInventoryHidden",[]];
_hidden pushBackUnique _sid;
_medic setVariable ["ACME_syringeInventoryHidden",_hidden,false];
[_medic,_rows] call ACME_fnc_narcStoreCommit;
[_medic,_patient,_bodyPart,_doses,"administer",_site,[[],[+_refundRow],_successItems],["syringeB279",_request,_sid]] call ACME_fnc_medicationRequest;
if (hasInterface && {_medic isEqualTo ACE_player} && {!isNull findDisplay 84000}) then {
    call ACME_fnc_skRefreshDrawn;
    call ACME_fnc_skBuildHotspots;
};

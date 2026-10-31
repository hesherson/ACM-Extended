/* Retire only this finite pickup. A late callback cannot release a newer treatment's stance. */
params ["_unit","_request","_token",["_success",false],["_releasePose",true]];
if (isNull _unit) exitWith {};
private _state = _unit getVariable ["ACME_litterCollect",[]];
if (count _state != 5 || {(_state select 0) != _request} || {(_state select 1) != _token}) exitWith {};
private _animated = (_state select 2) in ["anim","cancel"];
private _pfh = _unit getVariable ["ACME_litterPFH",-1];
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
_unit setVariable ["ACME_litterPFH",-1];
private _key = _unit getVariable ["ACME_litterKey",-1];
if (_key >= 0) then {(findDisplay 46) displayRemoveEventHandler ["KeyDown",_key];};
_unit setVariable ["ACME_litterKey",-1];
_success = _success && {_animated} && {[_unit,true] call ACME_fnc_medicalLitterCanCollect}
    && {(_state select 4) == (_unit getVariable ["ACME_providerLocalityEpoch",0])};
if (_success) then {_state set [2,"commit"];} else {_unit setVariable ["ACME_litterCollect",[]];};
["ACME_medicalLitter",[["cancel","commit"] select _success,_unit,clientOwner,_request,_token]] call CBA_fnc_serverEvent;
// Clear our ownership before asking whether a newer controller owns the provider.
if (_releasePose && {_animated} && {local _unit} && {alive _unit} && {isNull objectParent _unit}
    && {!(_unit getVariable ["ACE_isUnconscious",false])}
    && {!([_unit] call ACME_fnc_providerStanceOwned)}) then {
    _unit setUnitPos "AUTO";
    if (!_success && {missionNamespace getVariable ["ACME_interventionAnimations",true]}) then {
        [_unit,[_unit,"AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation,2] call ACME_fnc_doAnim;
    };
};
